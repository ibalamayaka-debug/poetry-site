# -*- coding: utf-8 -*-
import sqlite3

db_path = "/home/ibalamayaka_gmail_com/poetry_site/poetry.db"
print("Connecting to DB...")
conn = sqlite3.connect(db_path)
print("Rebuilding FTS5 index... This might take a minute.")
conn.execute("INSERT INTO poems_fts(poems_fts) VALUES('rebuild')")
conn.commit()
print("Rebuild complete!")
conn.close()
