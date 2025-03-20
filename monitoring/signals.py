from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import MonitoringResult, MonitoringTask, ProductMonitoringConfig
from products.models import Product, PricePoint
from .tasks import process_monitoring_alert
from .services import MonitoringPrioritizer

@receiver(post_save, sender=MonitoringResult)
def handle_monitoring_result(sender, instance, created, **kwargs):
    """
    Réagit à la création d'un résultat de monitoring
    - Crée un point de prix dans l'historique
    - Traite les alertes si nécessaire
    """
    if not created:
        return
    
    # Créer un point de prix pour l'historique
    PricePoint.objects.create(
        product=instance.product,
        price=instance.current_price,
        currency=instance.product.currency,
        is_available=instance.currently_available,
        is_deal=instance.is_deal,
        source='monitoring'
    )
    
    # Si une alerte est déclenchée, la traiter de manière asynchrone
    if instance.alert_triggered:
        process_monitoring_alert.delay(str(instance.id))

@receiver(post_save, sender=Product)
def create_monitoring_config(sender, instance, created, **kwargs):
    """
    Crée automatiquement une configuration de monitoring pour les nouveaux produits
    """
    if created:
        # Vérifier si une configuration existe déjà
        if not hasattr(instance, 'monitoring_config'):
            config = ProductMonitoringConfig(
                product=instance,
                frequency='normal',  # Fréquence par défaut
                active=True,
                next_scheduled=timezone.now()  # Planifier un premier monitoring immédiatement
            )
            config.save()
            
            # Calcul initial du score de priorité
            MonitoringPrioritizer._update_product_priority(instance)

@receiver(post_save, sender=MonitoringTask)
def handle_task_completion(sender, instance, **kwargs):
    """
    Réagit à la complétion d'une tâche de monitoring
    """
    # Si la tâche vient d'être marquée comme terminée
    if instance.status == 'completed' and instance.completed_at:
        # Mettre à jour la date de dernière vérification du produit
        Product.objects.filter(id=instance.product_id).update(
            last_checked=instance.completed_at
        )
        
        # Mettre à jour la configuration de monitoring
        try:
            config = ProductMonitoringConfig.objects.get(product_id=instance.product_id)
            config.last_monitored = instance.completed_at
            
            # Recalculer la prochaine vérification planifiée
            interval_hours = config.get_monitoring_interval()
            config.next_scheduled = instance.completed_at + timezone.timedelta(hours=interval_hours)
            
            config.save(update_fields=['last_monitored', 'next_scheduled', 'updated_at'])
        except ProductMonitoringConfig.DoesNotExist:
            pass  # La configuration a peut-être été supprimée
