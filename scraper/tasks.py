import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from .models import Product, PricePoint, ScrapingTask, Screenshot, Retailer
from .bridge.puppeteer_bridge import PuppeteerBridge
from .extractors.amazon import AmazonExtractor
from .extractors.fnac import FnacExtractor
from .extractors.cdiscount import CdiscountExtractor
from .extractors.darty import DartyExtractor
from .utils.retry import celery_retry_task

logger = logging.getLogger(__name__)

# Map des domaines vers leur extracteur correspondant
EXTRACTORS = {
    'amazon': AmazonExtractor,
    'fnac': FnacExtractor,
    'cdiscount': CdiscountExtractor,
    'darty': DartyExtractor,
}

def get_extractor_for_url(url):
    """Détermine l'extracteur à utiliser en fonction de l'URL"""
    from urllib.parse import urlparse
    
    domain = urlparse(url).netloc.lower()
    
    if 'amazon' in domain:
        return AmazonExtractor
    elif 'fnac' in domain:
        return FnacExtractor
    elif 'cdiscount' in domain:
        return CdiscountExtractor
    elif 'darty' in domain:
        return DartyExtractor
    else:
        raise ValueError(f"Aucun extracteur disponible pour {domain}")

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def scrape_product(self, product_id=None, product_url=None):
    """
    Tâche de scraping d'un produit spécifique
    
    Args:
        product_id: ID du produit à scraper (si existant)
        product_url: URL du produit à scraper (pour nouveau produit)
    """
    logger.info(f"Démarrage scraping produit: ID={product_id}, URL={product_url}")
    
    try:
        # Initialiser le bridge Puppeteer
        puppeteer = PuppeteerBridge(headless=True)
        
        # Cas 1: Produit existant à mettre à jour
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                url = product.url
                extractor_class = get_extractor_for_url(url)
            except Product.DoesNotExist:
                logger.error(f"Produit avec ID {product_id} non trouvé")
                return False
                
        # Cas 2: Nouvelle URL à scraper
        elif product_url:
            url = product_url
            extractor_class = get_extractor_for_url(url)
            
            # Vérifier si le produit existe déjà avec cette URL
            existing = Product.objects.filter(url=url).first()
            if existing:
                product = existing
                product_id = existing.id
                logger.info(f"URL déjà existante, mise à jour du produit ID={product_id}")
            else:
                product = None
        else:
            logger.error("Aucun product_id ou product_url fourni")
            return False
        
        # Extraire les données produit via Puppeteer
        product_data = puppeteer.run_async(
            puppeteer.extract_product_data(url, extractor_class)
        )
        
        if not product_data:
            logger.error(f"Aucune donnée extraite pour {url}")
            return False
        
        # Déterminer le détaillant
        retailer_name = product_data.get('retailer', '').lower()
        retailer, _ = Retailer.objects.get_or_create(
            name=retailer_name,
            defaults={'domain': retailer_name, 'is_active': True}
        )
        
        # Traiter les données extraites
        with transaction.atomic():
            # Cas nouveau produit
            if not product:
                product = Product(
                    url=url,
                    retailer=retailer,
                    title=product_data.get('title', ''),
                    image_url=product_data.get('image_url', ''),
                    description=product_data.get('description', ''),
                    sku=product_data.get('sku', ''),
                    current_price=product_data.get('price', 0),
                    currency=product_data.get('currency', 'EUR'),
                    lowest_price=product_data.get('price', 0),
                    highest_price=product_data.get('price', 0),
                    last_checked=timezone.now(),
                    is_available=product_data.get('in_stock', True),
                    metadata=product_data.get('metadata', {}),
                )
                product.save()
            
            # Cas mise à jour produit existant
            else:
                product.title = product_data.get('title', product.title)
                product.image_url = product_data.get('image_url', product.image_url)
                product.description = product_data.get('description', product.description)
                
                current_price = product_data.get('price', product.current_price)
                
                # Mettre à jour prix min/max si nécessaire
                if current_price < product.lowest_price:
                    product.lowest_price = current_price
                if current_price > product.highest_price:
                    product.highest_price = current_price
                
                product.current_price = current_price
                product.currency = product_data.get('currency', product.currency)
                product.is_available = product_data.get('in_stock', product.is_available)
                product.last_checked = timezone.now()
                
                # Mettre à jour metadata en préservant les données existantes
                metadata = product.metadata.copy()
                metadata.update(product_data.get('metadata', {}))
                product.metadata = metadata
                
                product.save()
            
            # Créer un point de prix pour l'historique
            price_point = PricePoint(
                product=product,
                price=product_data.get('price', 0),
                currency=product_data.get('currency', 'EUR'),
                is_available=product_data.get('in_stock', True),
                is_deal=product_data.get('is_deal', False),
                source='scraper'
            )
            price_point.save()
            
            # Traiter les captures d'écran
            if 'screenshots' in product_data and product_data['screenshots']:
                for screenshot_type, path in product_data['screenshots'].items():
                    if path:
                        screenshot = Screenshot(
                            product=product,
                            price_point=price_point,
                            image=path.replace(f"{settings.MEDIA_ROOT}/", ""),  # Chemin relatif
                            type=screenshot_type
                        )
                        screenshot.save()
        
        logger.info(f"Scraping réussi pour produit ID={product.id}, URL={url}")
        return True
        
    except Exception as e:
        logger.exception(f"Erreur lors du scraping: {str(e)}")
        self.retry(exc=e)
        return False

@shared_task
def schedule_product_updates():
    """
    Planifie les mises à jour de produits en fonction de leur priorité
    """
    # Produits à mettre à jour urgemment (prix volatils ou forte demande)
    high_priority = Product.objects.filter(
        last_checked__lte=timezone.now() - timedelta(hours=4),
        metadata__contains={'priority': 'high'}
    ).values_list('id', flat=True)[:100]
    
    # Produits à mettre à jour normalement
    normal_priority = Product.objects.filter(
        last_checked__lte=timezone.now() - timedelta(hours=12)
    ).exclude(
        id__in=high_priority
    ).values_list('id', flat=True)[:200]
    
    # Produits à faible priorité (peu de volatilité)
    low_priority = Product.objects.filter(
        last_checked__lte=timezone.now() - timedelta(days=1)
    ).exclude(
        id__in=list(high_priority) + list(normal_priority)
    ).values_list('id', flat=True)[:300]
    
    # Planifier les tâches avec priorités différentes
    for product_id in high_priority:
        scrape_product.apply_async(args=[product_id], priority=1)
    
    for product_id in normal_priority:
        scrape_product.apply_async(args=[product_id], priority=5)
    
    for product_id in low_priority:
        scrape_product.apply_async(args=[product_id], priority=9)
    
    total = len(high_priority) + len(normal_priority) + len(low_priority)
    logger.info(f"Planifié {total} mises à jour de produits")
    
    return total

@shared_task
def process_scraping_queue():
    """
    Traite la file d'attente des tâches de scraping
    """
    # Récupérer les tâches en attente, par ordre de priorité
    pending_tasks = ScrapingTask.objects.filter(
        status='pending'
    ).order_by('priority', 'created_at')[:500]
    
    count = 0
    for task in pending_tasks:
        # Mettre à jour le statut
        task.status = 'processing'
        task.started_at = timezone.now()
        task.save()
        
        try:
            # Lancer la tâche de scraping
            if task.product_id:
                scrape_product.delay(product_id=task.product_id)
            else:
                scrape_product.delay(product_url=task.url)
            
            task.status = 'completed'
            count += 1
        except Exception as e:
            task.status = 'failed'
            task.error_message = str(e)
            logger.error(f"Erreur lors du traitement de la tâche {task.id}: {str(e)}")
        
        task.completed_at = timezone.now()
        task.save()
    
    logger.info(f"Traité {count} tâches de scraping")
    return count
