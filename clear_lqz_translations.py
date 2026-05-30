# -*- coding: utf-8 -*-
import sqlite3

db_path = "/home/ibalamayaka_gmail_com/poetry_site/poetry.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get count before update
cur.execute("SELECT COUNT(*) FROM poems WHERE author LIKE '%李清照%' AND translation_baihua IS NOT NULL AND translation_baihua != ''")
count_before = cur.fetchone()[0]
print(f"Translations before update: {count_before}")

# Clear translations for all Li Qingzhao poems EXCEPT 声声慢
cur.execute("""
    UPDATE poems 
    SET translation_baihua = NULL 
    WHERE author LIKE '%李清照%' 
    AND title NOT LIKE '%声声慢%'
""")

rows_affected = cur.rowcount
conn.commit()

# Get count after update
cur.execute("SELECT COUNT(*) FROM poems WHERE author LIKE '%李清照%' AND translation_baihua IS NOT NULL AND translation_baihua != ''")
count_after = cur.fetchone()[0]

print(f"Rows updated (translations removed): {rows_affected}")
print(f"Translations remaining: {count_after}")

conn.close()
