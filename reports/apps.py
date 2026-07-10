from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reports'
    verbose_name = 'RoadWatch Reports'

    def ready(self):
        # Register signals so Profile is auto-created for new Users
        import reports.signals  # noqa: F401
