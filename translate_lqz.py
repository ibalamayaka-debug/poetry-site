import sqlite3
import requests

DB_PATH = "C:/Users/15322/poetry_deploy/poetry.db"
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

def translate_poem(content):
    prompt = f"你是一个精通中国古典文学的专家。请将以下古诗词翻译成现代白话文，要求准确、优美，只返回翻译内容，不要有任何多余的解释：\n\n{content}"
    payload = {"model": MODEL_NAME, "prompt": prompt, "stream": False}
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=30)
        return response.json().get("response", "").strip()
    except:
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("正在库中检索李清照的作品...\n")
    # 选取李清照的5首作品
    cursor.execute("SELECT id, title, paragraphs FROM poems WHERE author = '李清照' LIMIT 5")
    poems = cursor.fetchall()
    
    if not poems:
        print("数据库中没有找到作者为 '李清照' 的诗词。")
        return

    for poem in poems:
        title = poem['title']
        content = poem['paragraphs']
        print(f"【{title}】")
        print(f"原文：\n{content}")
        
        translation = translate_poem(content)
        if translation:
            print(f"Qwen 翻译：\n{translation}")
            cursor.execute("UPDATE poems SET translation_baihua = ? WHERE id = ?", (translation, poem['id']))
            conn.commit()
        print("-" * 50)

    conn.close()

if __name__ == "__main__":
    main()
