# Jundong’s Blog

Astro 静态博客，部署地址：https://hajiwo.github.io

## 本地开发

使用 Node.js >= 22.12：

```sh
npm ci
npm run dev
npm run build
```

`main` 跟踪 `origin/main`，远程仓库为 `https://github.com/Hajiwo/Hajiwo.github.io.git`。推送到 main 后，现有 GitHub Actions 工作流构建并部署 GitHub Pages。

## 写文章

在 `src/content/blog/` 新建 Markdown / MDX，填写 `title`、`description`、`pubDate`，可选 `series`（默认“学习笔记”）和 `heroImage`。系列卡片、数量、筛选和搜索由真实文章生成；草稿继续放在 `src/content/drafts/`。

## 后续 Django 后端

当前保持完整静态输出，无后端依赖。未来 Django 部署到 PythonAnywhere，提供 HTTPS JSON API；GitHub Pages 继续托管前端。公开文章可在 Astro 构建时读取 API，以保留 SEO 和静态阅读体验；评论等动态功能再由浏览器请求 API。届时为实际前端域名配置 Django CORS，并在后端保存所有密钥。后端目前尚未实现。
