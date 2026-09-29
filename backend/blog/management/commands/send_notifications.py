import time
from django.core.management.base import BaseCommand
from blog.notifications import collect_articles, deliver_pending


class Command(BaseCommand):
    help = 'Deliver queued notifications; --watch polls every 15 seconds. Use one always-on worker.'

    def add_arguments(self, parser):
        parser.add_argument('--watch', action='store_true')

    def handle(self, *args, **options):
        while True:
            collect_articles()
            sent = deliver_pending()
            self.stdout.write(f'Delivered {sent} notifications')
            if not options['watch']:
                return
            time.sleep(15)
