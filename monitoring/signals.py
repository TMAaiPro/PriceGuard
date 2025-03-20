import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import MonitoringTask, MonitoringResult
from .tasks import high_priority_monitoring, normal_priority_monitoring, low_priority_monitoring

logger = logging.getLogger(__name__)


@receiver(post_save, sender=MonitoringTask)
def handle_new_monitoring_task(sender, instance, created, **kwargs):
    """
    Signal handler pour traiter les nouvelles tâches de monitoring
    dès leur création si elles sont hautement prioritaires
    """
    if created and instance.status == 'pending' and instance.priority <= 3:
        logger.info(f"Traitement immédiat de la tâche haute priorité {instance.id}")
        
        # Mettre à jour le statut
        instance.status = 'scheduled'
        
        # Lancer la tâche immédiatement
        task = high_priority_monitoring.delay(str(instance.id))
        
        # Enregistrer l'ID de la tâche Celery
        instance.celery_task_id = task.id
        instance.save(update_fields=['status', 'celery_task_id', 'updated_at'])


@receiver(post_save, sender=MonitoringResult)
def handle_monitoring_result(sender, instance, created, **kwargs):
    """
    Signal handler pour traiter les résultats de monitoring
    dès leur création
    """
    if created:
        # Enregistrer dans les logs les changements importants
        changes = []
        
        if instance.price_changed:
            changes.append(f"prix: {instance.previous_price} -> {instance.current_price}")
        
        if instance.availability_changed:
            changes.append(f"disponibilité: {instance.previously_available} -> {instance.currently_available}")
        
        if changes:
            logger.info(
                f"Changements détectés pour {instance.product}: {', '.join(changes)}"
            )
        
        # Si une alerte est déclenchée, enregistrer dans les logs
        if instance.alert_triggered:
            logger.info(
                f"Alerte déclenchée pour {instance.product}: {instance.alert_type} - {instance.alert_message}"
            )
