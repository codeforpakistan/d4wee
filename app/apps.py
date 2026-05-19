from django.apps import AppConfig


class D4WEEConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    
    def ready(self):
        # Import signals to register them
        import app.signals  # noqa: F401
