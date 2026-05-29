from django.apps import AppConfig


class AppDocConfig(AppConfig):
    name = 'backend.apps.doc'
    label = 'app_doc'

    def ready(self):
        import backend.apps.doc.signals  # noqa
