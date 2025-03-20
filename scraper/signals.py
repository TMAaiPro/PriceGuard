import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

from .models import PricePoint, Product
from .tasks import scrape_product

logger = logging.getLogger(__name__)

@receiver(post_save, sender=PricePoint)
def handle_price_change(sender, instance, created, **kwargs):
    """
    Réagit aux changements de prix pour déclencher des actions
    comme les notifications ou les analyses
    """
    if not created:
        return
    
    product = instance.product
    
    # Vérifier si le prix a changé de manière significative
    previous_points = PricePoint.objects.filter(
        product=product,
        timestamp__lt=instance.timestamp
    ).order_by('-timestamp')[:1]
    
    if not previous_points:
        # Premier point de prix, pas de comparaison à faire
        return
    
    previous_point = previous_points[0]
    price_diff = instance.price - previous_point.price
    
    # Si le prix a baissé de plus de 5%
    if price_diff < 0 and abs(price_diff) / previous_point.price > Decimal('0.05'):
        logger.info(f"Baisse de prix significative détectée pour {product.title}: {previous_point.price} -> {instance.price}")
        
        # Envoyer des notifications (à implémenter dans d'autres modules)
        try:
            from notifications.tasks import send_price_drop_notification
            send_price_drop_notification.delay(
                product_id=product.id,
                old_price=float(previous_point.price),
                new_price=float(instance.price),
                currency=instance.currency
            )
        except ImportError:
            logger.warning("Module de notifications non disponible")
    
    # Si un produit qui n'était pas disponible le devient
    if instance.is_available and not previous_point.is_available:
        logger.info(f"Produit {product.title} à nouveau disponible")
        
        # Envoyer des notifications (à implémenter dans d'autres modules)
        try:
            from notifications.tasks import send_back_in_stock_notification
            send_back_in_stock_notification.delay(
                product_id=product.id,
                price=float(instance.price),
                currency=instance.currency
            )
        except ImportError:
            logger.warning("Module de notifications non disponible")

@receiver(post_save, sender=ScrapingTask)
def handle_new_scraping_task(sender, instance, created, **kwargs):
    """
    Déclenche le scraping lorsqu'une nouvelle tâche est créée avec
    le statut 'pending'
    """
    from .models import ScrapingTask  # Import ici pour éviter les imports circulaires
    
    if not created:
        return
    
    if instance.status == 'pending':
        logger.info(f"Nouvelle tâche de scraping créée: {instance.id}")
        
        # Lancer la tâche immédiatement si priorité haute
        if instance.priority <= 3:
            if instance.product_id:
                task = scrape_product.delay(product_id=instance.product_id)
            else:
                task = scrape_product.delay(product_url=instance.url)
            
            # Mettre à jour l'ID de la tâche Celery
            ScrapingTask.objects.filter(id=instance.id).update(
                celery_task_id=task.id,
                status='processing'
            )
