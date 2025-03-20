import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from .models import MonitoringTask, ProductMonitoringConfig, MonitoringResult
from .services import MonitoringScheduler, MonitoringPrioritizer, MonitoringResultsAnalyzer, MonitoringStatsService
from products.models import Product
from scraper.bridge.puppeteer_bridge import PuppeteerBridge
from scraper.extractors.base import get_extractor_for_url

logger = logging.getLogger(__name__)

# Tâches de monitoring principal

@shared_task(bind=True, queue='high_priority', max_retries=3, default_retry_delay=30)
def high_priority_monitoring(self, task_id):
    """
    Tâche de monitoring à haute priorité
    
    Args:
        task_id: ID de la tâche de monitoring
    """
    return _perform_monitoring(self, task_id)


@shared_task(bind=True, queue='default', max_retries=3, default_retry_delay=60)
def normal_priority_monitoring(self, task_id):
    """
    Tâche de monitoring à priorité normale
    
    Args:
        task_id: ID de la tâche de monitoring
    """
    return _perform_monitoring(self, task_id)


@shared_task(bind=True, queue='low_priority', max_retries=3, default_retry_delay=120)
def low_priority_monitoring(self, task_id):
    """
    Tâche de monitoring à basse priorité
    
    Args:
        task_id: ID de la tâche de monitoring
    """
    return _perform_monitoring(self, task_id)


def _perform_monitoring(celery_task, task_id):
    """
    Implémentation commune pour les tâches de monitoring
    
    Args:
        celery_task: Tâche Celery actuelle
        task_id: ID de la tâche de monitoring
    
    Returns:
        dict: Résultat du monitoring
    """
    logger.info(f"Starting monitoring task {task_id}")
    
    try:
        # Récupérer la tâche
        task = MonitoringTask.objects.select_related('product').get(id=task_id)
        
        # Marquer comme en cours
        task.mark_as_running()
        
        # Récupérer l'URL du produit
        product = task.product
        url = product.url
        
        # Déterminer l'extracteur approprié
        extractor_class = get_extractor_for_url(url)
        
        # Initialiser le bridge Puppeteer
        puppeteer = PuppeteerBridge(headless=True)
        
        try:
            # Extraire les données produit via Puppeteer
            product_data = puppeteer.run_async(
                puppeteer.extract_product_data(url, extractor_class)
            )
            
            if not product_data:
                raise ValueError("Aucune donnée extraite")
            
            # Analyser les résultats
            monitoring_result = MonitoringResultsAnalyzer.analyze_result(product, product_data)
            
            # Mettre à jour le produit avec les dernières données
            with transaction.atomic():
                product.current_price = product_data.get('price', product.current_price)
                product.is_available = product_data.get('in_stock', product.is_available)
                product.last_checked = timezone.now()
                
                # Mettre à jour prix min/max si nécessaire
                if product.current_price < product.lowest_price:
                    product.lowest_price = product.current_price
                if product.current_price > product.highest_price:
                    product.highest_price = product.current_price
                
                product.save()
            
            # Marquer la tâche comme terminée
            task.mark_as_completed(result_data={
                'result_id': str(monitoring_result.id),
                'price_changed': monitoring_result.price_changed,
                'availability_changed': monitoring_result.availability_changed,
                'alert_triggered': monitoring_result.alert_triggered
            })
            
            # Si une alerte est déclenchée, traiter l'alerte
            if monitoring_result.alert_triggered:
                process_monitoring_alert.delay(str(monitoring_result.id))
            
            logger.info(f"Monitoring task {task_id} completed successfully")
            return {
                'status': 'success',
                'result_id': str(monitoring_result.id)
            }
            
        except Exception as e:
            logger.error(f"Error during monitoring task {task_id}: {str(e)}")
            
            # Tenter de réessayer
            failure = task.mark_as_failed(str(e))
            
            if not failure:  # Si nous n'avons pas atteint le max_retries
                celery_task.retry(exc=e)
            
            raise
            
    except MonitoringTask.DoesNotExist:
        logger.error(f"Monitoring task {task_id} not found")
        return {
            'status': 'error',
            'message': f"Task {task_id} not found"
        }


@shared_task(queue='default')
def process_monitoring_alert(result_id):
    """
    Traite une alerte générée par le monitoring
    
    Args:
        result_id: ID du résultat de monitoring
    """
    try:
        result = MonitoringResult.objects.select_related('product').get(id=result_id)
        
        # Implémenter la logique de notification ici
        # ...
        
        logger.info(f"Processed alert for result {result_id}, type: {result.alert_type}")
        return {
            'status': 'success',
            'alert_type': result.alert_type
        }
        
    except MonitoringResult.DoesNotExist:
        logger.error(f"Monitoring result {result_id} not found")
        return {
            'status': 'error',
            'message': f"Result {result_id} not found"
        }


# Tâches de scheduling

@shared_task(queue='maintenance')
def schedule_monitoring_tasks(batch_size=1000):
    """
    Planifie les tâches de monitoring pour les produits qui doivent être vérifiés
    
    Args:
        batch_size: Nombre de produits à traiter par lot
    """
    count = MonitoringScheduler.schedule_products_for_monitoring(batch_size)
    return {
        'status': 'success',
        'scheduled_count': count
    }


@shared_task(queue='maintenance')
def process_monitoring_queue(max_tasks=200):
    """
    Traite la file d'attente des tâches de monitoring en les affectant
    aux queues Celery appropriées
    
    Args:
        max_tasks: Nombre maximum de tâches à traiter
    """
    # Récupérer les tâches à traiter
    pending_tasks = MonitoringTask.objects.filter(
        status='pending'
    ).order_by('priority', 'scheduled_time')[:max_tasks]
    
    high_prio_count = 0
    normal_prio_count = 0
    low_prio_count = 0
    
    for task in pending_tasks:
        # Mettre à jour le statut
        task.status = 'scheduled'
        
        # Déterminer la queue en fonction de la priorité
        if task.priority <= 3:
            celery_task = high_priority_monitoring.delay(str(task.id))
            high_prio_count += 1
        elif task.priority <= 7:
            celery_task = normal_priority_monitoring.delay(str(task.id))
            normal_prio_count += 1
        else:
            celery_task = low_priority_monitoring.delay(str(task.id))
            low_prio_count += 1
        
        # Enregistrer l'ID de la tâche Celery
        task.celery_task_id = celery_task.id
        task.save(update_fields=['status', 'celery_task_id', 'updated_at'])
    
    total = high_prio_count + normal_prio_count + low_prio_count
    logger.info(f"Processed {total} tasks ({high_prio_count} high, {normal_prio_count} normal, {low_prio_count} low)")
    
    return {
        'status': 'success',
        'total_processed': total,
        'high_priority': high_prio_count,
        'normal_priority': normal_prio_count,
        'low_priority': low_prio_count
    }


# Tâches de maintenance

@shared_task(queue='maintenance')
def update_product_priorities(batch_size=5000):
    """
    Met à jour les priorités des produits en fonction de divers facteurs
    
    Args:
        batch_size: Nombre de produits à traiter par lot
    """
    count = MonitoringPrioritizer.update_product_priorities(batch_size)
    return {
        'status': 'success',
        'updated_count': count
    }


@shared_task(queue='maintenance')
def cleanup_old_monitoring_data(days_to_keep=30):
    """
    Nettoie les anciennes données de monitoring
    
    Args:
        days_to_keep: Nombre de jours de données à conserver
    """
    cutoff_date = timezone.now() - timedelta(days=days_to_keep)
    
    # Supprimer les anciennes tâches terminées
    old_tasks = MonitoringTask.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['completed', 'failed', 'cancelled']
    )
    tasks_count = old_tasks.count()
    old_tasks.delete()
    
    logger.info(f"Deleted {tasks_count} old monitoring tasks")
    
    return {
        'status': 'success',
        'deleted_tasks_count': tasks_count
    }


@shared_task(queue='maintenance')
def update_monitoring_stats():
    """Met à jour les statistiques quotidiennes de monitoring"""
    stats = MonitoringStatsService.update_daily_stats()
    return {
        'status': 'success',
        'date': stats.date.isoformat(),
        'total_tasks': stats.total_tasks
    }


# Configuration des tâches périodiques Celery Beat
CELERY_BEAT_SCHEDULE = {
    'schedule-monitoring-tasks': {
        'task': 'monitoring.tasks.schedule_monitoring_tasks',
        'schedule': timedelta(minutes=5),
        'kwargs': {'batch_size': 1000},
    },
    'process-monitoring-queue': {
        'task': 'monitoring.tasks.process_monitoring_queue',
        'schedule': timedelta(minutes=2),
        'kwargs': {'max_tasks': 200},
    },
    'update-product-priorities': {
        'task': 'monitoring.tasks.update_product_priorities',
        'schedule': timedelta(hours=6),
        'kwargs': {'batch_size': 5000},
    },
    'cleanup-old-monitoring-data': {
        'task': 'monitoring.tasks.cleanup_old_monitoring_data',
        'schedule': timedelta(days=1),
        'kwargs': {'days_to_keep': 30},
    },
    'update-monitoring-stats': {
        'task': 'monitoring.tasks.update_monitoring_stats',
        'schedule': timedelta(hours=1),
    },
}
