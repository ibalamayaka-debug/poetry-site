# -*- coding: utf-8 -*-
import sqlite3
import json
import os

db_path = "/home/ibalamayaka_gmail_com/poetry_site/poetry.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT id, title, paragraphs FROM poems WHERE author LIKE '%李清照%' AND (translation_baihua IS NULL OR translation_baihua = '')")
rows = [dict(zip(['id', 'title', 'paragraphs'], row)) for row in cur.fetchall()]

with open("lqz_poems.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

conn.close()
print("SUCCESS: lqz_poems.json created")
