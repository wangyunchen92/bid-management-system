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

    def _compress_image(self, image_bytes: bytes, max_width: int = 1500, quality: int = 85) -> tuple:
        """压缩图片以减少 token 消耗和识别耗时

        - 超宽图按比例缩放到 max_width
        - 统一转 JPEG（比 PNG 体积小）
        - 返回 (压缩后字节, 'jpeg')
        """
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(image_bytes))
        # RGBA/P 模式转 RGB（JPEG 不支持透明）
        if img.mode in ('RGBA', 'P', 'LA'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 按比例缩放
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        return buf.getvalue(), 'jpeg'

    def _try_vision_recognize(self, file_path: str, module: str) -> Optional[dict]:
        """对扫描件/图片/图片 PDF 用视觉模型识别

        支持三种情况：
        1. 直接上传的 jpg/png/jpeg 图片
        2. PDF 中有内嵌图片（常见的扫描 PDF）
        3. PDF 是矢量渲染但无文本层（罕见），将首页渲染为图片

        所有图片统一压缩到 1500px 宽以降低 token 消耗和耗时。
        """
        import base64
        import os

        vision_model = getattr(settings, "AI_VISION_MODEL", None)
        if not vision_model:
            return None

        ext = os.path.splitext(file_path)[1].lower().lstrip('.')

        try:
            # 构造图片数据
            if ext in ('jpg', 'jpeg', 'png'):
                with open(file_path, 'rb') as f:
                    image_bytes = f.read()
            elif ext == 'pdf':
                import fitz
                doc = fitz.open(file_path)
                page = doc[0]
                # 优先取内嵌大图
                images = page.get_images()
                image_bytes = None
                if images:
                    xref = images[0][0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                if not image_bytes:
                    # 渲染首页为图片（150 DPI）
                    pix = page.get_pixmap(dpi=150)
                    image_bytes = pix.tobytes("png")
                doc.close()
            else:
                return None

            # 压缩图片（大图缩放到 1500px 宽，JPEG 质量 85%）
            original_size = len(image_bytes)
            image_bytes, img_ext = self._compress_image(image_bytes)
            logger.info(f"图片压缩: {original_size/1024:.0f}KB → {len(image_bytes)/1024:.0f}KB")

            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            module_info = MODULE_PROMPTS[module]
            client = self._get_client()
            response = client.chat.completions.create(
                model=vision_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"请识别这张{module_info['description']}图片中的信息。\n\n{module_info['fields']}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/{img_ext};base64,{image_b64}"}},
                    ],
                }],
                max_tokens=2048,
                temperature=0.1,
            )
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1] if "\n" in result_text else result_text
                if result_text.endswith("```"):
                    result_text = result_text[:-3].strip()
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

        # 过滤页分隔符和空行后判断有效文本长度
        import re
        effective_text = re.sub(r'---\s*第\s*\d+\s*页\s*---|\s+', '', text)
        if len(effective_text) < 20:
            # 扫描件/图片 PDF / 直接图片 — 尝试视觉模型
            logger.info(f"有效文本太少({len(effective_text)}字)，尝试视觉模型识别...")
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
