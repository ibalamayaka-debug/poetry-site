import sqlite3
import requests
import json

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

    # 选取几首有代表性的苏轼作品
    targets = ["题西林壁", "饮湖上初晴后雨二首其二", "念奴娇·赤壁怀古", "水调歌头·明月几时有"]
    
    print(f"正在获取并翻译苏轼的作品...\n")
    
    for title in targets:
        cursor.execute("SELECT id, title, paragraphs FROM poems WHERE author = '苏轼' AND title LIKE ? LIMIT 1", (f"%{title}%",))
        poem = cursor.fetchone()
        
        if poem:
            content = poem['paragraphs']
            print(f"【{poem['title']}】")
            print(f"原文：\n{content}")
            
            translation = translate_poem(content)
            if translation:
                print(f"Qwen 翻译：\n{translation}")
                # 更新数据库
                cursor.execute("UPDATE poems SET translation_baihua = ? WHERE id = ?", (translation, poem['id']))
                conn.commit()
            print("-" * 50)
        else:
            print(f"未找到诗词：{title}")

    conn.close()

if __name__ == "__main__":
    main()
