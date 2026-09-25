import ast
from datetime import datetime, time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from blog.models import Article, Series


def parse_frontmatter(source: str):
    parts = source.split('---', 2)
    if len(parts) != 3 or parts[0].strip():
        raise ValueError('missing frontmatter')
    metadata = {}
    for line in parts[1].splitlines():
        if ':' not in line:
            continue
        key, raw_value = line.split(':', 1)
        value = raw_value.strip()
        if value[:1] in {"'", '"'}:
            try:
                value = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                pass
        metadata[key.strip()] = value
    return metadata, parts[2].lstrip()


class Command(BaseCommand):
    help = 'Import Markdown/MDX posts from the Astro content directory into Django.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=Path,
            default=settings.BASE_DIR.parent / 'src' / 'content' / 'blog',
            help='Astro blog content directory.',
        )

    def handle(self, *args, **options):
        content_dir = options['path'].resolve()
        if not content_dir.is_dir():
            raise CommandError(f'Content directory does not exist: {content_dir}')

        imported = 0
        for path in sorted([*content_dir.rglob('*.md'), *content_dir.rglob('*.mdx')]):
            try:
                metadata, body = parse_frontmatter(path.read_text(encoding='utf-8'))
                title = str(metadata['title'])
                description = str(metadata['description'])
                published_date = datetime.fromisoformat(str(metadata['pubDate'])).date()
            except (KeyError, ValueError) as error:
                raise CommandError(f'Invalid frontmatter in {path}: {error}') from error

            series_name = str(metadata.get('series') or '学习笔记')
            series_slug = 'study-notes' if series_name == '学习笔记' else path.parent.name.lower().replace('_', '-')
            series, _ = Series.objects.get_or_create(
                name=series_name,
                defaults={'slug': series_slug, 'description': ''},
            )
            Article.objects.update_or_create(
                slug=path.stem.lower(),
                defaults={
                    'title': title,
                    'description': description,
                    'body': body,
                    'series': series,
                    'status': Article.Status.PUBLISHED,
                    'published_at': timezone.make_aware(datetime.combine(published_date, time.min)),
                },
            )
            imported += 1

        self.stdout.write(self.style.SUCCESS(f'Synced {imported} article(s) from {content_dir}'))
