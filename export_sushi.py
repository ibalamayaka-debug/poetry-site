# -*- coding: utf-8 -*-
import sqlite3
import json
import os

db_path = "/home/ibalamayaka_gmail_com/poetry_site/poetry.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get all untranslated poems by Su Shi (苏轼)
cur.execute("SELECT id, title, paragraphs FROM poems WHERE author LIKE '%苏轼%' AND (translation_baihua IS NULL OR translation_baihua = '') LIMIT 200")
rows = [dict(zip(['id', 'title', 'paragraphs'], row)) for row in cur.fetchall()]

with open("sushi_poems.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

conn.close()
print(f"SUCCESS: sushi_poems.json created with {len(rows)} poems.")
