from django.apps import AppConfig


class ScraperConfig(AppConfig):
    name = 'scraper'
    verbose_name = 'Scraper de prix'

    def ready(self):
        # Import des signaux au démarrage
        import scraper.signals
