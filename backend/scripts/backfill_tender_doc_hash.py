"""为现有 tender_document 记录回填 file_hash（SHA256）

幂等：已有 hash 的记录跳过；找不到本地物理文件的记录跳过

执行：cd backend && python3 scripts/backfill_tender_doc_hash.py
"""

import hashlib
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "bid.db")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "uploads")


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ DB 不存在: {DB_PATH}"); sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 确保 file_hash 列存在
    c.execute("PRAGMA table_info(tender_document)")
    cols = [r[1] for r in c.fetchall()]
    if "file_hash" not in cols:
        c.execute("ALTER TABLE tender_document ADD COLUMN file_hash VARCHAR(64)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_tender_document_file_hash ON tender_document(file_hash)")
        print("✓ 列 file_hash + 索引已建")

    c.execute("SELECT id, stored_path FROM tender_document WHERE file_hash IS NULL AND is_deleted=0")
    rows = c.fetchall()
    if not rows:
        print("无需回填")
        return

    backfilled, skipped = 0, 0
    for did, sp in rows:
        abs_path = os.path.join(UPLOAD_DIR, sp)
        if not os.path.exists(abs_path):
            print(f"  跳过 id={did}（文件不存在: {sp}）")
            skipped += 1
            continue
        with open(abs_path, "rb") as f:
            fhash = hashlib.sha256(f.read()).hexdigest()
        c.execute("UPDATE tender_document SET file_hash=? WHERE id=?", (fhash, did))
        backfilled += 1

    conn.commit()
    print(f"\n✓ 回填 {backfilled} 条；跳过 {skipped} 条（物理文件不存在）")


if __name__ == "__main__":
    main()
