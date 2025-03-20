import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from products.models import Product
from monitoring.models import ProductMonitoringConfig

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Initialise les configurations de monitoring pour tous les produits'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Nombre de produits à traiter par lot'
        )
        parser.add_argument(
            '--frequency',
            type=str,
            default='normal',
            choices=['high', 'normal', 'low'],
            help='Fréquence de monitoring par défaut'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Ignorer les produits qui ont déjà une configuration'
        )
    
    def handle(self, *args, **options):
        batch_size = options['batch_size']
        frequency = options['frequency']
        skip_existing = options['skip_existing']
        
        # Récupérer les produits qui n'ont pas encore de configuration
        if skip_existing:
            products_with_config = ProductMonitoringConfig.objects.values_list('product_id', flat=True)
            products = Product.objects.exclude(id__in=products_with_config)
        else:
            products = Product.objects.all()
        
        total_products = products.count()
        self.stdout.write(f"Initialisation du monitoring pour {total_products} produits")
        
        # Traiter par lots
        processed = 0
        created = 0
        
        for i in range(0, total_products, batch_size):
            batch = products[i:i+batch_size]
            
            now = timezone.now()
            configs_to_create = []
            
            for product in batch:
                # Distribuer les next_scheduled sur les prochaines 24h pour éviter les pics
                hours_offset = (processed % 24)
                next_scheduled = now + timedelta(hours=hours_offset)
                
                config = ProductMonitoringConfig(
                    product=product,
                    frequency=frequency,
                    active=True,
                    next_scheduled=next_scheduled
                )
                configs_to_create.append(config)
                processed += 1
            
            # Création en masse
            if configs_to_create:
                ProductMonitoringConfig.objects.bulk_create(
                    configs_to_create,
                    ignore_conflicts=True
                )
                created += len(configs_to_create)
            
            self.stdout.write(f"Progression: {processed}/{total_products}")
        
        self.stdout.write(self.style.SUCCESS(f"Initialisation terminée. {created} configurations créées."))
