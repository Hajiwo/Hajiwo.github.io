from django.apps import AppConfig


class BlogConfig(AppConfig):
    name = 'blog'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from . import signals  # noqa: F401
