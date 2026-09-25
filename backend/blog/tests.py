from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from .models import Article, Comment, Series

@override_settings(SECURE_SSL_REDIRECT=False)
class BlogAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.series = Series.objects.create(
            name='学习笔记', name_en='Study Notes', slug='notes',
            description='学习记录', description_en='Study records',
        )
        self.article = Article.objects.create(
            title='公开笔记', title_en='Public notes', slug='public',
            description='学习 AI', description_en='Learn AI',
            body='中文 Markdown', body_en='English Markdown',
            series=self.series, status='published',
        )
        Article.objects.create(title='Secret draft', slug='draft', description='secret', body='private', series=self.series)
        Article.objects.create(title='Future', slug='future', description='future', body='private', status='published', published_at=timezone.now()+timedelta(days=1), series=self.series)

    def test_visibility_and_read_only(self):
        result = self.client.get('/api/v1/articles/').json()
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['results'][0]['slug'], 'public')
        self.assertEqual(result['results'][0]['series_name'], '学习笔记')
        self.assertEqual(result['results'][0]['title_en'], 'Public notes')
        self.assertEqual(result['results'][0]['series_name_en'], 'Study Notes')
        for slug in ['draft', 'future', 'missing']:
            self.assertEqual(self.client.get(f'/api/v1/articles/{slug}/').status_code, 404)
        self.assertEqual(self.client.post('/api/v1/articles/', {}).status_code, 405)
        self.assertEqual(self.client.patch('/api/v1/articles/public/', {'title':'hacked'}).status_code, 405)

    def test_search_series_and_pagination(self):
        self.assertEqual(self.client.get('/api/v1/articles/?q=AI&series=notes').json()['count'], 1)
        self.assertEqual(self.client.get('/api/v1/articles/?q=secret').json()['count'], 0)
        self.assertEqual(self.client.get('/api/v1/articles/?series=missing').json()['count'], 0)
        self.assertEqual(self.client.get('/api/v1/series/').json()['results'][0]['article_count'], 1)
        self.assertEqual(self.client.get('/api/v1/articles/?page=999').status_code, 404)
        detail = self.client.get('/api/v1/articles/public/').json()
        self.assertEqual(detail['body'], '中文 Markdown')
        self.assertEqual(detail['body_en'], 'English Markdown')
        series = self.client.get('/api/v1/series/').json()['results'][0]
        self.assertEqual(series['name_en'], 'Study Notes')
        self.assertEqual(series['description_en'], 'Study records')

    def test_comment_moderation_and_validation(self):
        url = '/api/v1/articles/public/comments/'
        response = self.client.post(url, {'author':'Reader', 'body':'Hello', 'approved':True}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(Comment.objects.get().approved)
        self.assertEqual(self.client.get(url).json()['count'], 0)
        Comment.objects.update(approved=True)
        self.assertEqual(self.client.get(url).json()['count'], 1)
        self.assertEqual(self.client.post(url, {'author':' ', 'body':'x'}).status_code, 400)
        self.assertEqual(self.client.post(url, {'author':'x', 'body':'a'*2001}).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/articles/draft/comments/', {'author':'x','body':'x'}).status_code, 404)

    def test_comment_throttle(self):
        for _ in range(5):
            self.assertEqual(self.client.post('/api/v1/articles/public/comments/', {'author':'x','body':'x'}).status_code, 201)
        self.assertEqual(self.client.post('/api/v1/articles/public/comments/', {'author':'x','body':'x'}).status_code, 429)

    def test_cors_and_admin(self):
        url = '/api/v1/health/'
        self.assertEqual(self.client.get(url, HTTP_ORIGIN='https://hajiwo.github.io')['Access-Control-Allow-Origin'], 'https://hajiwo.github.io')
        self.assertEqual(self.client.get(url, HTTP_ORIGIN='http://127.0.0.1:4321')['Access-Control-Allow-Origin'], 'http://127.0.0.1:4321')
        self.assertNotIn('Access-Control-Allow-Origin', self.client.get(url, HTTP_ORIGIN='https://untrusted.example'))
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_admin_dashboard_and_editor(self):
        from django.contrib.auth import get_user_model
        admin = get_user_model().objects.create_superuser('owner', password='test-only-password')
        self.client.force_login(admin)
        self.assertContains(self.client.get('/admin/'), '记录新的想法')
        add_page = self.client.get('/admin/blog/article/add/')
        self.assertContains(add_page, '发布设置')
        self.assertContains(add_page, '中文实时预览')
        self.assertContains(add_page, 'English preview')
        self.assertContains(add_page, 'English title')
        response = self.client.post('/admin/blog/article/add/', {
            'title': 'Admin draft', 'slug': 'admin-draft', 'description': 'Created in admin',
            'body': '# Hello', 'series': self.series.pk, 'status': 'draft',
            'published_at_0': '2026-09-25', 'published_at_1': '12:00:00', '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Article.objects.filter(slug='admin-draft').exists())
        self.assertEqual(self.client.get('/api/v1/articles/admin-draft/').status_code, 404)

    def test_admin_article_full_crud_and_duplicate(self):
        from django.contrib.auth import get_user_model
        admin = get_user_model().objects.create_superuser('crud-owner', password='test-only-password')
        self.client.force_login(admin)

        create_response = self.client.post('/admin/blog/article/add/', {
            'title': 'CRUD article', 'slug': 'crud-article', 'description': 'Created',
            'body': '# First version', 'series': self.series.pk, 'status': 'draft',
            'published_at_0': '2026-09-25', 'published_at_1': '12:00:00', '_save': 'Save',
        })
        self.assertEqual(create_response.status_code, 302)
        article = Article.objects.get(slug='crud-article')

        list_page = self.client.get('/admin/blog/article/')
        self.assertContains(list_page, 'CRUD article')
        self.assertContains(list_page, '草稿')
        change_page = self.client.get(f'/admin/blog/article/{article.pk}/change/')
        self.assertContains(change_page, '保存并立即发布')
        self.assertContains(change_page, '# First version')

        update_response = self.client.post(f'/admin/blog/article/{article.pk}/change/', {
            'title': 'CRUD article updated', 'slug': 'crud-article', 'description': 'Updated',
            'body': '# Second version', 'series': self.series.pk, 'status': 'published',
            'title_en': 'CRUD article in English', 'description_en': 'Updated in English',
            'body_en': '# English version',
            'published_at_0': '2026-09-25', 'published_at_1': '12:00:00', '_continue': 'Save',
        })
        self.assertEqual(update_response.status_code, 302)
        article.refresh_from_db()
        self.assertEqual(article.title, 'CRUD article updated')
        self.assertEqual(article.body, '# Second version')
        self.assertEqual(article.title_en, 'CRUD article in English')

        duplicate_response = self.client.post(f'/admin/blog/article/{article.pk}/change/', {
            'title': article.title, 'slug': article.slug, 'description': article.description,
            'body': article.body, 'series': self.series.pk, 'status': article.status,
            'title_en': article.title_en, 'description_en': article.description_en,
            'body_en': article.body_en,
            'published_at_0': '2026-09-25', 'published_at_1': '12:00:00', '_duplicate': 'Duplicate',
        })
        self.assertEqual(duplicate_response.status_code, 302)
        duplicate = Article.objects.get(slug='crud-article-copy')
        self.assertEqual(duplicate.status, 'draft')
        self.assertEqual(duplicate.body_en, '# English version')

        delete_page = self.client.get(f'/admin/blog/article/{duplicate.pk}/delete/')
        self.assertContains(delete_page, '你确认想要删除')
        delete_response = self.client.post(f'/admin/blog/article/{duplicate.pk}/delete/', {'post': 'yes'})
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Article.objects.filter(pk=duplicate.pk).exists())

    def test_admin_permission_boundary_and_login_template(self):
        from django.contrib.auth import get_user_model
        self.assertContains(self.client.get('/admin/login/'), '回到你的写作空间')
        staff = get_user_model().objects.create_user('limited', password='test-only-password', is_staff=True)
        self.client.force_login(staff)
        self.assertNotContains(self.client.get('/admin/'), 'Public notes')
        self.assertEqual(self.client.get('/admin/blog/article/').status_code, 403)
        self.assertEqual(self.client.post('/admin/blog/article/add/', {}).status_code, 403)

    def test_sync_astro_content_command(self):
        with TemporaryDirectory() as temporary_directory:
            content = Path(temporary_directory) / 'Synced_Post.mdx'
            content.write_text(
                "---\ntitle: 'Synced post'\ndescription: 'From Astro'\n"
                "pubDate: '2026-09-20'\nseries: 'Integration'\n---\n\n# Body\n",
                encoding='utf-8',
            )
            call_command('sync_astro_content', path=Path(temporary_directory), verbosity=0)

        article = Article.objects.get(slug='synced_post')
        self.assertEqual(article.title, 'Synced post')
        self.assertEqual(article.series.name, 'Integration')
        self.assertEqual(article.status, 'published')
        self.assertIn('# Body', article.body)
