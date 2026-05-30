# -*- coding: utf-8 -*-
import sqlite3

db_path = "/home/ibalamayaka_gmail_com/poetry_site/poetry.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

q_variants = ["静夜思", "靜夜思"]
sql = "SELECT rowid FROM poems_fts WHERE poems_fts MATCH ? OR poems_fts MATCH ?"
print("Executing FTS OR query...")
res = cur.execute(sql, q_variants).fetchall()
print(f"Found {len(res)} results.")
conn.close()
