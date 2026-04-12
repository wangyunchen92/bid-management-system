"""
企业资料 AI 识别服务
上传文件 → 提取文本 → AI 解析 → 返回结构化字段
"""
import json
import logging
from typing import Optional

from openai import OpenAI
from app.config import settings
from app.services.document_parser import document_parser

logger = logging.getLogger(__name__)

# 每个模块的提取 prompt
MODULE_PROMPTS = {
    "qualifications": {
        "description": "企业资质证书",
        "fields": """请提取以下字段（JSON格式，不要```json包裹）：
{
  "cert_name": "证书名称",
  "cert_type": "证书类型，只能填以下值之一：BUSINESS_LICENSE/QUALIFICATION/ISO/SAFETY/OTHER",
  "cert_no": "证书编号",
  "issuing_authority": "发证机关",
  "issue_date": "发证日期 (YYYY-MM-DD 或 null)",
  "expiry_date": "有效期截止 (YYYY-MM-DD 或 null)"
}""",
    },
    "achievements": {
        "description": "业绩案例/中标通知书/合同",
        "fields": """请提取以下字段（JSON格式，不要```json包裹）：
{
  "project_name": "项目名称",
  "client_name": "甲方/业主单位",
  "contract_amount": "合同金额（万元，数字，无法确定填null）",
  "completion_date": "完成/签订日期 (YYYY-MM-DD 或 null)",
  "project_type": "项目类型",
  "description": "项目简要描述（一句话）"
}""",
    },
    "personnel-certs": {
        "description": "人员证书",
        "fields": """请提取以下字段（JSON格式，不要```json包裹）：
{
  "person_name": "持证人姓名",
  "cert_name": "证书名称",
  "cert_no": "证书编号",
  "cert_type": "证书类型",
  "issue_date": "发证日期 (YYYY-MM-DD 或 null)",
  "expiry_date": "有效期截止 (YYYY-MM-DD 或 null)"
}""",
    },
    "products": {
        "description": "产品/设备资料",
        "fields": """请提取以下字段（JSON格式，不要```json包裹）：
{
  "name": "产品/设备名称",
  "model": "型号/规格",
  "brand": "品牌/厂商",
  "quantity": "数量（数字，无法确定填1）",
  "unit": "单位（台/套/个等）",
  "description": "产品简要描述"
}""",
    },
}


class LibraryAIService:

    def __init__(self):
        self.client = None

    def _get_client(self) -> OpenAI:
        if self.client is None:
            self.client = OpenAI(api_key=settings.AI_API_KEY, base_url=settings.AI_BASE_URL)
        return self.client

    def _try_vision_recognize(self, file_path: str, module: str) -> Optional[dict]:
        """对扫描件/图片 PDF 用视觉模型识别"""
        import base64
        import fitz

        try:
            doc = fitz.open(file_path)
            page = doc[0]
            images = page.get_images()
            if not images:
                doc.close()
                return None

            xref = images[0][0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            ext = base_image["ext"]
            doc.close()

            # 尝试用视觉模型
            vision_model = getattr(settings, "AI_VISION_MODEL", None)
            if not vision_model:
                return None

            module_info = MODULE_PROMPTS[module]
            client = self._get_client()
            response = client.chat.completions.create(
                model=vision_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"请识别这张{module_info['description']}图片中的信息。\n\n{module_info['fields']}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{image_b64}"}},
                    ],
                }],
                max_tokens=2048,
                temperature=0.1,
            )
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1] if "\n" in result_text else result_text
                if result_text.endswith("```"):
                    result_text = result_text[:-3]
            return json.loads(result_text)
        except Exception as e:
            logger.warning(f"视觉模型识别失败: {e}")
            return None

    def recognize(self, file_path: str, module: str) -> dict:
        """识别文件内容，返回结构化字段"""
        if module not in MODULE_PROMPTS:
            raise ValueError(f"不支持的模块: {module}")

        # 提取文本
        text = ""
        try:
            result = document_parser.extract_text(file_path)
            text = result["text"]
        except Exception as e:
            logger.error(f"文本提取失败: {e}")

        if not text or len(text.strip()) < 10:
            # 扫描件/图片 PDF — 尝试视觉模型
            logger.info("文本提取为空，尝试视觉模型识别...")
            vision_result = self._try_vision_recognize(file_path, module)
            if vision_result:
                return vision_result
            return {"error": "该文件是扫描件或图片，无法提取文字。请开通视觉模型或手动填写信息。"}

        # 截断过长文本
        if len(text) > 10000:
            text = text[:10000]

        module_info = MODULE_PROMPTS[module]

        prompt = f"""你是一个专业的文档识别助手。请从以下{module_info['description']}文件内容中提取信息。

{module_info['fields']}

注意：如果某个字段无法从文件中确定，填 null。日期统一转为 YYYY-MM-DD 格式。金额统一转为万元。

文件内容：
{text}"""

        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个精确的文档信息提取助手，只输出JSON，不要其他任何内容。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2048,
                temperature=0.1,
            )

            result_text = response.choices[0].message.content.strip()
            # 清理 markdown 包裹
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1] if "\n" in result_text else result_text
                if result_text.endswith("```"):
                    result_text = result_text[:-3]

            return json.loads(result_text)
        except json.JSONDecodeError:
            logger.error(f"AI 返回 JSON 解析失败")
            return {"error": "AI 识别结果格式异常，请手动填写"}
        except Exception as e:
            logger.error(f"AI 识别失败: {e}")
            return {"error": f"AI 识别失败: {str(e)}"}


library_ai_service = LibraryAIService()
