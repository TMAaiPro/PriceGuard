import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import MonitoringResult, ProductMonitoringConfig
from .tasks import process_monitoring_alert

logger = logging.getLogger(__name__)

@receiver(post_save, sender=MonitoringResult)
def handle_monitoring_result_saved(sender, instance, created, **kwargs):
    """
    Gère les actions à effectuer lorsqu'un résultat de monitoring est sauvegardé
    """
    if not created:
        return
        
    # Mettre à jour la date de dernier monitoring pour le produit
    try:
        config = ProductMonitoringConfig.objects.get(product=instance.product)
        config.last_monitored = instance.monitored_at
        
        # Recalculer la prochaine date de vérification
        interval_hours = config.get_monitoring_interval()
        config.next_scheduled = instance.monitored_at + timezone.timedelta(hours=interval_hours)
        
        config.save(update_fields=['last_monitored', 'next_scheduled', 'updated_at'])
        logger.debug(f"Updated monitoring config for product {instance.product.id}")
    except ProductMonitoringConfig.DoesNotExist:
        # Créer une configuration si elle n'existe pas
        ProductMonitoringConfig.objects.create(
            product=instance.product,
            last_monitored=instance.monitored_at,
            next_scheduled=instance.monitored_at + timezone.timedelta(hours=12)  # Valeur par défaut
        )
        logger.info(f"Created new monitoring config for product {instance.product.id}")
    
    # Traiter les alertes
    if instance.alert_triggered:
        logger.info(f"Alert triggered for product {instance.product.id}: {instance.alert_type}")

@receiver(post_save, sender=ProductMonitoringConfig)
def handle_config_saved(sender, instance, created, **kwargs):
    """
    Gère les actions à effectuer lorsqu'une configuration de monitoring est sauvegardée
    """
    if created:
        logger.info(f"New monitoring config created for product {instance.product.id}")
        
        # Si aucune date de prochaine vérification n'est définie, la calculer
        if not instance.next_scheduled and instance.last_monitored:
            interval_hours = instance.get_monitoring_interval()
            instance.next_scheduled = instance.last_monitored + timezone.timedelta(hours=interval_hours)
            instance.save(update_fields=['next_scheduled'])
