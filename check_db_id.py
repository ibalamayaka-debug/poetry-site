# -*- coding: utf-8 -*-
import sqlite3
import json

db_path = "/home/ibalamayaka_gmail_com/poetry_site/poetry.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ID 398655: 静夜思
row = cur.execute("SELECT * FROM poems WHERE id = 398655").fetchone()
if row:
    print(json.dumps(dict(row), ensure_ascii=False))
else:
    print("Not found.")

conn.close()
