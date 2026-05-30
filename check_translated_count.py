import sqlite3

DB_PATH = "C:/Users/15322/poetry_deploy/poetry.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM poems WHERE translation_baihua IS NOT NULL AND translation_baihua != ''")
    count = cursor.fetchone()[0]
    conn.close()
    print(f"Total translated: {count}")

if __name__ == "__main__":
    main()
