#!/bin/bash

# 确保遇到错误时停止执行
set -e

echo "🚀 开始配置 Git 并推送到 GitHub (使用 HTTPS)..."

# 1. 切换到项目目录
cd /mnt/c/Users/15322/poetry_deploy

# 2. 解决 WSL 经常遇到的安全目录报错问题
echo "⚙️ 配置 Git 安全目录..."
git config --global --add safe.directory /mnt/c/Users/15322/poetry_deploy

# 3. 初始化 Git
if [ ! -d ".git" ]; then
    echo "📦 初始化 Git 仓库..."
    git init
else
    echo "✅ Git 仓库已存在。"
fi

# 4. 配置 .gitignore
echo "🛡️ 重新生成 .gitignore..."
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

# 5. 配置远程仓库 (HTTPS)
echo "🔗 配置远端仓库地址..."
# 如果之前配错了，先删掉
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/ibalamayaka-debug/poetry-site.git
git branch -M main

# 6. 添加并提交
echo "📝 添加文件并提交..."
git add .
# 只有在有更改时才提交
git diff-index --quiet HEAD || git commit -m "feat: 准备部署到 Vercel (对接 Turso 数据库)"

# 7. 推送
echo "⬆️ 正在推送到 GitHub..."
# 使用 HTTPS 推送时，如果没有缓存密码，终端会卡住要求输入密码/Token。
# 我们先尝试执行，如果它卡主需要交互，用户在终端里会看到提示。
git push -u origin main

echo "🎉 恭喜！脚本执行完毕。"
