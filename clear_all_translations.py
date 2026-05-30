# -*- coding: utf-8 -*-
import sqlite3

db_path = "/home/ibalamayaka_gmail_com/poetry_site/poetry.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get count before update
cur.execute("SELECT COUNT(*) FROM poems WHERE translation_baihua IS NOT NULL AND translation_baihua != ''")
count_before = cur.fetchone()[0]
print(f"Translations before update: {count_before}")

# Clear all translations
cur.execute("UPDATE poems SET translation_baihua = NULL")
rows_affected = cur.rowcount
conn.commit()

print(f"Rows updated (translations removed): {rows_affected}")

conn.close()
