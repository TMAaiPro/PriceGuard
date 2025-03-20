import logging
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.db.models import F, ExpressionWrapper, FloatField, Q, Case, When, Value

from products.models import Product
from ..models import MonitoringTask, ProductMonitoringConfig

logger = logging.getLogger(__name__)

class MonitoringSchedulingUtils:
    """
    Utilitaires pour la planification optimisée des tâches de monitoring
    """
    
    @classmethod
    def distribute_load(cls, max_tasks_per_hour, date=None):
        """
        Distribue les tâches de monitoring sur une journée pour répartir la charge
        
        Args:
            max_tasks_per_hour: Nombre maximal de tâches par heure
            date: Date pour laquelle effectuer la planification (aujourd'hui par défaut)
        
        Returns:
            int: Nombre de tâches planifiées
        """
        if date is None:
            date = timezone.now().date()
        
        start_dt = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()))
        end_dt = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.max.time()))
        
        # Nombre de tâches déjà planifiées par heure
        existing_tasks = (
            MonitoringTask.objects
            .filter(scheduled_time__range=(start_dt, end_dt))
            .extra({'hour': "EXTRACT(hour FROM scheduled_time)"})
            .values('hour')
            .annotate(count=Count('id'))
        )
        
        # Construire un dictionnaire des tâches par heure
        tasks_by_hour = {int(item['hour']): item['count'] for item in existing_tasks}
        
        # Trouver les produits à planifier
        configs = ProductMonitoringConfig.objects.filter(
            active=True,
            next_scheduled__range=(start_dt, end_dt)
        ).select_related('product')
        
        # Répartir les tâches par heure en fonction des capacités
        tasks_created = 0
        
        for config in configs:
            # Déterminer l'heure optimale
            next_hour = config.next_scheduled.hour
            best_hour = cls._find_best_hour(tasks_by_hour, next_hour, max_tasks_per_hour)
            
            if best_hour is not None:
                # Planifier à cette heure
                scheduled_time = start_dt + timedelta(hours=best_hour)
                
                # Créer la tâche
                with transaction.atomic():
                    task = MonitoringTask(
                        product=config.product,
                        scheduled_time=scheduled_time,
                        priority=int(config.priority_score)
                    )
                    task.save()
                    
                    # Mettre à jour le compteur pour cette heure
                    if best_hour in tasks_by_hour:
                        tasks_by_hour[best_hour] += 1
                    else:
                        tasks_by_hour[best_hour] = 1
                    
                    # Mettre à jour la config du produit
                    interval_hours = config.get_monitoring_interval()
                    next_scheduled = timezone.now() + timedelta(hours=interval_hours)
                    
                    config.next_scheduled = next_scheduled
                    config.save(update_fields=['next_scheduled', 'updated_at'])
                    
                    tasks_created += 1
            else:
                logger.warning(f"Impossible de planifier le produit {config.product.id}: toutes les heures sont pleines")
        
        logger.info(f"Distribution de charge: {tasks_created} tâches planifiées")
        return tasks_created
    
    @classmethod
    def _find_best_hour(cls, tasks_by_hour, preferred_hour, max_per_hour):
        """
        Trouve la meilleure heure pour planifier une tâche
        
        Args:
            tasks_by_hour: Dictionnaire avec nombre de tâches par heure
            preferred_hour: Heure préférée
            max_per_hour: Nombre maximal de tâches par heure
            
        Returns:
            int: Meilleure heure ou None si toutes sont pleines
        """
        # Essayer d'abord l'heure préférée
        if preferred_hour not in tasks_by_hour or tasks_by_hour[preferred_hour] < max_per_hour:
            return preferred_hour
        
        # Chercher dans les heures environnantes (d'abord +/-1h, puis +/-2h, etc.)
        for offset in range(1, 12):
            # Essayer l'heure préférée + offset
            hour_plus = (preferred_hour + offset) % 24
            if hour_plus not in tasks_by_hour or tasks_by_hour[hour_plus] < max_per_hour:
                return hour_plus
            
            # Essayer l'heure préférée - offset
            hour_minus = (preferred_hour - offset) % 24
            if hour_minus not in tasks_by_hour or tasks_by_hour[hour_minus] < max_per_hour:
                return hour_minus
        
        # Toutes les heures sont pleines
        return None
    
    @classmethod
    def rebalance_priorities(cls, batch_size=1000):
        """
        Rééquilibre les priorités des tâches en attente
        pour assurer une distribution équitable
        
        Args:
            batch_size: Nombre de tâches à traiter par lot
            
        Returns:
            int: Nombre de tâches mises à jour
        """
        pending_tasks = MonitoringTask.objects.filter(
            status='pending'
        ).select_related('product')[:batch_size]
        
        updated_count = 0
        
        for task in pending_tasks:
            try:
                # Récupérer la config de monitoring
                config = ProductMonitoringConfig.objects.get(product=task.product)
                
                # Mettre à jour la priorité si nécessaire
                new_priority = int(config.priority_score)
                if task.priority != new_priority:
                    task.priority = new_priority
                    task.save(update_fields=['priority', 'updated_at'])
                    updated_count += 1
                    
            except ProductMonitoringConfig.DoesNotExist:
                # Pas de config, laisser la priorité inchangée
                pass
        
        logger.info(f"Rééquilibré les priorités pour {updated_count} tâches")
        return updated_count
