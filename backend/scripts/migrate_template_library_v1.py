"""库模板 v1 迁移：清理硬编码 + 新增报价表/最后承诺报价表

幂等：可重复执行（按内容判断是否需要更新）

执行：
    cd backend && python3 scripts/migrate_template_library_v1.py
"""

import sqlite3
import sys
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "bid.db")


# ── 修改的模板内容 ──────────────────────────────────────────

TEMPLATE_AUTH_LETTER_NEW = """法定代表人（单位负责人）授权委托书

本授权书声明：{公司名称}（供应商名称）授权本公司{法定代表人}（供应商授权代表姓名）代表本公司参加{招标单位}的{项目名称}（项目编号：{招标编号}）采购活动，全权代表本公司处理磋商过程的一切事宜，包括但不限于：提交响应文件、参与磋商、签约等。供应商授权代表在磋商过程中所签署的一切文件和处理与之有关的一切事务，本公司均予以认可并对此承担责任。供应商授权代表无转委托权。特此授权。

本授权书自出具之日起生效。

授权代表（或法定代表人）联系方式：{授权代表电话}

特此声明。

供应商签章：{公司名称}（单位盖章）
日期：{日期}

注：1. 本项目只允许有唯一的供应商授权代表，提供身份明证扫描件或影印件；
2. 法定代表人参加磋商的无需提供磋商授权书，提供身份证明扫描件或影印件。
"""

TEMPLATE_DEAL_COMMIT_NEW = """主要成交标的承诺函

我单位同意成交结果公告中公示以下主要成交标的信息并承诺：响应文件中所提供的主要成交标的信息均真实有效。若被发现存在任何虚假、隐瞒情况，我单位承担由此产生的一切后果。

名称：{项目名称}
服务范围：我方完全满足竞争性磋商文件要求
服务要求：我方完全满足竞争性磋商文件要求
服务时间：我方完全满足竞争性磋商文件要求
服务标准：我方完全满足竞争性磋商文件要求

供应商电子签章：{公司名称}（盖章）
日期：{日期}

备注：
1. 表中所列内容为满足本项目要求的主要成交标的信息；
2. 成交供应商提供的以上承诺情况，将按约定随成交结果公告同时公告；
3. 本页《主要成交标的承诺函》由供应商准确填写。
"""

TEMPLATE_LEGAL_PERSON_ID_NEW = """法定代表人（单位负责人）身份证明书

单位名称：{公司名称}
单位性质：{单位性质}
地　　址：{公司地址}
成立时间：{成立时间}
经营期限：{经营期限}
姓　　名：{法定代表人}　　性别：{法定代表人性别}　　年龄：{法定代表人年龄}　　职务：{法定代表人职务}

系{公司名称}的法定代表人（单位负责人）。

特此证明。

供应商：{公司名称}（盖章）
日　期：{日期}

附：法定代表人（单位负责人）身份证正反面复印件
"""

TEMPLATE_PRICE_TABLE = """1-1 报价表

项目名称：{项目名称}
项目编号：{招标编号}

| 供应商名称 | {公司名称} |
| --- | --- |
| 磋商范围 | 全部 |
| 报价（详见备注说明） | 大写：____<br>小写：____ |
| 备注说明 | ____ |

供应商电子签章：{公司名称}（盖章）

日期：{日期}

注：
1. 本表内容根据磋商文件要求包括了服务及其配套的设计、采购、制造、检测、试验、运输、保险、仓储、税费以及现场落地、安装及安装耗损、调试、培训、技术服务（包括技术资料、图纸的提供）质保期内的售后服务保障等所有费用。
2. 特殊事项在备注中注明。
3. 表中大写金额与小写金额不一致的，以大写金额为准。
4. 如供应商电子交易系统中填写的报价与响应文件中签章的报价表不一致，以响应文件中签章的报价表为准。
"""

TEMPLATE_QUALIFICATION_DECLARATION = """供应商资格声明书

致：{招标单位}

在参与本次项目磋商中，我单位承诺：

（一）具有良好的商业信誉和健全的财务会计制度；

（二）具有履行合同所必需的设备和专业技术能力；

（三）有依法缴纳税收和社会保障资金的良好记录；

（四）参加采购活动前三年内，在经营活动中没有重大违法记录（重大违法记录指因违法经营受到刑事处罚或者责令停产停业、吊销许可证或者执照、较大数额罚款等行政处罚，不包括因违法经营被禁止在一定期限内参加采购活动，但期限已经届满的情形）；

（五）我单位不存在为采购项目提供整体设计、规范编制或者项目管理、监理、检测等服务后，再参加该采购项目的其他采购活动的情形（单一来源采购项目除外）；

（六）我单位（含不具有独立法人资格的分支机构）无以下不良信用记录情形：
（1）被人民法院列入失信被执行人；
（2）被税务部门列入重大税收违法案件当事人名单；
（3）被政府采购监管部门列入政府采购严重违法失信行为记录名单。

（七）我单位不属于行政法规规定的公益一类事业单位、或使用事业编制且由财政拨款保障的群团组织；

（八）我单位无"单位负责人为同一人或者存在直接控股、管理关系的不同供应商，参加同一合同项下的采购活动"的情形。与我单位存在单位负责人为同一人或者存在直接控股、管理关系的其他法人单位信息如下（如有，不论其是否参加同一合同项下的采购活动均须填写）：

| 序号 | 单位名称 | 相互关系 |
| --- | --- | --- |
| 1 | ____ | ____ |
| 2 | ____ | ____ |

本单位对上述声明的真实性负责。如有虚假，将依法承担相应责任。

供应商电子签章：{公司名称}（盖章）

日期：{日期}
"""

TEMPLATE_BUSINESS_RESPONSE_TABLE = """商务响应表

| 序号 | 商务条款 | 磋商文件要求 | 供应商承诺 | 偏离说明 |
| --- | --- | --- | --- | --- |
| 1 | 付款方式 | 详见磋商文件 | 完全响应 | 无偏离 |
| 2 | 服务地点 | 详见磋商文件 | 完全响应 | 无偏离 |
| 3 | 服务期限 | 详见磋商文件 | 完全响应 | 无偏离 |
| 4 | 服务标准 | 详见磋商文件 | 完全响应 | 无偏离 |
| 5 | 验收方式 | 详见磋商文件 | 完全响应 | 无偏离 |

磋商文件中所列商务要求，我公司确认，对磋商文件所列商务要求，除以上响应表所列情况外，我方响应情况全部为"无偏离"。

供应商电子签章：{公司名称}（盖章）

日期：{日期}

注：
1. "无偏离"指与竞争性磋商文件要求一致，"正偏离"指优于竞争性磋商文件要求；"负偏离"指低于竞争性磋商文件要求。
2. 无论正偏离或负偏离，供应商均需在"供应商承诺"一栏中列明响应的详细内容，否则视同供应商响应情况为"无偏离"。
3. 如供应商未在上述偏离表中填写内容，视同供应商响应情况为"无偏离"。
"""

TEMPLATE_FINAL_PRICE_TABLE = """1-2 最后承诺报价表

（第　次报价书）

项目名称：{项目名称}
项目编号：{招标编号}

| 供应商名称 | {公司名称} |
| --- | --- |
| 磋商范围 | 全部 / 第　包 |
| 最后报价（详见备注说明） | 大写：____<br>小写：____ |
| 备注说明 | ____ |

供应商公章或授权代表签字：{公司名称}（盖章）

日期：{日期}

注：
1. 本页《报价表》由供应商在接到报价通知后依据磋商情况填写，并在规定时间内提交。考虑磋商报价的方便，供应商在填写最后承诺报价后，（第一次报价 - 最后承诺报价）除以第一次报价后得出的优惠率视同为需求表中全部分项设备、工程量或服务的优惠浮动值（特定分项优惠除外），而不考虑措施项目清单和规费税金清单的金额改变。此优惠率调整原则适用于合同内价格的计算及项目增减、变更时价格的计算。
2. 表中大写金额与小写金额不一致的，以大写金额为准。
3. 如供应商电子交易系统中填写的报价与提交的签章的最后承诺报价表不一致，以签章的最后承诺报价表为准。
"""


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ DB 不存在: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 备份原内容到本地文件，防误操作
    backup_path = os.path.join(
        os.path.dirname(DB_PATH),
        f"knowledge_template_backup_{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt",
    )
    with open(backup_path, "w", encoding="utf-8") as f:
        c.execute("SELECT id, title, content FROM knowledge_template WHERE id IN (2,3,11) ORDER BY id")
        for row in c.fetchall():
            f.write(f"=== id={row[0]} {row[1]} ===\n{row[2]}\n\n{'='*60}\n\n")
    print(f"✓ 原内容已备份至 {backup_path}")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── 修改 id=2 授权委托书 ──
    c.execute("UPDATE knowledge_template SET content=?, updated_at=? WHERE id=2",
              (TEMPLATE_AUTH_LETTER_NEW, now))
    print(f"✓ 修改 id=2 法定代表人授权委托书（去硬编码电话）")

    # ── 修改 id=3 主要成交标的承诺函 ──
    c.execute("UPDATE knowledge_template SET content=?, updated_at=? WHERE id=3",
              (TEMPLATE_DEAL_COMMIT_NEW, now))
    print(f"✓ 修改 id=3 主要成交标的承诺函（补签章字段）")

    # ── 修改 id=11 法定代表人身份证明书 ──
    c.execute("UPDATE knowledge_template SET content=?, updated_at=? WHERE id=11",
              (TEMPLATE_LEGAL_PERSON_ID_NEW, now))
    print(f"✓ 修改 id=11 法定代表人身份证明书（去 5 处硬编码）")

    # ── 新增 id=13 报价表 + id=14 最后承诺报价表 ──
    c.execute("SELECT id FROM knowledge_template WHERE id=13")
    if c.fetchone():
        c.execute("UPDATE knowledge_template SET title=?, content=?, category=?, tags=?, updated_at=? WHERE id=13",
                  ("报价表（通用模板）", TEMPLATE_PRICE_TABLE, "PRICE", "报价表,响应报价,通用模板", now))
        print(f"✓ 更新 id=13 报价表（通用模板）")
    else:
        c.execute("""
            INSERT INTO knowledge_template (id, title, category, content, tags, usage_count,
                                            created_at, updated_at, is_deleted)
            VALUES (13, ?, 'PRICE', ?, '报价表,响应报价,通用模板', 0, ?, ?, 0)
        """, ("报价表（通用模板）", TEMPLATE_PRICE_TABLE, now, now))
        print(f"✓ 新增 id=13 报价表（通用模板）")

    c.execute("SELECT id FROM knowledge_template WHERE id=14")
    if c.fetchone():
        c.execute("UPDATE knowledge_template SET title=?, content=?, category=?, tags=?, updated_at=? WHERE id=14",
                  ("最后承诺报价表（通用模板）", TEMPLATE_FINAL_PRICE_TABLE, "PRICE", "最后承诺报价表,最后报价,通用模板", now))
        print(f"✓ 更新 id=14 最后承诺报价表（通用模板）")
    else:
        c.execute("""
            INSERT INTO knowledge_template (id, title, category, content, tags, usage_count,
                                            created_at, updated_at, is_deleted)
            VALUES (14, ?, 'PRICE', ?, '最后承诺报价表,最后报价,通用模板', 0, ?, ?, 0)
        """, ("最后承诺报价表（通用模板）", TEMPLATE_FINAL_PRICE_TABLE, now, now))
        print(f"✓ 新增 id=14 最后承诺报价表（通用模板）")

    # ── 新增 id=15 供应商资格声明书 ──
    c.execute("SELECT id FROM knowledge_template WHERE id=15")
    if c.fetchone():
        c.execute("UPDATE knowledge_template SET title=?, content=?, category=?, tags=?, updated_at=? WHERE id=15",
                  ("供应商资格声明书（通用模板）", TEMPLATE_QUALIFICATION_DECLARATION, "COMMITMENT", "供应商资格,资格声明,声明书,通用模板", now))
        print(f"✓ 更新 id=15 供应商资格声明书（通用模板）")
    else:
        c.execute("""
            INSERT INTO knowledge_template (id, title, category, content, tags, usage_count,
                                            created_at, updated_at, is_deleted)
            VALUES (15, ?, 'COMMITMENT', ?, '供应商资格,资格声明,声明书,通用模板', 0, ?, ?, 0)
        """, ("供应商资格声明书（通用模板）", TEMPLATE_QUALIFICATION_DECLARATION, now, now))
        print(f"✓ 新增 id=15 供应商资格声明书（通用模板）")

    # ── 新增 id=16 商务响应表 ──
    c.execute("SELECT id FROM knowledge_template WHERE id=16")
    if c.fetchone():
        c.execute("UPDATE knowledge_template SET title=?, content=?, category=?, tags=?, updated_at=? WHERE id=16",
                  ("商务响应表（通用模板）", TEMPLATE_BUSINESS_RESPONSE_TABLE, "COMMITMENT", "商务响应表,商务条款,通用模板", now))
        print(f"✓ 更新 id=16 商务响应表（通用模板）")
    else:
        c.execute("""
            INSERT INTO knowledge_template (id, title, category, content, tags, usage_count,
                                            created_at, updated_at, is_deleted)
            VALUES (16, ?, 'COMMITMENT', ?, '商务响应表,商务条款,通用模板', 0, ?, ?, 0)
        """, ("商务响应表（通用模板）", TEMPLATE_BUSINESS_RESPONSE_TABLE, now, now))
        print(f"✓ 新增 id=16 商务响应表（通用模板）")

    conn.commit()
    conn.close()
    print("\n✓ 全部完成")


if __name__ == "__main__":
    main()
