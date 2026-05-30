# -*- coding: utf-8 -*-
import sqlite3

db_path = "/home/ibalamayaka_gmail_com/poetry_site/poetry.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# ID 398655: 静夜思
translation1 = "明亮的月光洒在床前的窗户纸上，好像地上泛起了一层霜。我禁不住抬起头来，看那天窗外空中的一轮明月，不由得低头沉思，想起远方的家乡。"
cur.execute("UPDATE poems SET translation_baihua = ? WHERE id = 398655", (translation1,))

conn.commit()
print("Translations added successfully by ID.")
conn.close()
