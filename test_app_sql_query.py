# -*- coding: utf-8 -*-
import sqlite3
import time

db_path = "/home/ibalamayaka_gmail_com/poetry_site/poetry.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

q_variants = ['静夜思', '靜夜思']
match_parts = ["poems_fts MATCH ?" for _ in q_variants]
fts_clause = "poems.id IN (SELECT rowid FROM poems_fts WHERE " + " OR ".join(match_parts) + ")"

like_parts = []
for _ in q_variants:
    like_parts.append("poems.title LIKE ?")
    like_parts.append("poems.paragraphs LIKE ?")

where_sql = "WHERE (" + fts_clause + " OR " + " OR ".join(like_parts) + ")"
params = []
params.extend([f'"{v}"' for v in q_variants])
for v in q_variants:
    params.append(f"%{v}%")
    params.append(f"%{v}%")

query_sql = f"""
    WITH filtered AS (
        SELECT id, dynasty, author, title, paragraphs, category, translation_baihua, appreciation
        FROM poems
        {where_sql}
    ), ranked AS (
        SELECT *,
            ROW_NUMBER() OVER (
                PARTITION BY title, paragraphs
                ORDER BY id DESC
            ) AS rn
        FROM filtered
    )
    SELECT id, dynasty, author, title, paragraphs, category, translation_baihua, appreciation
    FROM ranked
    WHERE rn = 1
    ORDER BY id DESC
    LIMIT ? OFFSET ?
"""
print("Executing Query SQL...")
t0 = time.time()
res = cur.execute(query_sql, [*params, 20, 0]).fetchall()
print(f"Total: {len(res)} in {time.time()-t0:.2f}s")
conn.close()
