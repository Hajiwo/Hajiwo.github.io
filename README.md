# Jundong's Blog

个人博客采用前后端分离架构：

- `src/`：Astro 静态前端，由 GitHub Actions 构建并部署到 GitHub Pages。
- `backend/`：Django REST API 与管理员后台，部署到 PythonAnywhere。
- `backend/infotech/`：InfoTech 学生指南，与博客共用 Django Web App，通过 `/infotech/` 访问；使用独立课程数据库、路由、模板和静态资源，部署见 `backend/deploy/infotech.md`。
- Django 数据库是文章、项目报告、系列与评论的唯一内容来源；`Article.content_type` 将普通文章与项目报告分开。
- `/` 展示 Blogs，导航仅提供博客和关于；`/blogs/` 是相同的博客入口；`/articles/` 为无导航入口且不收录到站点地图的文章页（仍可公开访问）；前端通过 `PUBLIC_API_BASE_URL` 实时读取公开 API。

生产环境需要在 GitHub Actions 仓库变量中设置：

```text
PUBLIC_API_BASE_URL=https://<pythonanywhere-username>.pythonanywhere.com/api/v1
```

PythonAnywhere 使用 `backend/.env.example` 作为环境变量模板，并通过 `backend/deploy/pythonanywhere_wsgi.py` 启动 Django。

Articles 独立站包含即时评论、回复和 Markdown 讨论；Django 后台管理话题、回复、订阅读者及邮件队列。订阅后直接建立浏览器身份并加入成功通知邮件，已有邮箱可以登录，邮箱不进入公开 API。通知覆盖新文章、讨论更新与回复，支持偏好设置和退订。

邮件由 PythonAnywhere 后台任务持续读取 Django 数据库队列，通过 SMTP 发送；邮箱凭据保存在服务器环境变量。
