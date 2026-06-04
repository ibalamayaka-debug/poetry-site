import sqlite3
import libsql
import os
import sys
import time

# ==================== 配置 ====================
current_dir = os.path.dirname(os.path.abspath(__file__))

# 支持通过环境变量指定本地数据库路径（用户可以设置 LOCAL_POETRY_DB）
LOCAL_DB = os.environ.get("LOCAL_POETRY_DB") or os.path.join(current_dir, "poetry.db")

TURSO_URL = os.environ.get("TURSO_DATABASE_URL") or "libsql://my-poetry-db-ymxl97.aws-ap-south-1.turso.io"
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

BATCH_SIZE = 800
MAX_RETRIES = 3
# =============================================

if not TURSO_TOKEN:
    print("❌ 错误: 未设置 TURSO_AUTH_TOKEN 环境变量")
    sys.exit(1)

def sync():
    print("🚀 开始同步本地 → Turso")
    print(f"📁 本地数据库路径: {LOCAL_DB}")

    # 连接本地
    if not os.path.exists(LOCAL_DB):
        print(f"❌ 错误: 本地数据库不存在: {LOCAL_DB}")
        print("请确认路径正确，或先将 poetry.db 放到正确位置")
        return

    local_conn = sqlite3.connect(LOCAL_DB)
    local_conn.row_factory = sqlite3.Row
    local_cur = local_conn.cursor()

    # 检查表是否存在
    local_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='poems'")
    if not local_cur.fetchone():
        print("❌ 错误: 本地数据库中没有 poems 表")
        print("请先运行导入脚本创建表和导入数据，或检查数据库文件是否正确")
        local_conn.close()
        return

    # 连接云端
    print("正在连接 Turso 云数据库...")
    for attempt in range(MAX_RETRIES):
        try:
            remote_conn = libsql.connect(TURSO_URL, auth_token=TURSO_TOKEN)
            remote_cur = remote_conn.cursor()
            print("✅ 云端连接成功")
            break
        except Exception as e:
            print(f"连接失败 ({attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(2)
    else:
        print("❌ 无法连接 Turso")
        local_conn.close()
        return

    # 建表（云端）
    remote_cur.execute("""
        CREATE TABLE IF NOT EXISTS poems (
            id INTEGER PRIMARY KEY,
            dynasty TEXT, author TEXT, title TEXT, paragraphs TEXT,
            category TEXT, source_file TEXT, raw_json TEXT,
            translation_baihua TEXT, appreciation TEXT
        )
    """)
    remote_conn.commit()

    # 获取本地最大 id 和云端最大 id（实现增量同步）
    local_cur.execute("SELECT MAX(id) FROM poems")
    local_max = local_cur.fetchone()[0] or 0

    remote_cur.execute("SELECT MAX(id) FROM poems")
    remote_max = remote_cur.fetchone()[0] or 0

    print(f"本地最大 id: {local_max} | 云端最大 id: {remote_max}")

    if local_max <= remote_max:
        print("✅ 本地数据已全部同步或更旧，无需同步")
        local_conn.close()
        remote_conn.close()
        return

    # 分批同步新增数据
    offset = 0
    total_new = local_max - remote_max
    synced = 0

    print(f"开始增量同步 {total_new} 条数据...")

    while True:
        local_cur.execute(f"""
            SELECT * FROM poems 
            WHERE id > ? 
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """, (remote_max,))
        
        rows = local_cur.fetchall()
        if not rows:
            break

        data = [tuple(row) for row in rows]
        placeholders = ",".join(["?" for _ in range(len(rows[0]))])

        try:
            remote_cur.executemany(f"INSERT OR REPLACE INTO poems VALUES ({placeholders})", data)
            remote_conn.commit()
            
            synced += len(rows)
            offset += len(rows)
            progress = (synced / total_new) * 100
            sys.stdout.write(f"\r进度: {synced}/{total_new} ({progress:.1f}%)")
            sys.stdout.flush()
        except Exception as e:
            print(f"\n❌ 同步出错: {e}")
            time.sleep(1)

    print("\n\n🎉 同步完成！")
    local_conn.close()
    remote_conn.close()

if __name__ == "__main__":
    sync()