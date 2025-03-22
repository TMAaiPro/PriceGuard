import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
import uuid

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def schedule_notification_delivery(self, user_id, alert_id, channel, batch_type, priority=5):
    """
    Planifie la livraison d'une notification
    
    Args:
        user_id: ID de l'utilisateur
        alert_id: ID de l'alerte
        channel: Canal de notification
        batch_type: Type de batch ('immediate', 'hourly', 'daily')
        priority: Priorité de la notification (1-10)
    """
    from notifications.services import NotificationService
    from django.contrib.auth import get_user_model
    from alerts.models import Alert
    
    User = get_user_model()
    
    try:
        # Vérifier si l'utilisateur et l'alerte existent
        try:
            user = User.objects.get(id=user_id)
            alert = Alert.objects.get(id=alert_id)
        except (User.DoesNotExist, Alert.DoesNotExist) as e:
            logger.error(f"Erreur de planification de notification: {str(e)}")
            return False
        
        # Appliquer le throttling basé sur le canal et l'utilisateur
        if not should_send_notification(user_id, channel, alert_id):
            logger.info(f"Notification throttled pour user={user_id}, channel={channel}")
            return False
        
        # Si notification immédiate
        if batch_type == 'immediate':
            # Traiter immédiatement
            NotificationService.process_immediate_notification(
                user_id=user_id,
                alert_id=alert_id,
                channel=channel,
                priority=priority
            )
            return True
        
        # Sinon, ajouter à un batch
        from notifications.models import NotificationBatch, NotificationBatchItem
        
        # Rechercher un batch existant pour l'utilisateur, canal et type
        # qui n'a pas encore été traité
        existing_batch = NotificationBatch.objects.filter(
            user_id=user_id,
            channel=channel,
            batch_type=batch_type,
            status='pending',
            scheduled_for__gt=timezone.now()  # Pas encore prévu pour envoi
        ).first()
        
        # Si batch existant, ajouter l'alerte
        if existing_batch:
            # Vérifier si l'alerte n'est pas déjà dans ce batch
            if not NotificationBatchItem.objects.filter(
                batch=existing_batch,
                alert_id=alert_id
            ).exists():
                # Ajouter l'alerte au batch
                NotificationBatchItem.objects.create(
                    batch=existing_batch,
                    alert_id=alert_id
                )
                
                # Incrémenter le compteur
                existing_batch.items_count = existing_batch.items_count + 1
                existing_batch.save(update_fields=['items_count'])
            
            return True
        
        # Sinon, créer un nouveau batch
        batch = NotificationService.create_notification_batch(
            user_id=user_id,
            channel=channel,
            batch_type=batch_type,
            alerts=[alert]
        )
        
        # Planifier le traitement du batch
        process_notification_batch.apply_async(
            args=[str(batch.id)],
            eta=batch.scheduled_for
        )
        
        return True
        
    except Exception as e:
        logger.exception(f"Erreur lors de la planification de notification: {str(e)}")
        self.retry(exc=e, countdown=60)  # Réessayer dans 1 minute
        return False


@shared_task(bind=True, max_retries=3)
def process_notification_batch(self, batch_id):
    """
    Traite un batch de notifications
    
    Args:
        batch_id: ID du batch à traiter
    """
    from notifications.services import NotificationService
    
    try:
        success = NotificationService.process_notification_batch(batch_id)
        return success
        
    except Exception as e:
        logger.exception(f"Erreur lors du traitement du batch {batch_id}: {str(e)}")
        self.retry(exc=e, countdown=300)  # Réessayer dans 5 minutes
        return False


@shared_task
def process_pending_batches():
    """Traite tous les batchs en attente qui sont prêts à être envoyés"""
    from notifications.models import NotificationBatch
    
    # Récupérer les batchs prêts à être envoyés
    now = timezone.now()
    ready_batches = NotificationBatch.objects.filter(
        status='pending',
        scheduled_for__lte=now  # Prévu pour maintenant ou avant
    )
    
    count = 0
    for batch in ready_batches:
        # Planifier le traitement de chaque batch
        process_notification_batch.delay(str(batch.id))
        count += 1
    
    logger.info(f"Planifié le traitement de {count} batchs en attente")
    return count


@shared_task(bind=True, max_retries=5)
def retry_failed_notification(self, delivery_id):
    """
    Réessaie une notification qui a échoué
    
    Args:
        delivery_id: ID de la livraison à réessayer
    """
    from notifications.models import NotificationDelivery
    from notifications.services import NotificationService
    
    try:
        delivery = NotificationDelivery.objects.get(id=delivery_id)
        
        # Vérifier si la notification est en échec
        if delivery.status != 'failed':
            return True
        
        # Incrémenter le compteur de tentatives
        delivery.retry_count += 1
        delivery.save(update_fields=['retry_count'])
        
        # Si trop de tentatives, abandonner
        if delivery.retry_count > 5:
            logger.warning(f"Abandon de la notification {delivery_id} après {delivery.retry_count} tentatives")
            return False
        
        # Envoyer via l'adaptateur approprié
        adapter = NotificationService._get_channel_adapter(delivery.channel)
        success, message_id, error = adapter.send_notification(delivery)
        
        if success:
            delivery.message_id = message_id
            delivery.mark_as_sent()
            
            # Mettre à jour l'alerte si nécessaire
            if delivery.alert and not delivery.alert.was_notified:
                delivery.alert.was_notified = True
                delivery.alert.notification_sent_at = timezone.now()
                delivery.alert.save(update_fields=['was_notified', 'notification_sent_at'])
            
            return True
        else:
            delivery.error_message = error
            delivery.save(update_fields=['error_message'])
            
            # Réessayer plus tard avec backoff exponentiel
            retry_delay = 300 * (2 ** (delivery.retry_count - 1))  # 5min, 10min, 20min, ...
            self.retry(countdown=retry_delay)
            
            return False
            
    except NotificationDelivery.DoesNotExist:
        logger.error(f"Livraison introuvable: {delivery_id}")
        return False
    except Exception as e:
        logger.exception(f"Erreur lors de la réessaie de la notification {delivery_id}: {str(e)}")
        self.retry(exc=e, countdown=300)
        return False


@shared_task(bind=True, max_retries=3)
def retry_failed_batch(self, batch_id):
    """
    Réessaie un batch de notifications qui a échoué
    
    Args:
        batch_id: ID du batch à réessayer
    """
    from notifications.models import NotificationBatch
    
    try:
        batch = NotificationBatch.objects.get(id=batch_id)
        
        # Vérifier si le batch est en échec
        if batch.status != 'failed':
            return True
        
        # Réinitialiser le statut
        batch.status = 'pending'
        batch.error_message = ''
        batch.save(update_fields=['status', 'error_message'])
        
        # Replanifier le traitement
        process_notification_batch.delay(str(batch.id))
        
        return True
        
    except NotificationBatch.DoesNotExist:
        logger.error(f"Batch introuvable: {batch_id}")
        return False
    except Exception as e:
        logger.exception(f"Erreur lors de la réessaie du batch {batch_id}: {str(e)}")
        self.retry(exc=e, countdown=300)
        return False


@shared_task
def clean_expired_notifications():
    """Nettoie les notifications expirées"""
    from notifications.models import InAppNotification
    
    # Supprimer les notifications in-app expirées
    now = timezone.now()
    result = InAppNotification.objects.filter(
        expires_at__lt=now
    ).delete()
    
    deleted_count = result[0] if result and isinstance(result, tuple) else 0
    logger.info(f"Supprimé {deleted_count} notifications expirées")
    
    return deleted_count


@shared_task(bind=True)
def update_user_engagement_metrics(self, user_id):
    """
    Met à jour les métriques d'engagement pour un utilisateur
    
    Args:
        user_id: ID de l'utilisateur
    """
    from notifications.services import EngagementService
    
    try:
        metrics = EngagementService.update_user_metrics(user_id)
        return True if metrics else False
    except Exception as e:
        logger.exception(f"Erreur lors de la mise à jour des métriques pour l'utilisateur {user_id}: {str(e)}")
        self.retry(exc=e, countdown=300)
        return False


@shared_task
def update_all_engagement_metrics():
    """Met à jour les métriques d'engagement pour tous les utilisateurs"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    user_ids = User.objects.values_list('id', flat=True)
    count = 0
    
    for user_id in user_ids:
        update_user_engagement_metrics.delay(str(user_id))
        count += 1
    
    logger.info(f"Planifié la mise à jour des métriques pour {count} utilisateurs")
    return count


def should_send_notification(user_id, channel, alert_id):
    """
    Vérifie si une notification doit être envoyée en fonction des règles de throttling
    
    Args:
        user_id: ID de l'utilisateur
        channel: Canal de notification
        alert_id: ID de l'alerte
        
    Returns:
        bool: True si la notification doit être envoyée
    """
    from django.core.cache import cache
    from django.conf import settings
    
    # Récupérer les règles de throttling
    channel_config = settings.NOTIFICATION_CHANNELS.get(channel, {}).get('settings', {})
    throttle_rate = channel_config.get('throttle_rate', '100/hour')
    
    # Parser le taux (format: nombre/période)
    parts = throttle_rate.split('/')
    if len(parts) != 2:
        return True  # En cas d'erreur de config, autoriser l'envoi
    
    limit = int(parts[0])
    period = parts[1]
    
    # Convertir la période en secondes
    if period == 'second':
        period_seconds = 1
    elif period == 'minute':
        period_seconds = 60
    elif period == 'hour':
        period_seconds = 3600
    elif period == 'day':
        period_seconds = 86400
    else:
        period_seconds = 3600  # Par défaut 1 heure
    
    # Vérifier si l'alerte a déjà été notifiée récemment sur ce canal
    alert_key = f"notification:alert:{alert_id}:{channel}"
    if cache.get(alert_key):
        return False  # Éviter les doublons pour la même alerte
    
    # Clé pour le throttling utilisateur/canal
    cache_key = f"notification:throttle:{user_id}:{channel}"
    
    # Récupérer le compteur actuel
    current_count = cache.get(cache_key, 0)
    
    # Si limite atteinte, bloquer l'envoi
    if current_count >= limit:
        return False
    
    # Incrémenter le compteur
    cache.set(cache_key, current_count + 1, period_seconds)
    
    # Marquer l'alerte comme notifiée sur ce canal
    cache.set(alert_key, True, 3600)  # 1 heure
    
    return True
