import sqlite3
import requests

DB_PATH = "C:/Users/15322/poetry_deploy/poetry.db"
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

def translate_poem(content):
    prompt = f"你是一个精通中国古典文学的专家。请将以下著名的苏轼《前赤壁赋》翻译成现代白话文。要求准确、文辞优美，保持原文的哲学意境，只返回翻译内容，不要有任何多余的解释：\n\n{content}"
    payload = {"model": MODEL_NAME, "prompt": prompt, "stream": False}
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=120)
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"翻译过程中出错: {e}")
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("正在翻译苏轼的《前赤壁赋》...\n")
    # 使用刚才找到的确切标题和作者
    cursor.execute("SELECT id, title, paragraphs FROM poems WHERE title = '前赤壁賦' AND author LIKE '%蘇軾%'")
    poem = cursor.fetchone()
    
    if not poem:
        print("未能在数据库中定位到《前赤壁赋》。")
        return

    content = poem['paragraphs']
    print(f"【{poem['title']}】")
    print("-" * 30)
    
    translation = translate_poem(content)
    if translation:
        print(f"Qwen 翻译结果：\n\n{translation}")
        # 更新数据库
        cursor.execute("UPDATE poems SET translation_baihua = ? WHERE id = ?", (translation, poem['id']))
        conn.commit()
    else:
        print("翻译失败。")

    conn.close()

if __name__ == "__main__":
    main()
