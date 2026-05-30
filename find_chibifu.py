import sqlite3

DB_PATH = "C:/Users/15322/poetry_deploy/poetry.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 模糊匹配 苏轼 和 赤壁
    cursor.execute("SELECT title FROM poems WHERE author = '苏轼' AND title LIKE '%赤壁%'")
    results = cursor.fetchall()
    print("找到的相关标题：")
    for r in results:
        print(r[0])
    
    # 如果没找到，看看苏轼最长的几篇作品标题
    if not results:
        print("\n没找到标题含'赤壁'的作品，列出苏轼的前20个作品：")
        cursor.execute("SELECT title FROM poems WHERE author = '苏轼' LIMIT 20")
        for r in cursor.fetchall():
            print(r[0])
            
    conn.close()

if __name__ == "__main__":
    main()
