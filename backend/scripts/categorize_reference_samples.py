"""把 reference_samples.jsonl 分类，每个 category 选 top-N 最有代表性的样本。

不调 AI，纯关键词命中计分排序。

输出：data/reference_samples_top.jsonl（最终落库的精选样本）
"""

import json
import os
import re

IN_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "reference_samples.jsonl")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "reference_samples_top.jsonl")

# category → (关键词列表, 最终选 top N)
CATEGORIES = [
    ("服务方案", [
        "服务承诺", "服务方式", "服务流程", "服务响应", "7×24", "24小时", "客户回访",
        "项目联系人", "一小时", "现场响应", "四个优先",
    ], 4),
    ("印刷工艺", [
        "套印", "印刷工艺", "晒版", "出片", "打样", "校色", "网点", "色彩管理",
        "四色印刷", "烫银", "哑膜", "锁线", "模切", "覆膜", "胶印", "油墨", "墨色",
    ], 4),
    ("质量控制", [
        "质量保障", "质量责任", "质量管控", "误差", "监督", "考核", "整改",
        "印刷品质", "重印", "验收", "缺陷",
    ], 3),
    ("应急预案", [
        "应急预案", "紧急订单", "紧急情况", "突发", "应对措施", "应急响应",
        "重印资源", "备用设备",
    ], 3),
    ("安全生产", [
        "消防", "安全生产", "安全责任", "防火", "安全操作", "用电安全", "消防器材",
        "灭火器", "安全培训", "事故预防",
    ], 3),
    ("仓储物流", [
        "仓库", "堆放", "卡板", "防潮", "防尘", "防霉", "运输", "配送", "包装",
        "成品", "原料", "湿度", "温度",
    ], 3),
    ("保密措施", [
        "保密", "机密", "信息管控", "保密协议", "信息安全", "数据保护",
    ], 2),
    ("人员配置", [
        "项目经理", "项目负责人", "组织架构", "人员配置", "团队", "环节对接",
        "项目组",
    ], 2),
    ("环保措施", [
        "节能", "环保", "绿色印刷", "VOC", "废弃物", "节约", "回收",
    ], 2),
    ("售后服务", [
        "售后服务", "客户回访", "满意度", "售后承诺",
    ], 2),
]


def score(content: str, keywords: list[str]) -> int:
    s = 0
    for kw in keywords:
        s += content.count(kw)
    # 加分：含"误差≤"/"温度"等带数字+单位的工艺指标
    s += len(re.findall(r'≤?\s*\d+(?:\.\d+)?\s*(?:mm|cm|m|℃|%|小时|分钟|秒)', content)) * 3
    # 加分：含编号清单（一/二/三 + （1）（2）（3））
    s += len(re.findall(r'^[（(][一二三四五六七八九十]+[）)]', content, re.MULTILINE))
    return s


def main():
    with open(IN_PATH, encoding="utf-8") as f:
        samples = [json.loads(line) for line in f]

    print(f"输入 {len(samples)} 个章节")

    selected: list[dict] = []
    used_ids: set[int] = set()  # 避免一段被多个 category 抢

    for cat_name, keywords, top_n in CATEGORIES:
        scored = []
        for i, s in enumerate(samples):
            if i in used_ids:
                continue
            sc = score(s["content"], keywords)
            if sc >= 3:  # 命中阈值
                scored.append((sc, i, s))
        scored.sort(key=lambda x: -x[0])

        picked = 0
        for sc, idx, s in scored:
            if picked >= top_n:
                break
            used_ids.add(idx)
            selected.append({
                **s,
                "category": cat_name,
                "score": sc,
                "matched_keywords": [k for k in keywords if k in s["content"]][:5],
            })
            picked += 1
        print(f"  [{cat_name}] 命中 {len(scored)} 候选，选了 {picked}")

    print(f"\n最终选 {len(selected)} 个样本入库")

    # 字数分布
    buckets = {"300-800": 0, "800-1500": 0, "1500-3000": 0, "3000+": 0}
    for s in selected:
        n = s["length"]
        if n < 800: buckets["300-800"] += 1
        elif n < 1500: buckets["800-1500"] += 1
        elif n < 3000: buckets["1500-3000"] += 1
        else: buckets["3000+"] += 1
    print("字数分布:", buckets)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for s in selected:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"\n✓ 已写入 {OUT_PATH}")


if __name__ == "__main__":
    main()
