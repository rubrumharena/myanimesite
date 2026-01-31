from django.apps import AppConfig


class ListsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lists'

    def ready(self):
        import lists.signals
