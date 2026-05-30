import sqlite3
import requests
import json
import time

# 配置
DB_PATH = "poetry.db"
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

def translate_poem(content):
    prompt = f"你是一个精通中国古典文学的专家。请将以下古诗词翻译成现代白话文，要求准确、优美，只返回翻译内容，不要有任何多余的解释：\n\n{content}"
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=30)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"翻译出错: {e}")
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 查找没有翻译的诗词 (先限制10个作为测试)
    cursor.execute("SELECT id, title, author, paragraphs FROM poems WHERE translation_baihua IS NULL LIMIT 10")
    poems = cursor.fetchall()

    if not poems:
        print("没有找到需要翻译的诗词。")
        return

    print(f"开始翻译 {len(poems)} 首诗词...")

    for poem in poems:
        pid = poem['id']
        title = poem['title']
        author = poem['author']
        content = poem['paragraphs']
        
        print(f"正在翻译: [{author}] {title}...")
        print(f"原文:\n{content}")
        
        translation = translate_poem(content)
        
        if translation:
            cursor.execute("UPDATE poems SET translation_baihua = ? WHERE id = ?", (translation, pid))
            conn.commit()
            print(f"翻译结果:\n{translation}")
            print("-" * 30)
        else:
            print(f"跳过: {title}")
        
        # 稍微停顿一下，避免压力过大 (虽然是本地，但也建议加上)
        time.sleep(0.5)

    conn.close()
    print("翻译任务结束。")

if __name__ == "__main__":
    main()
