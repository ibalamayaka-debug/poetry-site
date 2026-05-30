import sqlite3
import requests

DB_PATH = "C:/Users/15322/poetry_deploy/poetry.db"
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

def translate_poem(content):
    # 对于赤壁赋这种长篇，我们稍微调整下 prompt
    prompt = f"你是一个精通中国古典文学的专家。请将以下著名的《赤壁赋》翻译成现代白话文。要求准确、文辞优美，保持原文的意境，只返回翻译内容，不要有任何解释：\n\n{content}"
    payload = {"model": MODEL_NAME, "prompt": prompt, "stream": False}
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=60)
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"翻译过程中出错: {e}")
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("正在库中检索苏轼的《赤壁赋》...\n")
    # 搜索包含“赤壁赋”的题目
    cursor.execute("SELECT id, title, paragraphs FROM poems WHERE author = '苏轼' AND title LIKE '%赤壁赋%' LIMIT 2")
    poems = cursor.fetchall()
    
    if not poems:
        print("数据库中没有找到《赤壁赋》。")
        return

    for poem in poems:
        title = poem['title']
        content = poem['paragraphs']
        print(f"【{title}】")
        # 如果太长，只打印开头预览
        preview = content[:200] + "..." if len(content) > 200 else content
        print(f"原文预览：\n{preview}\n")
        
        print(f"正在使用 Qwen 进行全文翻译，请稍候...\n")
        translation = translate_poem(content)
        if translation:
            print(f"Qwen 翻译结果：\n{translation}")
            cursor.execute("UPDATE poems SET translation_baihua = ? WHERE id = ?", (translation, poem['id']))
            conn.commit()
            print("\n" + "="*50 + "\n")
        else:
            print(f"翻译失败：{title}")

    conn.close()

if __name__ == "__main__":
    main()
