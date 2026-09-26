from django.core.validators import MaxLengthValidator
from django.db import models
from django.utils import timezone

class Series(models.Model):
    name = models.CharField(max_length=100, unique=True)
    name_en = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = '文章系列'
        verbose_name_plural = '文章系列'

    def __str__(self):
        return self.name

class ArticleQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status='published', published_at__lte=timezone.now())

class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        PUBLISHED = 'published', '已发布'

    class ContentType(models.TextChoices):
        ARTICLE = 'article', '文章'
        PROJECT = 'project', '项目报告'

    title = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.CharField(max_length=500)
    description_en = models.CharField(max_length=500, blank=True)
    body = models.TextField(help_text='Markdown 源文本；API 不执行 MDX 或 HTML。')
    body_en = models.TextField(blank=True, help_text='English Markdown source; MDX and raw HTML are not executed.')
    series = models.ForeignKey(Series, null=True, blank=True, on_delete=models.SET_NULL, related_name='articles')
    content_type = models.CharField(max_length=12, choices=ContentType.choices, default=ContentType.ARTICLE)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    objects = ArticleQuerySet.as_manager()

    class Meta:
        ordering = ['-published_at', '-id']
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['content_type', 'status', 'published_at']),
        ]
        verbose_name = '文章'
        verbose_name_plural = '文章'

    def __str__(self):
        return self.title

class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    author = models.CharField(max_length=80)
    body = models.TextField(validators=[MaxLengthValidator(2000)])
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        verbose_name = '评论'
        verbose_name_plural = '评论'

    def __str__(self):
        return f'{self.author}: {self.body[:40]}'
