from django.apps import AppConfig


class InfoTechConfig(AppConfig):
    name = 'infotech'
    # Preserve the source database's existing table names and migration history.
    label = 'courses'
    verbose_name = 'InfoTech student guide'
    default_auto_field = 'django.db.models.BigAutoField'

