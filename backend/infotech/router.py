class InfoTechRouter:
    """Keep student-guide tables in their own database."""

    def db_for_read(self, model, **hints):
        return 'infotech' if model._meta.app_label == 'courses' else None

    def db_for_write(self, model, **hints):
        return 'infotech' if model._meta.app_label == 'courses' else None

    def allow_relation(self, obj1, obj2, **hints):
        labels = {obj1._meta.app_label, obj2._meta.app_label}
        if 'courses' in labels:
            return labels == {'courses'}
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'courses':
            return db == 'infotech'
        if db == 'infotech':
            return False
        return None

