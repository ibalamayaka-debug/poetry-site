# -*- coding: utf-8 -*-
import sqlite3

db_path = "/home/ibalamayaka_gmail_com/poetry_site/poetry.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

data = [
    ("登鹳雀楼", "王之涣", "夕阳依傍着西山慢慢地沉没，滔滔黄河水朝着东海汹涌奔流。若想把千里的风光景物看够，那就要登上更高的一层城楼。"),
    ("春晓", "孟浩然", "春天睡醒不觉天已大亮，到处是鸟儿清脆的叫声。回想昨夜的阵阵风雨声，吹落了多少娇美的春花。"),
    ("望庐山瀑布", "李白", "香炉峰在阳光的照射下生起紫色烟霞，远远望见瀑布似白色绢绸悬挂在山前。高崖上飞腾直落的瀑布好像有几千尺，让人恍惚以为银河从天上泻落到人间。")
]

updated = 0
for title, author, trans in data:
    # Use LIKE for encoding robustness
    cur.execute("UPDATE poems SET translation_baihua = ? WHERE title LIKE ? AND author LIKE ?", (trans, f"%{title}%", f"%{author}%"))
    if cur.rowcount > 0:
        updated += cur.rowcount

conn.commit()
print(f"Batch updated {updated} entries.")
conn.close()
