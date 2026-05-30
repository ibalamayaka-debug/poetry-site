import sqlite3
import libsql
import os
import sys

# Configure the local DB path dynamically to work in both Windows and WSL
current_dir = os.path.dirname(os.path.abspath(__file__))
LOCAL_DB = os.path.join(current_dir, "poetry.db")

TURSO_URL = "libsql://my-poetry-db-ymxl97.aws-ap-south-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3ODAxMTMzNzksImlkIjoiMDE5ZTc3MDItZTgwMS03OWFhLThjMDctMjE2MjViYTBjNDBiIiwicmlkIjoiODljYzEyZDgtMmJhNi00OTdmLTliNDYtYTE3MzJmNjA4YTUwIn0.aEF2fho3ia3x9pYCXqtPcxulT6drNH_f8qFN-VDedlsREVf5hbyTbRVl8ncir9wvK0A_r4JwU2C8sVddBawMDw"

BATCH_SIZE = 500

def sync():
    # 1. 连接本地库
    local_conn = sqlite3.connect(LOCAL_DB)
    local_conn.row_factory = sqlite3.Row
    local_cur = local_conn.cursor()

    # 2. 连接云端 Turso
    print("正在连接云端 Turso 数据库...")
    remote_conn = libsql.connect(TURSO_URL, auth_token=TURSO_TOKEN)
    remote_cur = remote_conn.cursor()

    # 3. 在云端建表 (如果不存在)
    print("正在初始化云端表结构...")
    remote_cur.execute("""
        CREATE TABLE IF NOT EXISTS poems (
            id INTEGER PRIMARY KEY,
            dynasty TEXT,
            author TEXT,
            title TEXT,
            paragraphs TEXT,
            category TEXT,
            source_file TEXT,
            raw_json TEXT,
            translation_baihua TEXT,
            appreciation TEXT
        )
    """)

    # 4. 获取本地数据总数
    local_cur.execute("SELECT COUNT(*) FROM poems")
    total = local_cur.fetchone()[0]
    print(f"本地共有 {total} 首诗词待同步。")

    # 5. 分块同步
    print(f"开始同步 (每批 {BATCH_SIZE} 条)...")
    offset = 0
    while True:
        local_cur.execute(f"SELECT * FROM poems LIMIT {BATCH_SIZE} OFFSET {offset}")
        rows = local_cur.fetchall()
        if not rows:
            break
        
        # 转换数据格式
        data = [tuple(row) for row in rows]
        
        # 生成占位符
        placeholders = ",".join(["?" for _ in range(len(rows[0]))])
        
        try:
            remote_cur.executemany(f"INSERT OR REPLACE INTO poems VALUES ({placeholders})", data)
            remote_conn.commit()
            offset += len(rows)
            sys.stdout.write(f"\r进度: {offset}/{total} ({(offset/total*100):.2f}%)")
            sys.stdout.flush()
        except Exception as e:
            print(f"\n[错误] 同步出错: {e}")
            break

    print("\n同步完成！")
    local_conn.close()
    remote_conn.close()

if __name__ == "__main__":
    sync()
