import os
from celery import Celery
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Définir la variable d'environnement par défaut pour les settings Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'priceguard.settings')

# Initialiser l'application Celery
app = Celery('priceguard')

# Configuration depuis les settings Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Configuration spécifique
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=settings.TIME_ZONE,
    enable_utc=True,
    worker_prefetch_multiplier=1,  # Désactiver le prefetching pour une distribution équitable
    task_acks_late=True,  # Confirmer la tâche après exécution
    task_reject_on_worker_lost=True,  # Rejeter les tâches si le worker est perdu
    task_routes={
        'monitoring.tasks.high_priority_monitoring': {'queue': 'high_priority'},
        'monitoring.tasks.normal_priority_monitoring': {'queue': 'default'},
        'monitoring.tasks.low_priority_monitoring': {'queue': 'low_priority'},
        'monitoring.tasks.update_product_priorities': {'queue': 'maintenance'},
        'monitoring.tasks.cleanup_old_monitoring_data': {'queue': 'maintenance'},
    },
    broker_transport_options={
        'visibility_timeout': 3600,  # 1 heure
        'max_retries': 5,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.5,
    },
    broker_pool_limit=None,  # Désactiver la limite pour une meilleure scalabilité
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    
    # Configuration spécifique pour K8s
    broker_connection_timeout=30,
    result_backend_transport_options={
        'socket_timeout': 5,
        'socket_connect_timeout': 5,
    },
    
    # Configuration rate limiting
    task_default_rate_limit='1000/m',  # Limite globale de tâches
    
    # Configuration retry
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=300,  # 5 minutes
)

# Découverte automatique des tâches dans les applications Django
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    """Tâche de debug pour vérifier que Celery fonctionne correctement"""
    logger.info(f'Request: {self.request!r}')
