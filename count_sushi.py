# -*- coding: utf-8 -*-
import sqlite3

db_path = "/home/ibalamayaka_gmail_com/poetry_site/poetry.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM poems WHERE author LIKE '%苏轼%' AND (translation_baihua IS NULL OR translation_baihua = '')")
count = cur.fetchone()[0]

print(f"Remaining untranslated Su Shi poems: {count}")
conn.close()
