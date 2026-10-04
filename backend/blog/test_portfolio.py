from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import Article, Series


class PortfolioPublicationTests(TestCase):
    def test_dry_run_leaves_no_content(self):
        call_command('publish_portfolio', dry_run=True, stdout=StringIO())
        self.assertEqual(Article.objects.count(), 0)
        self.assertEqual(Series.objects.count(), 0)

    def test_publication_is_idempotent_and_retains_unrelated_articles(self):
        existing = Article.objects.create(title='Existing', slug='unrelated')
        call_command('publish_portfolio', stdout=StringIO())
        dates = dict(Article.objects.filter(content_type='project').values_list('slug', 'published_at'))
        call_command('publish_portfolio', stdout=StringIO())
        projects = Article.objects.filter(content_type='project')
        self.assertEqual(projects.count(), 6)
        self.assertEqual(dict(projects.values_list('slug', 'published_at')), dates)
        for article in projects:
            self.assertEqual(article.status, 'published')
            self.assertTrue(article.title_en and article.body_en)
        existing.refresh_from_db()
        self.assertEqual(existing.title, 'Existing')
