import uuid
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
    description = models.CharField(max_length=500, blank=True)
    description_en = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True, help_text='Markdown 源文本；API 不执行 MDX 或 HTML。')
    body_en = models.TextField(blank=True, help_text='English Markdown source; MDX and raw HTML are not executed.')
    series = models.ForeignKey(Series, null=True, blank=True, on_delete=models.SET_NULL, related_name='articles')
    content_type = models.CharField(max_length=12, choices=ContentType.choices, default=ContentType.ARTICLE)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    notification_sent_at = models.DateTimeField(null=True, blank=True, editable=False)
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
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    subscriber = models.ForeignKey('Subscriber', null=True, blank=True, on_delete=models.SET_NULL, related_name='comments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        verbose_name = '评论'
        verbose_name_plural = '评论'

    def __str__(self):
        return f'{self.author}: {self.body[:40]}'


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=80)
    verified_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=False)
    articles = models.BooleanField(default=True, verbose_name='新文章通知')
    discussions = models.BooleanField(default=True, verbose_name='讨论更新通知')
    replies = models.BooleanField(default=True, verbose_name='回复通知')
    language = models.CharField(max_length=2, choices=[('zh', '中文'), ('en', 'English')], default='zh')
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '订阅读者'
        verbose_name_plural = '订阅读者'

    def __str__(self):
        return f'{self.name} <{self.email}>'


class SubscriberLogin(models.Model):
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=80)
    language = models.CharField(max_length=2, default='zh')
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)


class SubscriberSession(models.Model):
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()


class Topic(models.Model):
    title = models.CharField(max_length=160, verbose_name='话题')
    author = models.CharField(max_length=80, verbose_name='发起人')
    body = models.TextField(validators=[MaxLengthValidator(20000)], verbose_name='内容（Markdown）')
    subscriber = models.ForeignKey(Subscriber, null=True, blank=True, on_delete=models.SET_NULL)
    visible = models.BooleanField(default=True, verbose_name='公开显示')
    locked = models.BooleanField(default=False, verbose_name='关闭回复')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-updated_at', '-id']
        verbose_name = '讨论话题'
        verbose_name_plural = '讨论话题'

    def __str__(self):
        return self.title


class DiscussionPost(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='posts')
    author = models.CharField(max_length=80)
    body = models.TextField(validators=[MaxLengthValidator(20000)])
    subscriber = models.ForeignKey(Subscriber, null=True, blank=True, on_delete=models.SET_NULL)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        verbose_name = '讨论回复'
        verbose_name_plural = '讨论回复'

    def __str__(self):
        return f'{self.author}: {self.body[:40]}'


class Notification(models.Model):
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE)
    event_key = models.CharField(max_length=100)
    kind = models.CharField(max_length=16, choices=[('articles', '新文章'), ('discussions', '讨论更新'), ('replies', '回复')])
    title = models.CharField(max_length=200)
    path = models.CharField(max_length=500)
    article = models.ForeignKey(Article, null=True, blank=True, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, null=True, blank=True, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, null=True, blank=True, on_delete=models.CASCADE)
    post = models.ForeignKey(DiscussionPost, null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    claimed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=200, blank=True)
    cancelled = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['subscriber', 'event_key'], name='unique_notification_recipient_event')]
        ordering = ['created_at', 'id']
        verbose_name = '邮件通知'
        verbose_name_plural = '邮件通知'
