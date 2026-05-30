import sqlite3

DB_PATH = "C:/Users/15322/poetry_deploy/poetry.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 搜索赤壁赋的开头名句
    print("正在通过内容搜索《赤壁赋》...")
    cursor.execute("SELECT title, author, paragraphs FROM poems WHERE paragraphs LIKE '%壬戌之秋%'")
    results = cursor.fetchall()
    if results:
        for r in results:
            print(f"找到作品：{r[0]} | 作者：{r[1]}")
            print(f"内容预览：{r[2][:100]}...")
    else:
        print("内容搜索未找到《赤壁赋》。")
        
    # 看看库里到底有多少个表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print("\n数据库中的表：", [r[0] for r in cursor.fetchall()])
            
    conn.close()

if __name__ == "__main__":
    main()
