"""
招标文件 AI 智能解析 — 调用火山引擎豆包大模型
"""
import base64
import io
import json
import logging
from typing import Optional

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

TENDER_PARSE_PROMPT = """你是一个专业的招标文件解析助手。请从以下招标文件内容中提取结构化信息。

请严格按照以下 JSON 格式输出，不要输出任何其他内容（不要 ```json 包裹）：

{
  "basic_info": {
    "project_name": "项目名称",
    "tender_no": "招标编号",
    "tender_unit": "招标人/采购人",
    "agent_unit": "代理机构（如有）",
    "tender_method": "招标方式（公开招标/邀请招标/竞争性谈判/询价/单一来源）",
    "budget_amount": null,
    "budget_amount_text": "预算金额原文描述"
  },
  "timeline": {
    "publish_date": "发布日期 (YYYY-MM-DD 或 null)",
    "question_deadline": "疑问截止 (YYYY-MM-DD HH:mm 或 null)",
    "bid_deadline": "投标截止 (YYYY-MM-DD HH:mm 或 null)",
    "open_bid_time": "开标时间 (YYYY-MM-DD HH:mm 或 null)",
    "open_bid_place": "开标地点",
    "deposit_amount": null,
    "deposit_amount_text": "保证金原文描述",
    "deposit_deadline": "保证金截止 (YYYY-MM-DD 或 null)"
  },
  "qualification": {
    "required_certs": ["需要的资质证书列表"],
    "required_experience": "业绩要求描述",
    "team_requirements": "人员要求描述",
    "financial_requirements": "财务要求描述",
    "exclusion_conditions": ["不得参与的条件列表"]
  },
  "scoring": {
    "method": "评分方式（综合评分法/最低价法/性价比法等）",
    "technical_score": null,
    "commercial_score": null,
    "price_score": null,
    "details": [
      {"category": "技术/商务/价格", "item": "评分项名称", "max_score": null, "criteria": "评分标准"}
    ]
  },
  "bid_document_requirements": {
    "format": "投标文件格式要求",
    "copies": "份数要求",
    "seal_requirements": "盖章签字要求",
    "chapters": [
      {
        "title": "章节标题（如：磋商响应函）",
        "section_type": "TEMPLATE/MANUAL/AI_GENERATE/LIBRARY",
        "template": "招标文件中提供的模板原文，原样保留格式（找不到时填空字符串）",
        "matched": true
      }
    ]
  },
  "risk_alerts": ["可能导致废标的注意事项列表，尤其关注容易忽略的条款"]
}

注意：
1. 如果某个字段在文件中没有找到，填 null
2. budget_amount 填数字（单位万元），如果无法确定数字填 null 但在 budget_amount_text 写原文
3. 日期尽量转换为标准格式
4. risk_alerts 非常重要，请仔细检查废标条件
5. chapters 中的 template 字段：找招标文件中"响应文件格式""投标文件格式""附件""格式一/二/三..."等部分，把对应章节的模板原文原样摘出（保留表格、空白下划线 ___、签章位 (签章) 等）；招标文件没提供模板则填空字符串并把 matched 设为 false
6. section_type 推断规则：
   - TEMPLATE：固定格式文件（响应函、声明函、承诺函、授权委托书、身份证明）
   - MANUAL：需手动填写数据（报价表、价格表、分项报价）
   - AI_GENERATE：需撰写方案（技术方案、服务方案、商务/技术偏离表）
   - LIBRARY：附资料（业绩证明、人员清单、资质证书、设备清单）"""


class TenderAIParser:

    def __init__(self):
        self.client = None

    def _get_client(self) -> OpenAI:
        if self.client is None:
            self.client = OpenAI(
                api_key=settings.AI_API_KEY,
                base_url=settings.AI_BASE_URL,
            )
        return self.client

    def ocr_single_page(self, pdf_path: str, page_index: int) -> str:
        """OCR 单页：渲染、压缩、调用视觉模型识别。返回页面文字。"""
        import fitz
        from PIL import Image

        vision_model = getattr(settings, "AI_VISION_MODEL", None)
        if not vision_model:
            raise Exception("视觉模型未配置（AI_VISION_MODEL 为空），无法 OCR 扫描件")

        client = self._get_client()
        doc = fitz.open(pdf_path)
        try:
            page = doc[page_index]
            pix = page.get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            if img.width > 1500:
                ratio = 1500 / img.width
                img = img.resize((1500, int(img.height * ratio)), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=85, optimize=True)
            img_b64 = base64.b64encode(buf.getvalue()).decode()
        finally:
            doc.close()

        response = client.chat.completions.create(
            model=vision_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "请把这页招标文件的所有文字（包括表格内容）完整地识别出来，按原顺序输出。不要总结，不要解释，只输出原文。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ],
            }],
            max_tokens=4096,
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()

    def get_pdf_page_count(self, pdf_path: str) -> int:
        import fitz
        doc = fitz.open(pdf_path)
        n = len(doc)
        doc.close()
        return n

    def ocr_pdf_with_vision(self, pdf_path: str, max_pages: int = 100) -> str:
        """对扫描件 PDF 用视觉模型逐页 OCR，返回拼接后的全文（无进度回调版本）"""
        total_pages = self.get_pdf_page_count(pdf_path)
        pages_to_process = min(total_pages, max_pages)
        logger.info(f"开始 OCR：共 {total_pages} 页，处理前 {pages_to_process} 页")

        all_text = []
        for i in range(pages_to_process):
            try:
                page_text = self.ocr_single_page(pdf_path, i)
                all_text.append(f"--- 第 {i+1} 页 ---\n{page_text}")
                logger.info(f"OCR 第 {i+1}/{pages_to_process} 页完成（{len(page_text)} 字）")
            except Exception as e:
                logger.warning(f"OCR 第 {i+1} 页失败: {e}")
                all_text.append(f"--- 第 {i+1} 页 ---\n[OCR 失败]")

        result = "\n\n".join(all_text)
        if total_pages > pages_to_process:
            result += f"\n\n[文档共 {total_pages} 页，仅处理了前 {pages_to_process} 页]"
        return result

    def parse(self, text: str) -> dict:
        """调用 AI 解析招标文件文本，返回结构化结果"""
        client = self._get_client()

        # 截断过长文本（预留输出空间）
        max_chars = 200000  # 约 100K tokens
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[文档过长，已截断]"

        try:
            response = client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=[
                    {"role": "system", "content": TENDER_PARSE_PROMPT},
                    {"role": "user", "content": f"请解析以下招标文件：\n\n{text}"},
                ],
                max_tokens=16384,
                temperature=0.1,
            )

            result_text = response.choices[0].message.content.strip()

            # 清理可能的 markdown 包裹
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1] if "\n" in result_text else result_text
                if result_text.endswith("```"):
                    result_text = result_text[:-3]

            return json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"AI 返回的 JSON 解析失败: {e}")
            return {"error": "AI 返回格式异常", "raw_response": result_text[:500]}
        except Exception as e:
            logger.error(f"AI 解析失败: {e}")
            raise

tender_ai_parser = TenderAIParser()
