# Articles 邮件部署

Articles 使用 Django 保存即时评论、话题和订阅读者。邮件由 PythonAnywhere 后端直接通过 mail.de SMTP 发送；验证邮件、文章、话题和回复通知均进入队列，由一个 Always-on task 发送。

服务器 `backend/.env`：

```dotenv
ARTICLES_SITE_URL=https://hajiwo.github.io/articles
SUBSCRIPTIONS_ENABLED=true
MAIL_DELIVERY_MODE=smtp
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mail.de
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_HOST_USER=发件邮箱
EMAIL_HOST_PASSWORD=邮箱密码或应用密码
DEFAULT_FROM_EMAIL=Articles Notifications <发件邮箱>
```

生产环境使用 `MAIL_DELIVERY_MODE=smtp`。SMTP 密码只保存在 PythonAnywhere 的 `backend/.env` 中，权限设为 `0600`，不会进入源码、前端或日志。

部署先备份数据库，再更新后端并执行 `migrate`、`collectstatic --noinput`、`check` 与 Web App reload，最后推送 main 发布前端。首次迁移不会补发已有文章。未来定时文章由邮件任务扫描后通知。

在 PythonAnywhere 的 Tasks 页面创建一个 Always-on task：

```bash
/home/jdChen3398/Hajiwo.github.io/backend/.venv/bin/python /home/jdChen3398/Hajiwo.github.io/backend/manage.py send_notifications --watch
```

验证邮件通常会在一分钟内发出；发送失败会按 2–60 分钟重试。后台“订阅登录链接”和“邮件通知”可以分别查看验证邮件与通知邮件的发送状态。暂停发信时，停止 Always-on task 并设置 `SUBSCRIPTIONS_ENABLED=false`。
