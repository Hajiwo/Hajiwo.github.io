import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from blog.models import Article, Series


class Command(BaseCommand):
    help = 'Validate or publish source-reviewed bilingual project reports.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR) / 'blog/portfolio/posts.json'
        posts = json.loads(path.read_text())
        with transaction.atomic():
            series, _ = Series.objects.get_or_create(slug='engineering-projects', defaults={
                'name': '工程项目', 'name_en': 'Engineering Projects',
                'description': '经过源码核验的项目设计、实现与验证记录。',
                'description_en': 'Source-reviewed design, implementation and validation reports.',
            })
            for data in posts:
                article, _ = Article.objects.get_or_create(slug=data['slug'])
                for key, value in data.items():
                    setattr(article, key, value)
                article.series = series
                article.content_type = Article.ContentType.PROJECT
                article.status = Article.Status.PUBLISHED
                article.full_clean()
                article.save()
            if options['dry_run']:
                transaction.set_rollback(True)
        self.stdout.write(f"{'Validated' if options['dry_run'] else 'Published'} {len(posts)} project reports")
