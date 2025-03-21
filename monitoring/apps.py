from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'
    
    def ready(self):
        """Initialisation de l'application"""
        # Importer les signaux
        import monitoring.signals
