import logging
import random
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, F, Count
from datetime import timedelta

from monitoring.models import MonitoringTask, ProductMonitoringConfig
from products.models import Product

logger = logging.getLogger(__name__)

class TaskDistributor:
    """
    Utilitaire pour distribuer équitablement les tâches de monitoring
    et optimiser leur exécution
    """
    
    @staticmethod
    def load_balance_monitoring_tasks(max_tasks=200, time_window_minutes=5):
        """
        Distribue équitablement les tâches de monitoring entre les workers
        en tenant compte de la priorité et des fenêtres de temps
        
        Args:
            max_tasks: Nombre maximum de tâches à charger
            time_window_minutes: Fenêtre de temps en minutes pour le regroupement
            
        Returns:
            tuple: (high_priority_count, normal_priority_count, low_priority_count)
        """
        now = timezone.now()
        window_end = now + timedelta(minutes=time_window_minutes)
        
        # Récupérer toutes les tâches éligibles à exécuter
        pending_tasks = MonitoringTask.objects.filter(
            status='pending',
            scheduled_time__lte=window_end
        ).order_by('priority', 'scheduled_time')[:max_tasks*2]  # Marge pour le filtrage
        
        # Distribuer entre les queues de priorité
        high_priority = []
        normal_priority = []
        low_priority = []
        
        # Allouer ~40% des slots à la haute priorité, ~40% à la normale, ~20% à la basse
        high_slots = int(max_tasks * 0.4)
        normal_slots = int(max_tasks * 0.4)
        low_slots = max_tasks - high_slots - normal_slots
        
        for task in pending_tasks:
            if task.priority <= 3 and len(high_priority) < high_slots:
                high_priority.append(task)
            elif task.priority <= 7 and len(normal_priority) < normal_slots:
                normal_priority.append(task)
            elif len(low_priority) < low_slots:
                low_priority.append(task)
            
            # Arrêter si toutes les queues sont remplies
            if (len(high_priority) >= high_slots and 
                len(normal_priority) >= normal_slots and 
                len(low_priority) >= low_slots):
                break
        
        return high_priority, normal_priority, low_priority
    
    @staticmethod
    def optimize_queue_consumption(high_tasks, normal_tasks, low_tasks):
        """
        Optimise la consommation des queues en s'assurant que les tâches 
        de haute priorité sont traitées rapidement tout en permettant 
        aux tâches de basse priorité d'être traitées
        
        Args:
            high_tasks: Liste des tâches de haute priorité
            normal_tasks: Liste des tâches de priorité normale
            low_tasks: Liste des tâches de basse priorité
            
        Returns:
            list: Tâches ordonnées pour un traitement optimal
        """
        optimized_queue = []
        
        # S'assurer qu'au moins une tâche de chaque priorité est traitée
        # dans chaque cycle si possible
        high_idx, normal_idx, low_idx = 0, 0, 0
        
        # Ratio approximatif 4:2:1 (haute:normale:basse)
        while (high_idx < len(high_tasks) or 
               normal_idx < len(normal_tasks) or 
               low_idx < len(low_tasks)):
            
            # Ajouter 4 tâches de haute priorité si disponibles
            for _ in range(4):
                if high_idx < len(high_tasks):
                    optimized_queue.append(high_tasks[high_idx])
                    high_idx += 1
            
            # Ajouter 2 tâches de priorité normale si disponibles
            for _ in range(2):
                if normal_idx < len(normal_tasks):
                    optimized_queue.append(normal_tasks[normal_idx])
                    normal_idx += 1
            
            # Ajouter 1 tâche de basse priorité si disponible
            if low_idx < len(low_tasks):
                optimized_queue.append(low_tasks[low_idx])
                low_idx += 1
        
        return optimized_queue
    
    @staticmethod
    def assign_to_queues(tasks, randomize=True):
        """
        Assigne les tâches aux queues Celery appropriées
        
        Args:
            tasks: Liste des tâches à assigner
            randomize: Si True, randomise légèrement l'ordre des tâches
            
        Returns:
            dict: Dictionnaire avec les tâches par queue
        """
        if randomize:
            # Légère randomisation pour éviter que tous les workers
            # traitent les mêmes produits en même temps
            tasks = list(tasks)  # Copie pour ne pas modifier l'original
            random.shuffle(tasks)
        
        queues = {
            'high_priority': [],
            'default': [],
            'low_priority': []
        }
        
        with transaction.atomic():
            for task in tasks:
                # Déterminer la queue en fonction de la priorité
                if task.priority <= 3:
                    queue_name = 'high_priority'
                elif task.priority <= 7:
                    queue_name = 'default'
                else:
                    queue_name = 'low_priority'
                
                # Mettre à jour le statut
                task.status = 'scheduled'
                task.save(update_fields=['status', 'updated_at'])
                
                # Ajouter à la queue appropriée
                queues[queue_name].append(task)
        
        return queues
    
    @staticmethod
    def distribute_retailers_evenly(max_tasks=200):
        """
        Distribue les tâches en s'assurant que différents retailers sont monitorés
        simultanément pour ne pas surcharger un même site
        
        Args:
            max_tasks: Nombre maximum de tâches à traiter
            
        Returns:
            list: Tâches sélectionnées pour le traitement
        """
        now = timezone.now()
        
        # Récupérer les tâches éligibles
        pending_tasks = MonitoringTask.objects.filter(
            status='pending',
            scheduled_time__lte=now
        ).select_related('product__retailer')
        
        # Regrouper les tâches par retailer
        retailer_tasks = {}
        for task in pending_tasks:
            retailer_id = task.product.retailer_id
            if retailer_id not in retailer_tasks:
                retailer_tasks[retailer_id] = []
            
            retailer_tasks[retailer_id].append(task)
        
        # Distribuer équitablement entre les retailers
        distributed_tasks = []
        retailer_counts = {}
        
        # Continuer jusqu'à avoir max_tasks ou avoir épuisé toutes les tâches
        while len(distributed_tasks) < max_tasks and retailer_tasks:
            # Pour chaque retailer, prendre la tâche de plus haute priorité
            for retailer_id, tasks in list(retailer_tasks.items()):
                if not tasks:
                    # Supprimer le retailer s'il n'a plus de tâches
                    del retailer_tasks[retailer_id]
                    continue
                
                # Incrémenter le compteur de ce retailer
                retailer_counts[retailer_id] = retailer_counts.get(retailer_id, 0) + 1
                
                # Obtenir la tâche de plus haute priorité (plus petit chiffre)
                tasks.sort(key=lambda x: (x.priority, x.scheduled_time))
                task = tasks.pop(0)
                distributed_tasks.append(task)
                
                # Vérifier si on a atteint le nombre maximum de tâches
                if len(distributed_tasks) >= max_tasks:
                    break
            
            # Si tous les retailers ont été traités mais qu'il reste de la place,
            # on recommence un autre cycle
        
        return distributed_tasks
    
    @staticmethod
    def manage_resource_throttling():
        """
        Gère le throttling des ressources pour éviter de surcharger les sites
        en ajustant dynamiquement le nombre de tâches concurrentes par retailer
        
        Returns:
            dict: Limites de tâches concurrentes par retailer
        """
        # Récupérer le nombre de tâches en cours par retailer
        running_tasks = (MonitoringTask.objects.filter(status='running')
                         .select_related('product__retailer')
                         .values('product__retailer__name')
                         .annotate(count=Count('id')))
        
        # Calculer les limites dynamiques par retailer
        # Certains sites peuvent supporter plus de trafic que d'autres
        retailer_limits = {}
        
        for task_group in running_tasks:
            retailer_name = task_group['product__retailer__name']
            current_count = task_group['count']
            
            # Définir les limites en fonction du retailer
            if 'amazon' in retailer_name.lower():
                # Amazon peut supporter plus de requêtes
                limit = 20
            elif any(r in retailer_name.lower() for r in ['fnac', 'darty', 'boulanger']):
                # Grandes enseignes françaises
                limit = 10
            else:
                # Autres sites plus petits
                limit = 5
            
            retailer_limits[retailer_name] = {
                'current': current_count,
                'limit': limit,
                'available': max(0, limit - current_count)
            }
        
        return retailer_limits
    
    @staticmethod
    def throttle_tasks_by_retailer(tasks):
        """
        Applique le throttling aux tâches en fonction des limites par retailer
        
        Args:
            tasks: Liste de tâches à filtrer
            
        Returns:
            list: Tâches filtrées en respectant les limites par retailer
        """
        # Obtenir les limites actuelles
        retailer_limits = TaskDistributor.manage_resource_throttling()
        
        # Tracker le nombre de tâches sélectionnées par retailer
        selected_count = {retailer: 0 for retailer in retailer_limits}
        selected_tasks = []
        
        for task in tasks:
            retailer_name = task.product.retailer.name
            
            # Si ce retailer n'est pas encore dans les limites, l'ajouter
            if retailer_name not in selected_count:
                selected_count[retailer_name] = 0
                retailer_limits[retailer_name] = {
                    'current': 0,
                    'limit': 5,  # Valeur par défaut pour nouveaux retailers
                    'available': 5
                }
            
            # Vérifier si on peut ajouter cette tâche
            current_limit = retailer_limits[retailer_name]
            if selected_count[retailer_name] < current_limit['available']:
                selected_tasks.append(task)
                selected_count[retailer_name] += 1
        
        return selected_tasks
