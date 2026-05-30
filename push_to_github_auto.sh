#!/bin/bash

echo "🚀 开始配置 Git 并推送到 GitHub..."

cd /mnt/c/Users/15322/poetry_deploy

if [ ! -d ".git" ]; then
    echo "📦 初始化 Git 仓库..."
    git init
else
    echo "✅ Git 仓库已存在。"
fi

echo "🛡️ 配置 .gitignore (防止上传大文件和临时文件)..."
cat << EOF > .gitignore
poetry.db
poetry.db-journal
poetry_dump.sql
poetry_dump.sq
venv/
__pycache__/
*.pyc
.pytest_cache/
.aidex/
.vscode/
.DS_Store
*.zip
*.log
EOF

# 强制更新远程仓库地址
echo "🔗 配置远端仓库地址..."
git remote remove origin 2>/dev/null
git remote add origin git@github.com:ibalamayaka-debug/poetry-site.git
git branch -M main

echo "📝 添加文件并提交..."
git add .
git commit -m "feat: 准备部署到 Vercel (对接 Turso 数据库)"

echo "⬆️ 正在推送到 GitHub..."
# 设置超时时间防止无限卡住，并使用 SSH
GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new" git push -u origin main

if [ $? -eq 0 ]; then
    echo "🎉 恭喜！代码已成功推送到 GitHub。"
else
    echo "❌ 推送失败。可能是 SSH 密钥未配置，请检查。"
fi
