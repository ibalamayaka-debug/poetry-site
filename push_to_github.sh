#!/bin/bash

echo "🚀 开始配置 Git 并推送到 GitHub..."

# 1. 确保在正确的目录
cd /mnt/c/Users/15322/poetry_deploy

# 2. 初始化 Git 仓库 (如果之前没有)
if [ ! -d ".git" ]; then
    echo "📦 初始化 Git 仓库..."
    git init
else
    echo "✅ Git 仓库已存在。"
fi

# 3. 创建或更新 .gitignore 文件
echo "🛡️ 配置 .gitignore (防止上传大文件和临时文件)..."
cat << EOF > .gitignore
# 数据库文件 (已经在 Turso 云端了，千万别传 500MB 的文件到 Git)
poetry.db
poetry.db-journal
poetry_dump.sql
poetry_dump.sq

# 虚拟环境和缓存
venv/
__pycache__/
*.pyc
.pytest_cache/

# 隐藏文件和系统文件
.aidex/
.vscode/
.DS_Store
*.zip
*.log
EOF

# 4. 检查是否有远端仓库
REMOTE_EXISTS=$(git remote -v)
if [ -z "$REMOTE_EXISTS" ]; then
    echo "⚠️ 尚未配置 GitHub 远端仓库。"
    echo "请在浏览器打开: https://github.com/new"
    echo "创建一个名为 'poetry-site' 的空仓库 (不要勾选 README 和 gitignore)。"
    read -p "👉 创建好后，请将仓库的 HTTPS 地址 (如 https://github.com/ibalamayaka-debug/poetry-site.git) 粘贴到这里并回车: " REPO_URL
    
    if [ -n "$REPO_URL" ]; then
        git remote add origin "$REPO_URL"
        git branch -M main
        echo "🔗 已关联远端仓库: $REPO_URL"
    else
        echo "❌ 未提供远端地址，脚本退出。请手动关联远端仓库。"
        exit 1
    fi
fi

# 5. 提交代码
echo "📝 添加文件并提交..."
git add .
git commit -m "feat: 初次提交，准备部署到 Vercel (对接 Turso 数据库)"

# 6. 推送到 GitHub
echo "⬆️ 正在推送到 GitHub..."
git branch -M main
git push -u origin main

echo "🎉 恭喜！代码已成功推送到 GitHub。"
echo "下一步：登录 Vercel 官网，点击 'Add New -> Project'，导入这个仓库即可！"
