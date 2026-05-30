import sqlite3
import requests
import time
import sys

# 配置
DB_PATH = "C:/Users/15322/poetry_deploy/poetry.db"
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"
BATCH_SIZE = 50  # 每批处理50首

def translate_poem(content):
    # 强调“白话一点”和“通俗易懂”
    prompt = (
        "你是一个精通中国古典文学的专家。请将以下古诗词翻译成现代白话文。\n"
        "要求：语言要通俗易懂、口语化一点，像讲故事一样自然，但要准确保留原意。\n"
        "只返回翻译后的白话文内容，不要有任何引言、解释或评论。\n\n"
        f"{content}"
    )
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"\n[错误] 翻译请求失败: {e}")
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 统计剩余待翻译数量
    cursor.execute("SELECT COUNT(*) FROM poems WHERE translation_baihua IS NULL OR translation_baihua = ''")
    total_remaining = cursor.fetchone()[0]
    
    if total_remaining == 0:
        print("所有诗词已翻译完成！")
        return

    print(f"检测到共有 {total_remaining} 首诗词待翻译。")
    print(f"正在以每批 {BATCH_SIZE} 首的速度开始全自动翻译（翻译风格：通俗白话）...")
    print("按 Ctrl+C 可随时停止。\n")

    count = 0
    try:
        while True:
            cursor.execute(
                "SELECT id, title, author, paragraphs FROM poems "
                "WHERE translation_baihua IS NULL OR translation_baihua = '' "
                "LIMIT ?", (BATCH_SIZE,)
            )
            batch = cursor.fetchall()
            
            if not batch:
                break
                
            for poem in batch:
                pid = poem['id']
                title = poem['title']
                author = poem['author']
                content = poem['paragraphs']
                
                # 过滤掉一些无效内容
                if not content or len(content.strip()) < 5:
                    cursor.execute("UPDATE poems SET translation_baihua = '[暂无有效内容]' WHERE id = ?", (pid,))
                    conn.commit()
                    continue

                sys.stdout.write(f"\r正在翻译({count+1}/{total_remaining}): [{author}] {title} ... ")
                sys.stdout.flush()
                
                translation = translate_poem(content)
                
                if translation:
                    cursor.execute("UPDATE poems SET translation_baihua = ? WHERE id = ?", (translation, pid))
                    conn.commit()
                    count += 1
                else:
                    # 失败了稍微等一下再试
                    time.sleep(2)
            
            # 每批完成后的状态输出
            print(f"\n已完成一批 {len(batch)} 首。")
            
    except KeyboardInterrupt:
        print("\n用户停止了任务。")
    finally:
        conn.close()
        print(f"\n任务结束，本次共成功翻译并存入 {count} 首诗词。")

if __name__ == "__main__":
    main()
