from django.contrib import admin, messages
from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .forms import ArticleAdminForm
from .models import Article, Comment, Series, Topic, DiscussionPost, Subscriber, SubscriberLogin, Notification


class BlogAdminSite(AdminSite):
    site_header = "Jundong’s Blog"
    site_title = '博客管理'
    index_title = '内容概览'
    index_template = 'admin/dashboard.html'

    def index(self, request, extra_context=None):
        context = dict(extra_context or {})
        if self.has_permission(request):
            context['metrics'] = {
                'articles': Article.objects.filter(content_type=Article.ContentType.ARTICLE).count() if request.user.has_perm('blog.view_article') else None,
                'projects': Article.objects.filter(content_type=Article.ContentType.PROJECT).count() if request.user.has_perm('blog.view_article') else None,
                'published': Article.objects.published().count() if request.user.has_perm('blog.view_article') else None,
                'pending': Comment.objects.filter(approved=False).count() if request.user.has_perm('blog.view_comment') else None,
                'series': Series.objects.count() if request.user.has_perm('blog.view_series') else None,
            }
            context['recent_articles'] = (
                Article.objects.select_related('series').order_by('-updated_at')[:5]
                if request.user.has_perm('blog.view_article') else []
            )
        return super().index(request, context)


blog_admin = BlogAdminSite(name='blog_admin')


@admin.register(Series, site=blog_admin)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_en', 'slug', 'article_total', 'order']
    list_editable = ['order']
    search_fields = ['name', 'name_en', 'slug', 'description', 'description_en']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('中文版本', {'fields': ('name', 'description')}),
        ('English version', {'fields': ('name_en', 'description_en')}),
        ('显示设置', {'fields': ('slug', 'order')}),
    )

    @admin.display(description='文章数')
    def article_total(self, obj):
        return obj.articles.count()


@admin.register(Article, site=blog_admin)
class ArticleAdmin(admin.ModelAdmin):
    form = ArticleAdminForm
    change_form_template = 'admin/blog/article/change_form.html'
    list_display = [
        'title', 'content_type_badge', 'status_badge', 'series', 'published_at', 'updated_at',
        'translation_status', 'content_size', 'quick_actions',
    ]
    list_display_links = ['title']
    list_filter = ['content_type', 'status', 'series', 'published_at', 'updated_at']
    search_fields = ['title', 'title_en', 'slug', 'description', 'description_en', 'body', 'body_en']
    search_help_text = '搜索中英文标题、slug、简介或正文'
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['series']
    readonly_fields = ['updated_at']
    date_hierarchy = 'published_at'
    ordering = ['-updated_at', '-published_at']
    list_per_page = 25
    save_on_top = True
    actions_on_top = True
    actions_on_bottom = False
    fieldsets = (
        ('写文章', {
            'fields': ('title', 'body'),
            'description': '只需填写标题即可保存；正文可以稍后补充。支持 Markdown 实时预览。',
        }),
        ('发布设置', {
            'fields': ('content_type', 'series', 'status'),
        }),
        ('摘要（可选）', {
            'fields': ('description',), 'classes': ('collapse',),
        }),
        ('English version（可选）', {
            'fields': ('title_en', 'description_en', 'body_en'),
            'classes': ('collapse',),
            'description': '可随时补充。未填写英文正文时，英文页面会提示暂时仅提供中文内容。',
        }),
        ('更多设置', {
            'fields': ('slug', 'published_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'URL 标识自动生成；未来的发布时间表示定时发布。',
        }),
    )
    actions = ['publish', 'unpublish', 'duplicate']

    class Media:
        js = ['blog/article_editor.js']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('series')

    @admin.display(description='内容类型', ordering='content_type')
    def content_type_badge(self, obj):
        css_class = 'published' if obj.content_type == Article.ContentType.PROJECT else 'draft'
        return format_html(
            '<span class="article-status article-status--{}">{}</span>',
            css_class,
            obj.get_content_type_display(),
        )

    @admin.display(description='状态', ordering='status')
    def status_badge(self, obj):
        if obj.status == Article.Status.DRAFT:
            label, css_class = '草稿', 'draft'
        elif obj.published_at > timezone.now():
            label, css_class = '定时发布', 'scheduled'
        else:
            label, css_class = '已上线', 'published'
        return format_html('<span class="article-status article-status--{}">{}</span>', css_class, label)

    @admin.display(description='内容量')
    def content_size(self, obj):
        characters = len(obj.body.strip()) + len(obj.body_en.strip())
        return format_html('<span title="中英文正文字符数">{} 字符</span>', characters)

    @admin.display(description='双语内容')
    def translation_status(self, obj):
        complete = bool(obj.body_en.strip())
        label = '英文已提供' if complete else '仅中文'
        css_class = 'published' if complete else 'scheduled'
        return format_html('<span class="article-status article-status--{}">{}</span>', css_class, label)

    @admin.display(description='快捷操作')
    def quick_actions(self, obj):
        change_url = reverse('admin:blog_article_change', args=[obj.pk])
        delete_url = reverse('admin:blog_article_delete', args=[obj.pk])
        return format_html(
            '<span class="row-actions"><a href="{}">编辑</a><a href="{}" class="danger">删除</a></span>',
            change_url,
            delete_url,
        )

    @admin.action(description='立即发布选中的文章', permissions=['change'])
    def publish(self, request, queryset):
        updated = queryset.update(
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(), updated_at=timezone.now(),
        )
        from django.db import transaction
        from .notifications import collect_articles
        transaction.on_commit(collect_articles)
        self.message_user(request, f'已发布 {updated} 篇文章。', messages.SUCCESS)

    @admin.action(description='将选中文章移回草稿', permissions=['change'])
    def unpublish(self, request, queryset):
        updated = queryset.update(status=Article.Status.DRAFT, updated_at=timezone.now())
        self.message_user(request, f'已将 {updated} 篇文章移回草稿。', messages.SUCCESS)

    @admin.action(description='复制选中的文章为草稿', permissions=['add', 'change'])
    def duplicate(self, request, queryset):
        created = 0
        for article in queryset:
            self._duplicate_article(article)
            created += 1
        self.message_user(request, f'已复制 {created} 篇文章，新副本均为草稿。', messages.SUCCESS)

    def response_change(self, request, obj):
        if '_publish' in request.POST:
            obj.status = Article.Status.PUBLISHED
            obj.published_at = timezone.now()
            obj.save(update_fields=['status', 'published_at', 'updated_at'])
            self.message_user(request, '文章已保存并立即发布。', messages.SUCCESS)
            return HttpResponseRedirect(reverse('admin:blog_article_change', args=[obj.pk]))
        if '_draft' in request.POST:
            obj.status = Article.Status.DRAFT
            obj.save(update_fields=['status', 'updated_at'])
            self.message_user(request, '文章已保存为草稿。', messages.SUCCESS)
            return HttpResponseRedirect(reverse('admin:blog_article_change', args=[obj.pk]))
        if '_duplicate' in request.POST:
            duplicate = self._duplicate_article(obj)
            self.message_user(request, '已创建草稿副本。', messages.SUCCESS)
            return HttpResponseRedirect(reverse('admin:blog_article_change', args=[duplicate.pk]))
        return super().response_change(request, obj)

    def _duplicate_article(self, article):
        base_slug = f'{article.slug}-copy'
        slug = base_slug
        number = 2
        while Article.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{number}'
            number += 1
        return Article.objects.create(
            title=f'{article.title}（副本）',
            title_en=f'{article.title_en} (Copy)' if article.title_en else '',
            slug=slug,
            description=article.description,
            description_en=article.description_en,
            body=article.body,
            body_en=article.body_en,
            series=article.series,
            content_type=article.content_type,
            status=Article.Status.DRAFT,
            published_at=timezone.now(),
        )


@admin.register(Comment, site=blog_admin)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'article', 'parent', 'approved', 'created_at']
    list_filter = ['approved']
    search_fields = ['author', 'body']
    readonly_fields = ['created_at']
    actions = ['approve', 'hide']

    @admin.action(description='批准选中的评论', permissions=['change'])
    def approve(self, request, queryset):
        queryset.update(approved=True)

    @admin.action(description='隐藏选中的评论', permissions=['change'])
    def hide(self, request, queryset):
        queryset.update(approved=False)


blog_admin.register(get_user_model(), UserAdmin)
blog_admin.register(Group, GroupAdmin)


@admin.register(Topic, site=blog_admin)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'visible', 'locked', 'updated_at']
    list_filter = ['visible', 'locked']
    search_fields = ['title', 'body', 'author']
    readonly_fields = ['created_at', 'updated_at', 'subscriber']
    list_editable = ['visible', 'locked']


@admin.register(DiscussionPost, site=blog_admin)
class DiscussionPostAdmin(admin.ModelAdmin):
    list_display = ['author', 'topic', 'visible', 'created_at']
    list_filter = ['visible', 'topic']
    search_fields = ['author', 'body']
    readonly_fields = ['created_at', 'subscriber']
    list_editable = ['visible']


@admin.register(Subscriber, site=blog_admin)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'active', 'verified_at', 'created_at']
    list_filter = ['active', 'language']
    search_fields = ['email', 'name']
    readonly_fields = ['email', 'verified_at', 'created_at']
    exclude = ['unsubscribe_token']

    def has_add_permission(self, request):
        return False


@admin.register(SubscriberLogin, site=blog_admin)
class SubscriberLoginAdmin(admin.ModelAdmin):
    list_display = ['subscriber', 'name', 'sent_at', 'used_at', 'attempts', 'last_error', 'expires_at']
    list_filter = ['sent_at', 'used_at', 'language']
    search_fields = ['subscriber__email', 'subscriber__name', 'name']
    readonly_fields = [field.name for field in SubscriberLogin._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(Notification, site=blog_admin)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'subscriber', 'kind', 'sent_at', 'attempts', 'last_error', 'cancelled']
    list_filter = ['kind', 'cancelled', 'sent_at']
    readonly_fields = [field.name for field in Notification._meta.fields]

    def has_add_permission(self, request):
        return False
