import json

with open('C:/Users/15322/poetry_deploy/sushi_poems.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

subset = data[100:150]

with open('C:/Users/15322/poetry_deploy/subset.json', 'w', encoding='utf-8') as f:
    json.dump(subset, f, ensure_ascii=False, indent=2)
