# Jundong's Blog

个人博客采用前后端分离架构：

- `src/`：Astro 静态前端，由 GitHub Actions 构建并部署到 GitHub Pages。
- `backend/`：Django REST API 与管理员后台，部署到 PythonAnywhere。
- Django 数据库是文章、系列与评论的唯一内容来源；前端通过 `PUBLIC_API_BASE_URL` 实时读取公开 API。

生产环境需要在 GitHub Actions 仓库变量中设置：

```text
PUBLIC_API_BASE_URL=https://<pythonanywhere-username>.pythonanywhere.com/api/v1
```

PythonAnywhere 使用 `backend/.env.example` 作为环境变量模板，并通过 `backend/deploy/pythonanywhere_wsgi.py` 启动 Django。
