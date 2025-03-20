import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Sum, Avg, Min, Max, Count, Q, Case, When, Value, IntegerField
from .models import MonitoringTask, ProductMonitoringConfig, MonitoringResult, MonitoringStats
from products.models import Product, PricePoint

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    """
    Service responsable de la planification des tâches de monitoring
    """
    
    @classmethod
    def schedule_products_for_monitoring(cls, batch_size=1000):
        """
        Planifie le monitoring des produits qui doivent être vérifiés
        
        Args:
            batch_size: Nombre de produits à traiter par lot
        
        Returns:
            int: Nombre de tâches planifiées
        """
        now = timezone.now()
        
        # Sélectionner les produits qui doivent être monitorés
        configs = ProductMonitoringConfig.objects.filter(
            active=True,
            next_scheduled__lte=now
        ).select_related('product')[:batch_size]
        
        tasks_created = 0
        
        with transaction.atomic():
            for config in configs:
                # Créer une nouvelle tâche
                task = MonitoringTask(
                    product=config.product,
                    scheduled_time=now,
                    priority=int(config.priority_score)
                )
                task.save()
                
                # Mettre à jour la config
                interval_hours = config.get_monitoring_interval()
                next_scheduled = now + timedelta(hours=interval_hours)
                
                config.next_scheduled = next_scheduled
                config.save(update_fields=['next_scheduled', 'updated_at'])
                
                tasks_created += 1
        
        logger.info(f"Scheduled {tasks_created} products for monitoring")
        return tasks_created
    
    @classmethod
    def schedule_specific_product(cls, product_id, priority=None):
        """
        Planifie le monitoring d'un produit spécifique immédiatement
        
        Args:
            product_id: ID du produit à monitorer
            priority: Priorité optionnelle à assigner (1-10)
            
        Returns:
            MonitoringTask: Tâche créée ou None si le produit n'existe pas
        """
        try:
            product = Product.objects.get(id=product_id)
            
            # Récupérer ou créer la configuration de monitoring
            config, created = ProductMonitoringConfig.objects.get_or_create(
                product=product,
                defaults={'active': True}
            )
            
            # Déterminer la priorité
            if priority is None:
                priority = int(config.priority_score)
            
            # Créer la tâche
            now = timezone.now()
            task = MonitoringTask(
                product=product,
                scheduled_time=now,
                priority=priority
            )
            task.save()
            
            # Mettre à jour la date de prochaine vérification
            config.next_scheduled = now + timedelta(hours=config.get_monitoring_interval())
            config.save(update_fields=['next_scheduled', 'updated_at'])
            
            logger.info(f"Scheduled immediate monitoring for product {product_id}")
            return task
            
        except Product.DoesNotExist:
            logger.warning(f"Attempted to schedule monitoring for non-existent product {product_id}")
            return None
    
    @classmethod
    def update_product_monitoring_frequency(cls, product_id, frequency, custom_hours=None):
        """
        Met à jour la fréquence de monitoring d'un produit
        
        Args:
            product_id: ID du produit
            frequency: Nouvelle fréquence ('high', 'normal', 'low', 'custom')
            custom_hours: Heures personnalisées si frequency='custom'
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            config = ProductMonitoringConfig.objects.get(product_id=product_id)
            
            config.frequency = frequency
            if frequency == 'custom' and custom_hours is not None:
                config.custom_frequency_hours = max(1, min(168, custom_hours))  # Entre 1h et 7 jours
            
            # Recalculer la prochaine vérification
            if config.last_monitored:
                interval_hours = config.get_monitoring_interval()
                config.next_scheduled = config.last_monitored + timedelta(hours=interval_hours)
            
            config.save()
            return True
            
        except ProductMonitoringConfig.DoesNotExist:
            logger.warning(f"Attempted to update frequency for non-existent config (product {product_id})")
            return False


class MonitoringPrioritizer:
    """
    Service responsable de la priorisation des produits à monitorer
    """
    
    @classmethod
    def update_product_priorities(cls, batch_size=5000):
        """
        Met à jour les scores de priorité pour tous les produits
        en fonction de divers facteurs
        
        Args:
            batch_size: Nombre de produits à traiter par lot
        
        Returns:
            int: Nombre de produits mis à jour
        """
        now = timezone.now()
        configs = ProductMonitoringConfig.objects.filter(active=True)[:batch_size]
        
        updated_count = 0
        
        for config in configs:
            # Facteurs de priorité (valeurs entre 0 et 10)
            factors = {
                'volatility': cls._calculate_price_volatility(config.product, days=30),
                'popularity': cls._calculate_product_popularity(config.product),
                'price_level': cls._calculate_price_level_factor(config.product),
                'time_since_check': cls._calculate_time_factor(config.last_monitored, now),
                'manual_boost': config.manual_priority_boost
            }
            
            # Poids des facteurs (somme = 1.0)
            weights = {
                'volatility': 0.35,
                'popularity': 0.25,
                'price_level': 0.15,
                'time_since_check': 0.15,
                'manual_boost': 0.10
            }
            
            # Calculer le score de priorité pondéré (1-10)
            priority_score = sum(factors[k] * weights[k] for k in factors)
            
            # Normaliser entre 1 et 10
            priority_score = max(1.0, min(10.0, priority_score))
            
            # Inverser pour que 1 soit haute priorité et 10 basse priorité
            priority_score = 11 - priority_score
            
            # Mettre à jour la configuration
            config.priority_score = priority_score
            config.save(update_fields=['priority_score', 'updated_at'])
            
            updated_count += 1
        
        logger.info(f"Updated priorities for {updated_count} products")
        return updated_count
    
    @classmethod
    def _calculate_price_volatility(cls, product, days=30):
        """Calcule un score de volatilité de prix (0-10)"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Récupérer les points de prix récents
        price_points = PricePoint.objects.filter(
            product=product,
            timestamp__gte=cutoff_date
        ).order_by('timestamp')
        
        if price_points.count() < 2:
            return 5.0  # Valeur moyenne par défaut
        
        # Calculer le pourcentage de variation
        prices = list(price_points.values_list('price', flat=True))
        min_price = min(prices)
        max_price = max(prices)
        
        # Éviter division par zéro
        if min_price == 0:
            min_price = 0.01
        
        volatility_pct = (max_price - min_price) / min_price * 100
        
        # Mapper sur une échelle 0-10
        # 0% = 0, 50+% = 10
        volatility_score = min(10.0, volatility_pct / 5.0)
        
        return volatility_score
    
    @classmethod
    def _calculate_product_popularity(cls, product):
        """Calcule un score de popularité (0-10)"""
        # Simplification - dans un système réel, cela serait basé sur des vues, clics, etc.
        alerts_count = product.alerts.count() if hasattr(product, 'alerts') else 0
        
        # Mapper sur une échelle 0-10
        # 0 alertes = 1, 20+ alertes = 10
        popularity_score = min(10.0, 1.0 + alerts_count / 2.0)
        
        return popularity_score
    
    @classmethod
    def _calculate_price_level_factor(cls, product):
        """
        Calcule un facteur basé sur le niveau de prix (0-10)
        Les produits plus chers ont tendance à être plus prioritaires
        """
        current_price = product.current_price
        
        # Échelle logarithmique - 10€ = 1, 100€ = 5, 1000€+ = 10
        if current_price <= 0:
            return 1.0
        
        import math
        price_factor = 1.0 + 3.0 * math.log10(max(1.0, float(current_price)))
        return min(10.0, price_factor)
    
    @classmethod
    def _calculate_time_factor(cls, last_checked, now):
        """
        Calcule un facteur basé sur le temps écoulé depuis la dernière vérification (0-10)
        Plus le temps écoulé est long, plus la priorité est élevée
        """
        if last_checked is None:
            return 10.0  # Priorité maximale si jamais vérifié
        
        hours_since_check = (now - last_checked).total_seconds() / 3600
        
        # Mapper sur une échelle 0-10
        # 0h = 0, 48h+ = 10
        time_factor = min(10.0, hours_since_check / 4.8)
        
        return time_factor


class MonitoringResultsAnalyzer:
    """
    Service responsable de l'analyse des résultats de monitoring
    """
    
    @classmethod
    def analyze_result(cls, product, current_data):
        """
        Analyse les données actuelles par rapport aux données historiques
        et crée un résultat de monitoring
        
        Args:
            product: Objet produit
            current_data: Données actuelles extraites
            
        Returns:
            MonitoringResult: Résultat de l'analyse
        """
        # Récupérer le dernier résultat pour comparaison
        last_result = MonitoringResult.objects.filter(
            product=product
        ).order_by('-monitored_at').first()
        
        # Extraire les données actuelles
        current_price = current_data.get('price', 0)
        current_availability = current_data.get('in_stock', True)
        
        # Initialiser le résultat
        result = MonitoringResult(
            product=product,
            monitored_at=timezone.now(),
            current_price=current_price,
            currently_available=current_availability,
            is_deal=current_data.get('is_deal', False),
            extracted_data=current_data,
            raw_data=current_data.get('raw_data', {})
        )
        
        # Déterminer les changements si nous avons des données précédentes
        if last_result:
            result.previous_price = last_result.current_price
            result.previously_available = last_result.currently_available
            
            # Analyser les changements de prix
            if result.previous_price != result.current_price:
                result.price_changed = True
                result.price_change_amount = result.current_price - result.previous_price
                
                # Éviter division par zéro
                if result.previous_price > 0:
                    result.price_change_percentage = float(result.price_change_amount) / float(result.previous_price) * 100
            
            # Analyser les changements de disponibilité
            if result.previously_available != result.currently_available:
                result.availability_changed = True
        
        # Stocker les captures d'écran
        if 'screenshots' in current_data:
            result.screenshots = current_data['screenshots']
        
        # Vérifier si une alerte doit être déclenchée
        cls._check_alert_conditions(result, product)
        
        # Enregistrer le résultat
        result.save()
        
        # Mettre à jour la dernière date de monitoring
        config, _ = ProductMonitoringConfig.objects.get_or_create(
            product=product,
            defaults={'active': True}
        )
        config.last_monitored = result.monitored_at
        config.save(update_fields=['last_monitored', 'updated_at'])
        
        return result
    
    @classmethod
    def _check_alert_conditions(cls, result, product):
        """
        Vérifie si les conditions d'alerte sont remplies
        et configure le résultat en conséquence
        
        Args:
            result: Objet MonitoringResult à configurer
            product: Produit associé
        """
        # Récupérer la configuration de monitoring
        try:
            config = ProductMonitoringConfig.objects.get(product=product)
        except ProductMonitoringConfig.DoesNotExist:
            return
        
        # Changement de disponibilité
        if result.availability_changed:
            if not result.previously_available and result.currently_available:
                result.alert_triggered = True
                result.alert_type = 'back_in_stock'
                result.alert_message = "Ce produit est de nouveau disponible"
            elif result.previously_available and not result.currently_available:
                result.alert_triggered = True
                result.alert_type = 'out_of_stock'
                result.alert_message = "Ce produit n'est plus disponible"
        
        # Changement de prix
        if result.price_changed:
            # Calculer le seuil
            threshold_met = False
            threshold_message = ""
            
            # Vérifier le seuil absolu
            if config.price_threshold_absolute is not None and result.price_change_amount is not None:
                if abs(result.price_change_amount) >= config.price_threshold_absolute:
                    threshold_met = True
                    change = "baissé" if result.price_change_amount < 0 else "augmenté"
                    threshold_message = f"Le prix a {change} de {abs(result.price_change_amount)}€"
            
            # Vérifier le seuil en pourcentage
            if config.price_threshold_percentage is not None and result.price_change_percentage is not None:
                if abs(result.price_change_percentage) >= config.price_threshold_percentage:
                    threshold_met = True
                    change = "baissé" if result.price_change_amount < 0 else "augmenté"
                    threshold_message = f"Le prix a {change} de {abs(result.price_change_percentage):.1f}%"
            
            # Vérifier si on notifie pour tout changement
            if config.notify_on_any_change:
                threshold_met = True
                change = "baissé" if result.price_change_amount < 0 else "augmenté"
                if not threshold_message:
                    threshold_message = f"Le prix a {change} de {abs(result.price_change_amount)}€"
            
            # Déclencher l'alerte si nécessaire
            if threshold_met and result.price_change_amount < 0:  # Baisse de prix uniquement
                result.alert_triggered = True
                result.alert_type = 'price_drop'
                result.alert_message = threshold_message
            
            # Vérifier si c'est le prix le plus bas jamais vu
            if result.current_price == product.lowest_price:
                result.alert_triggered = True
                result.alert_type = 'lowest_price'
                result.alert_message = "C'est le prix le plus bas jamais vu pour ce produit"
        
        # Vérifier si c'est une promotion
        if result.is_deal and not result.alert_triggered:
            result.alert_triggered = True
            result.alert_type = 'deal'
            result.alert_message = "Ce produit est actuellement en promotion"


class MonitoringStatsService:
    """
    Service pour calculer et mettre à jour les statistiques de monitoring
    """
    
    @classmethod
    def update_daily_stats(cls, date=None):
        """
        Met à jour les statistiques de monitoring pour une date spécifique
        
        Args:
            date: Date pour laquelle calculer les stats (aujourd'hui par défaut)
        
        Returns:
            MonitoringStats: Objet stats mis à jour
        """
        if date is None:
            date = timezone.now().date()
        
        # Récupérer ou créer l'objet stats
        stats, created = MonitoringStats.objects.get_or_create(date=date)
        
        # Calculer la plage horaire
        start_dt = datetime.combine(date, datetime.min.time())
        end_dt = datetime.combine(date, datetime.max.time())
        
        # Requêtes pour les tâches de la journée
        tasks = MonitoringTask.objects.filter(
            created_at__date=date
        )
        
        results = MonitoringResult.objects.filter(
            monitored_at__date=date
        )
        
        # Statistiques des tâches
        stats.total_tasks = tasks.count()
        stats.completed_tasks = tasks.filter(status='completed').count()
        stats.failed_tasks = tasks.filter(status='failed').count()
        
        # Temps d'exécution (pour les tâches terminées avec données complètes)
        completed_tasks = tasks.filter(
            status='completed',
            started_at__isnull=False,
            completed_at__isnull=False
        )
        
        if completed_tasks.exists():
            # Calculer les temps d'exécution en secondes
            execution_times = []
            for task in completed_tasks:
                exec_time = (task.completed_at - task.started_at).total_seconds()
                execution_times.append(exec_time)
            
            if execution_times:
                stats.avg_execution_time = sum(execution_times) / len(execution_times)
                stats.max_execution_time = max(execution_times)
                stats.min_execution_time = min(execution_times)
        
        # Détection de changements
        stats.price_changes_detected = results.filter(price_changed=True).count()
        stats.availability_changes_detected = results.filter(availability_changed=True).count()
        stats.alerts_triggered = results.filter(alert_triggered=True).count()
        
        # Par priorité
        stats.high_priority_tasks = tasks.filter(priority__lte=3).count()
        stats.normal_priority_tasks = tasks.filter(priority__gt=3, priority__lte=7).count()
        stats.low_priority_tasks = tasks.filter(priority__gt=7).count()
        
        # Répartition par retailer
        retailer_counts = {}
        for task in tasks:
            retailer = task.product.retailer.name
            retailer_counts[retailer] = retailer_counts.get(retailer, 0) + 1
        
        stats.retailer_distribution = retailer_counts
        
        # Enregistrer les stats
        stats.save()
        
        return stats
