import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import MonitoringTask, MonitoringResult
from .tasks import process_monitoring_alert

logger = logging.getLogger(__name__)

@receiver(post_save, sender=MonitoringTask)
def handle_new_monitoring_task(sender, instance, created, **kwargs):
    """
    Signal déclenché lorsqu'une nouvelle tâche de monitoring est créée.
    Permet de déclencher des actions automatiques basées sur l'état de la tâche.
    """
    if created:
        logger.debug(f"Nouvelle tâche de monitoring créée: {instance.id}")
    else:
        # Une mise à jour de la tâche, vérifier s'il y a eu un changement de statut
        if instance.tracker.has_changed('status'):
            old_status = instance.tracker.previous('status')
            new_status = instance.status
            logger.info(f"Tâche {instance.id}: Statut changé de {old_status} à {new_status}")
            
            # Actions spécifiques selon les transitions d'état
            if new_status == 'completed':
                logger.info(f"Tâche {instance.id} terminée avec succès")
            elif new_status == 'failed':
                logger.warning(f"Tâche {instance.id} a échoué: {instance.error_message}")

@receiver(post_save, sender=MonitoringResult)
def handle_new_monitoring_result(sender, instance, created, **kwargs):
    """
    Signal déclenché lorsqu'un nouveau résultat de monitoring est créé.
    Permet de traiter automatiquement les alertes et de mettre à jour les statistiques.
    """
    if created:
        logger.debug(f"Nouveau résultat de monitoring créé: {instance.id}")
        
        # Si une alerte est déclenchée et n'a pas encore été traitée
        if instance.alert_triggered and not getattr(instance, '_alert_processed', False):
            logger.info(f"Alerte déclenchée dans le résultat {instance.id}: {instance.alert_type}")
            
            # Marquer l'alerte comme traitée pour éviter les doubles traitements
            instance._alert_processed = True
            
            # Traiter l'alerte de manière asynchrone
            process_monitoring_alert.delay(str(instance.id))
