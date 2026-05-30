# -*- coding: utf-8 -*-
import sqlite3
import json

db_path = "/home/ibalamayaka_gmail_com/poetry_site/poetry.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT id, title, paragraphs FROM poems WHERE author LIKE '%李清照%' AND (translation_baihua IS NULL OR translation_baihua = '')")
rows = cur.fetchall()

print(f"TOTAL_COUNT:{len(rows)}")

# Output first batch to process
batch = rows[:30]
print("BATCH_DATA:" + json.dumps(batch, ensure_ascii=False))

conn.close()
