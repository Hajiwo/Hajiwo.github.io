# Django 博客后端与管理端

Python 3.10+，Django 5.2 LTS，Django REST Framework，SQLite。

## 本地运行

```sh
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# 把输出写入 .env 的 DJANGO_SECRET_KEY；本地使用 DJANGO_DEBUG=true。
python manage.py migrate
python manage.py sync_astro_content
python manage.py createsuperuser
python manage.py runserver
```

访问 http://127.0.0.1:8000/admin/，用自己创建的管理员登录。没有预设账号密码。
管理端包含概览、文章创建/编辑/删除、搜索和系列筛选、草稿/发布/定时发布、系列排序、评论审核和用户权限。正文使用 Markdown 源文本编辑，并配有安全的实时近似预览。定时文章到时间后自动进入 API 查询结果，无需后台定时任务。

文章管理页还提供实时 Markdown 近似预览、字符统计、按状态/系列/日期筛选、快捷编辑与删除、批量发布/撤回，以及“保存并复制”工作流。删除操作仍经过 Django 的二次确认页。

公开站点会在浏览器中实时读取 Django 的文章列表、后端文章详情和评论。`sync_astro_content` 会把现有 Markdown/MDX 更新到 Django，使每篇文章拥有对应的 API 与评论端点；该命令可重复运行。Astro 构建中仍保留本地 Markdown，作为后端暂时不可用时的兜底内容。

前端根目录的 `.env` 配置：

```env
PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## API

所有路径均以 `/api/v1/` 开头，列表返回 `{count,next,previous,results}`，每页 20 条。

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | health/ | 运行状态 |
| GET | series/ | 系列及已上线文章数 |
| GET | articles/?q=AI&series=notes&page=1 | 文章搜索、系列筛选、分页 |
| GET | articles/<slug>/ | 文章详情与 Markdown body |
| GET | articles/<slug>/comments/ | 已审核评论 |
| POST | articles/<slug>/comments/ | JSON `{ "author": "读者", "body": "评论" }` |

草稿与未来文章返回 404。文章编辑只在登录后的管理端进行，公开 API 不提供写文章接口。评论默认待审核，正文最长 2000 字，每个来源每小时最多 5 次提交；当前限流使用进程内缓存，多进程生产部署应替换共享缓存，不能视为完整反垃圾系统。CORS 不是认证机制。前端显示评论必须使用纯文本，渲染 Markdown 时需净化 HTML。

## 测试

```sh
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py sync_astro_content
```

## PythonAnywhere

1. 将仓库拉取到 `/home/YOUR_USERNAME/Hajiwo.github.io`。创建 Python 3.10+ 虚拟环境，安装 `backend/requirements.txt`，Web 面板选择相同 Python 版本并设置该虚拟环境。
2. 建立 `backend/.env`：设置随机 `DJANGO_SECRET_KEY`、`DJANGO_DEBUG=false`、`DJANGO_ALLOWED_HOSTS=YOUR_USERNAME.pythonanywhere.com`（以实际域名为准），`CSRF_TRUSTED_ORIGINS=https://YOUR_USERNAME.pythonanywhere.com`，`CORS_ALLOWED_ORIGINS=https://hajiwo.github.io`。
3. 在 backend 目录执行 `python manage.py migrate`、`python manage.py createsuperuser`、`python manage.py collectstatic --noinput`。
4. 在 Web 面板打开实际 WSGI 配置文件，将 `deploy/pythonanywhere_wsgi.py` 的内容复制进去并替换用户名和路径。不要仅修改仓库 WSGI 文件后期待平台自动引用它。
5. Web 面板添加静态映射：URL `/static/` → `/home/YOUR_USERNAME/Hajiwo.github.io/backend/staticfiles`，然后 Reload。
6. 验证 HTTPS 下 `/api/v1/health/` 与 `/admin/`。运行 `python manage.py check --deploy`；生产强制 HTTPS。仅在平台明确提供并清洗代理头时配置代理 SSL header，避免盲目信任客户端 header。

SQLite 适合初期个人博客；定期备份 `db.sqlite3`。不要提交 `.env`、数据库、虚拟环境或管理员凭据。

参考：https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/ 和 https://www.djangoproject.com/download/ 。
