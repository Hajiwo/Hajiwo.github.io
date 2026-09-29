# Articles 邮件部署

Articles 使用 Django 保存即时评论、话题和订阅读者。邮件由 GitHub Actions 每 5 分钟领取后通过 mail.de SMTP 发送。PythonAnywhere 免费账户不需要运行常驻进程。GitHub 调度可能延迟，验证页会提示等待。公开仓库长期无活动可能停用定时工作流，需在 Actions 页面重新启用。

服务器 `backend/.env`：

```dotenv
ARTICLES_SITE_URL=https://hajiwo.github.io/articles
SUBSCRIPTIONS_ENABLED=true
MAIL_DELIVERY_MODE=remote
MAIL_WORKER_TOKEN=至少32字符的随机密钥
```

GitHub Actions 加密 Secrets：`MAIL_WORKER_TOKEN`（与服务器相同）、`MAIL_SMTP_USER`、`MAIL_SMTP_PASSWORD`。当前发件地址为 `hajiwo9123217@mail.de`，服务器为 `smtp.mail.de:587`，使用 STARTTLS。密码不进入源码、日志或前端。收件地址、邮件正文仅交给经过密钥认证的发送任务，任务日志只记录数量。

部署先备份数据库，再更新后端并执行 `migrate`、`collectstatic --noinput`、`check` 与 Web App reload，最后推送 main 发布前端。首次迁移不会补发已有文章。未来定时文章由邮件任务扫描后通知。

邮件任务领取的记录租期为 10 分钟；发送失败按 2–60 分钟重试。退订和内容可见性会在领取时检查。SMTP 已接受但回执未记入数据库时，重试可能重复投递。SMTP 接受不代表一定进入收件箱，需检查垃圾邮件。验证链接在领取发送时开始计算 30 分钟有效期。

手动发送：在 GitHub Actions 的 “Deliver Articles email” 运行工作流。后台“邮件通知”查看通知发送状态。暂停发信可关闭该工作流并设置 `SUBSCRIPTIONS_ENABLED=false`。

本地开发或可直接连接 SMTP 的服务器仍支持 `MAIL_DELIVERY_MODE=smtp`，并使用 `send_notifications --watch`。
