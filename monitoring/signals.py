import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import MonitoringResult, ProductMonitoringConfig
from products.models import Product

logger = logging.getLogger(__name__)

@receiver(post_save, sender=MonitoringResult)
def handle_monitoring_result(sender, instance, created, **kwargs):
    """
    Gère les résultats de monitoring après leur création
    
    Args:
        sender: Modèle qui a déclenché le signal
        instance: Instance du MonitoringResult
        created: True si c'est une nouvelle instance
    """
    if not created:
        return
    
    # Si une alerte a été déclenchée, on peut envoyer des notifications
    if instance.alert_triggered:
        logger.info(f"Alerte déclenchée pour le produit {instance.product.id}: {instance.alert_type}")
        
        # Code pour envoyer des notifications
        # (Implémenter dans un module séparé, puis appeler ici)

@receiver(post_save, sender=Product)
def create_monitoring_config_for_product(sender, instance, created, **kwargs):
    """
    Crée automatiquement une configuration de monitoring pour les nouveaux produits
    
    Args:
        sender: Modèle qui a déclenché le signal
        instance: Instance du Product
        created: True si c'est une nouvelle instance
    """
    if created:
        # Vérifier si une configuration existe déjà
        if not hasattr(instance, 'monitoring_config'):
            ProductMonitoringConfig.objects.create(
                product=instance,
                frequency='normal',
                active=True
            )
            logger.info(f"Configuration de monitoring créée pour le produit {instance.id}")
