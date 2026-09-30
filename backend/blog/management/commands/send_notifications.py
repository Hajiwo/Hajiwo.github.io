import time
from django.db import close_old_connections
from django.core.management.base import BaseCommand
from blog.notifications import collect_articles, deliver_pending, deliver_verifications


class Command(BaseCommand):
    help = 'Deliver queued notifications; --watch polls every 15 seconds. Use one always-on worker.'

    def add_arguments(self, parser):
        parser.add_argument('--watch', action='store_true')

    def handle(self, *args, **options):
        while True:
            close_old_connections()
            try:
                collect_articles()
                verifications = deliver_verifications()
                notifications = deliver_pending()
                self.stdout.write(f'Delivered {verifications} verification emails and {notifications} notifications')
            except Exception as exc:
                # Keep the dedicated worker alive; detailed SMTP responses can contain private server data.
                self.stderr.write(f'Notification worker cycle failed: {type(exc).__name__}')
            finally:
                close_old_connections()
            if not options['watch']:
                return
            time.sleep(15)
