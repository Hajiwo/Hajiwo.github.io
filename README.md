# Jundong’s Blog

Astro 静态博客，部署地址：https://hajiwo.github.io

## 本地开发

使用 Node.js >= 22.12：

```sh
npm ci
npm run dev
npm run build
```

前后端联调需要两个终端：

```sh
# 终端 1：Django API 与管理端
cd backend
source .venv/bin/activate
python manage.py migrate
python manage.py sync_astro_content
python manage.py runserver 127.0.0.1:8000

# 终端 2：Astro 前端
cd ..
cp -n .env.example .env
npm run dev -- --host 127.0.0.1
```

打开 `http://127.0.0.1:4321/`。首页显示“已同步后端”，文章页评论区显示“后端已连接”，即表示联调成功。后台发布的文章会由浏览器实时读取，不需要重启 Astro；后端文章使用 `/blog/article/?slug=...` 通用详情页。

`main` 跟踪 `origin/main`，远程仓库为 `https://github.com/Hajiwo/Hajiwo.github.io.git`。推送到 main 后，现有 GitHub Actions 工作流构建并部署 GitHub Pages。

PythonAnywhere 上线后，在 GitHub 仓库的 `Settings → Secrets and variables → Actions → Variables` 新建仓库变量 `PUBLIC_API_BASE_URL`，值为 `https://你的用户名.pythonanywhere.com/api/v1`，然后重新运行 Pages 工作流。该值是公开 API 地址，不应填写密钥。工作流已配置为在构建时注入这个地址；之后后台发布文章会由浏览器实时读取，无需再次构建前端。

## 写文章

在 `src/content/blog/` 新建 Markdown / MDX，填写 `title`、`description`、`pubDate`，可选 `series`（默认“学习笔记”）和 `heroImage`。系列卡片、数量、筛选和搜索由真实文章生成；草稿继续放在 `src/content/drafts/`。

## Django 后端与管理端

已在 [`backend/`](backend/README.md) 实现 Django API 和管理员界面，包括文章与系列管理、发布状态、搜索分页、评论审核。运行及 PythonAnywhere 部署步骤见后端 README。

前端文章列表、后端文章详情和评论区均通过 `PUBLIC_API_BASE_URL` 接入 Django API；本地 Markdown 可用 `python manage.py sync_astro_content` 同步到后端。构建内仍保留 Markdown 文章作为后端离线时的兜底内容。
