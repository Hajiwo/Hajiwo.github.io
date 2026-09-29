# Articles 邮件部署

前端仍部署 GitHub Pages；Django 管理文章、即时评论、话题、订阅读者及邮件队列。正式博客不显示讨论和订阅入口。

## Gmail 配置

在 PythonAnywhere 的 `backend/.env` 填写以下设置，密码不要提交 Git：

```dotenv
ARTICLES_SITE_URL=https://hajiwo.github.io/articles
SUBSCRIPTIONS_ENABLED=true
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_HOST_USER=jundong202917@gmail.com
DEFAULT_FROM_EMAIL=jundong202917@gmail.com
EMAIL_HOST_PASSWORD=在此填写Gmail应用专用密码
```

Gmail 需要开启两步验证并创建应用专用密码，不能使用普通登录密码。

- [Google 应用专用密码说明](https://support.google.com/accounts/answer/185833)
- [PythonAnywhere Gmail 发信说明](https://help.pythonanywhere.com/pages/SMTPForFreeUsers/)
- [Django 邮件配置](https://docs.djangoproject.com/en/5.2/topics/email/)

## 发布顺序

1. 备份服务器 `backend/db.sqlite3`，拉取代码。
2. 执行 `backend/.venv/bin/python backend/manage.py migrate`、`collectstatic --noinput` 和 `check`，重新加载 Web App。
3. 配置通知发送任务，再部署前端。第一次迁移不会给旧文章补发邮件，已有未来定时文章仍会在到期后通知。

通知任务：

```sh
cd /home/jdChen3398/Hajiwo.github.io
backend/.venv/bin/python backend/manage.py send_notifications --watch
```

建议使用 PythonAnywhere Always-on task 保持运行（需要支持该功能的套餐）。测试可在 Bash console 启动，但不能保证长期运行。若使用 Scheduled task，运行不带 `--watch` 的命令，延迟取决于调度频率。未运行发送任务时，通知只会保存在队列中，验证邮件仍会即时发送。

每封通知单独收件、附退订入口。发送失败按 2–60 分钟退避重试；后台“邮件通知”可以查看状态。SMTP 成功后、数据库记录成功前若进程崩溃，重试可能重复投递。运行任务前先验证发件配置，避免队列长期堆积。

## 验证

在 Articles 订阅页用自己的邮箱确认订阅；在另一浏览器以游客身份回复自己的评论，检查收件；关闭通知后重复操作，确认不再收件。不要在正式库创建测试订阅读者或向未经同意的地址发送测试邮件。
