# -*- coding: utf-8 -*-
import sqlite3

db_path = r"C:\Users\15322\poetry_deploy\poetry.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check if columns exist
cur.execute("PRAGMA table_info(poems)")
columns = [row[1] for row in cur.fetchall()]
if 'translation_baihua' not in columns:
    cur.execute("ALTER TABLE poems ADD COLUMN translation_baihua TEXT")
if 'appreciation' not in columns:
    cur.execute("ALTER TABLE poems ADD COLUMN appreciation TEXT")

conn.commit()

# Update 静夜思
translation1 = "明亮的月光洒在床前的窗户纸上，好像地上泛起了一层霜。我禁不住抬起头来，看那天窗外空中的一轮明月，不由得低头沉思，想起远方的家乡。"
cur.execute("UPDATE poems SET translation_baihua = ? WHERE title = '静夜思' AND author = '李白'", (translation1,))

# Update 登鹳雀楼
translation2 = "夕阳依傍着西山慢慢地沉没，滔滔黄河水朝着东海汹涌奔流。若想把千里的风光景物看够，那就要登上更高的一层城楼。"
cur.execute("UPDATE poems SET translation_baihua = ? WHERE title = '登鹳雀楼' AND author = '王之涣'", (translation2,))

# Update 春晓
translation3 = "春天睡醒不觉天已大亮，到处是鸟儿清脆的叫声。回想昨夜的阵阵风雨声，吹落了多少娇美的春花。"
cur.execute("UPDATE poems SET translation_baihua = ? WHERE title = '春晓' AND author = '孟浩然'", (translation3,))

# Update 望庐山瀑布
translation4 = "香炉峰在阳光的照射下生起紫色烟霞，远远望见瀑布似白色绢绸悬挂在山前。高崖上飞腾直落的瀑布好像有几千尺，让人恍惚以为银河从天上泻落到人间。"
cur.execute("UPDATE poems SET translation_baihua = ? WHERE title = '望庐山瀑布' AND author = '李白'", (translation4,))

conn.commit()
print("Translations added successfully.")

cur.execute("SELECT title, author, translation_baihua FROM poems WHERE translation_baihua IS NOT NULL")
for row in cur.fetchall():
    print(f"{row[0]} ({row[1]}): {row[2][:15]}...")

conn.close()
