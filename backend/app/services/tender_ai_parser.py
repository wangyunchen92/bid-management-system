"""
招标文件 AI 智能解析 — 调用火山引擎豆包大模型
"""
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
    "chapters": ["投标文件需要包含的章节"]
  },
  "risk_alerts": ["可能导致废标的注意事项列表，尤其关注容易忽略的条款"]
}

注意：
1. 如果某个字段在文件中没有找到，填 null
2. budget_amount 填数字（单位万元），如果无法确定数字填 null 但在 budget_amount_text 写原文
3. 日期尽量转换为标准格式
4. risk_alerts 非常重要，请仔细检查废标条件"""


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
                max_tokens=8192,
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
