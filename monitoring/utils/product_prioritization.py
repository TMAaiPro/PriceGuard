import logging
import math
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, StdDev, Min, Max, Count

from products.models import Product, PricePoint
from ..models import ProductMonitoringConfig, MonitoringResult

logger = logging.getLogger(__name__)

class ProductPrioritizer:
    """
    Classe utilitaire pour calculer et appliquer des priorités 
    aux produits pour le monitoring
    """
    
    FACTORS = {
        'volatility': 0.35,       # Volatilité des prix
        'popularity': 0.25,       # Popularité auprès des utilisateurs
        'price_level': 0.15,      # Niveau de prix (plus cher = plus prioritaire)
        'time_since_check': 0.15, # Temps écoulé depuis la dernière vérification
        'manual_boost': 0.10      # Boost manuel configuré par les administrateurs
    }
    
    @classmethod
    def calculate_priority_score(cls, product, config=None):
        """
        Calcule un score de priorité pour un produit en fonction
        de différents facteurs
        
        Args:
            product: Objet produit
            config: Configuration de monitoring optionnelle
            
        Returns:
            float: Score de priorité (1-10, où 1 est la plus haute priorité)
        """
        if config is None:
            try:
                config = ProductMonitoringConfig.objects.get(product=product)
            except ProductMonitoringConfig.DoesNotExist:
                logger.warning(f"Pas de config de monitoring pour le produit {product.id}")
                return 5.0  # Priorité moyenne par défaut
        
        now = timezone.now()
        
        # Calculer les facteurs
        factors = {
            'volatility': cls._calculate_price_volatility(product),
            'popularity': cls._calculate_product_popularity(product),
            'price_level': cls._calculate_price_level_factor(product),
            'time_since_check': cls._calculate_time_factor(config.last_monitored, now),
            'manual_boost': config.manual_priority_boost
        }
        
        # Calculer le score pondéré
        weighted_score = sum(factors[k] * cls.FACTORS[k] for k in factors)
        
        # Normaliser entre 1 et 10
        normalized_score = max(1.0, min(10.0, weighted_score))
        
        # Inverser pour que 1 soit haute priorité et 10 basse priorité
        inverted_score = 11 - normalized_score
        
        return inverted_score
    
    @classmethod
    def _calculate_price_volatility(cls, product, days=30):
        """
        Calcule un score de volatilité de prix (0-10)
        Plus les prix ont varié récemment, plus le score est élevé
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Récupérer les points de prix récents
        price_points = PricePoint.objects.filter(
            product=product,
            timestamp__gte=cutoff_date
        ).order_by('timestamp')
        
        count = price_points.count()
        
        if count < 2:
            return 5.0  # Valeur moyenne par défaut
        
        # Calculer le pourcentage de variation
        prices = list(price_points.values_list('price', flat=True))
        min_price = min(prices)
        max_price = max(prices)
        
        # Éviter division par zéro
        if min_price == 0:
            min_price = 0.01
        
        volatility_pct = (max_price - min_price) / min_price * 100
        
        # Calculer aussi la fréquence des changements
        changes = 0
        prev_price = None
        for price in prices:
            if prev_price is not None and price != prev_price:
                changes += 1
            prev_price = price
        
        change_ratio = changes / (count - 1) if count > 1 else 0
        
        # Combiner les deux facteurs (variation et fréquence)
        # 0% = 0, 50+% = 10 pour la variation
        volatility_score = min(10.0, volatility_pct / 5.0)
        
        # 0 changements = 0, 100% de changements = 10
        frequency_score = change_ratio * 10.0
        
        # Pondérer 70% variation, 30% fréquence
        combined_score = 0.7 * volatility_score + 0.3 * frequency_score
        
        return combined_score
    
    @classmethod
    def _calculate_product_popularity(cls, product):
        """
        Calcule un score de popularité (0-10)
        Plus le produit est populaire, plus son score est élevé
        """
        # Nombre d'alertes configurées pour ce produit
        alerts_count = product.alerts.count() if hasattr(product, 'alerts') else 0
        
        # Nombre de vues du produit (si disponible)
        views_count = getattr(product, 'view_count', 0)
        
        # Combiner les deux facteurs
        # 0 alertes = 0, 20+ alertes = 10
        alerts_score = min(10.0, alerts_count / 2.0)
        
        # 0 vues = 0, 1000+ vues = 10
        views_score = min(10.0, views_count / 100.0)
        
        # Pondérer 60% alertes, 40% vues
        combined_score = 0.6 * alerts_score + 0.4 * views_score
        
        # Si pas de données de vues, utiliser uniquement les alertes
        if views_count == 0:
            combined_score = alerts_score
        
        # Si pas d'alertes ni de vues, utiliser un score de base de 1.0
        if alerts_count == 0 and views_count == 0:
            combined_score = 1.0
        
        return combined_score
    
    @classmethod
    def _calculate_price_level_factor(cls, product):
        """
        Calcule un facteur basé sur le niveau de prix (0-10)
        Les produits plus chers ont tendance à être plus prioritaires
        """
        current_price = float(product.current_price)
        
        # Échelle logarithmique - 10€ = 1, 100€ = 5, 1000€+ = 10
        if current_price <= 0:
            return 1.0
        
        price_factor = 1.0 + 3.0 * math.log10(max(1.0, current_price))
        return min(10.0, price_factor)
    
    @classmethod
    def _calculate_time_factor(cls, last_checked, now):
        """
        Calcule un facteur basé sur le temps écoulé (0-10)
        Plus le temps écoulé est long, plus la priorité est élevée
        """
        if last_checked is None:
            return 10.0  # Priorité maximale si jamais vérifié
        
        hours_since_check = (now - last_checked).total_seconds() / 3600
        
        # Mapper sur une échelle 0-10
        # 0h = 0, 48h+ = 10
        time_factor = min(10.0, hours_since_check / 4.8)
        
        return time_factor
