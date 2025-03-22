import logging
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import json

from .models import AlertRule, NotificationDelivery, NotificationBatch, NotificationBatchItem, InAppNotification
from alerts.models import Alert
from products.models import Product, PriceHistory

logger = logging.getLogger(__name__)

class AlertRuleService:
    """Service pour l'évaluation des règles d'alerte"""
    
    @classmethod
    def process_price_change_event(cls, product_id, previous_price, current_price, source_info=None):
        """
        Traite un événement de changement de prix
        
        Args:
            product_id: ID du produit
            previous_price: Prix précédent
            current_price: Prix actuel
            source_info: Information sur la source de l'événement
        """
        product = Product.objects.get(id=product_id)
        
        # Calcul des métriques d'événement
        price_diff = current_price - previous_price
        price_diff_pct = (price_diff / previous_price) * 100 if previous_price > 0 else 0
        is_price_drop = price_diff < 0
        is_lowest_price = current_price <= product.lowest_price
        
        # Préparation des données d'événement
        event_data = {
            'event_type': 'price_drop' if is_price_drop else 'price_increase',
            'product_id': str(product_id),
            'previous_price': float(previous_price),
            'current_price': float(current_price),
            'price_diff': float(price_diff),
            'price_diff_pct': float(price_diff_pct),
            'is_lowest_price': is_lowest_price,
            'product_title': product.title,
            'timestamp': timezone.now().isoformat(),
            'source': source_info or 'system',
        }
        
        # Envoi de l'événement au moteur d'évaluation
        return cls.evaluate_event(event_data)
    
    @classmethod
    def process_availability_change_event(cls, product_id, previous_availability, current_availability, source_info=None):
        """
        Traite un événement de changement de disponibilité
        
        Args:
            product_id: ID du produit
            previous_availability: Disponibilité précédente
            current_availability: Disponibilité actuelle
            source_info: Information sur la source de l'événement
        """
        product = Product.objects.get(id=product_id)
        
        # Préparation des données d'événement
        event_data = {
            'event_type': 'availability',
            'product_id': str(product_id),
            'previous_availability': previous_availability,
            'current_availability': current_availability,
            'became_available': not previous_availability and current_availability,
            'became_unavailable': previous_availability and not current_availability,
            'product_title': product.title,
            'timestamp': timezone.now().isoformat(),
            'source': source_info or 'system',
        }
        
        # Envoi de l'événement au moteur d'évaluation
        return cls.evaluate_event(event_data)
    
    @classmethod
    def process_price_prediction_event(cls, product_id, predicted_price, current_price, confidence, prediction_date, source_info=None):
        """
        Traite un événement de prédiction de prix
        
        Args:
            product_id: ID du produit
            predicted_price: Prix prédit
            current_price: Prix actuel
            confidence: Confiance de la prédiction (0-1)
            prediction_date: Date pour laquelle la prédiction est faite
            source_info: Information sur la source de l'événement
        """
        product = Product.objects.get(id=product_id)
        
        # Calcul des métriques d'événement
        price_diff = predicted_price - current_price
        price_diff_pct = (price_diff / current_price) * 100 if current_price > 0 else 0
        is_price_drop_predicted = price_diff < 0
        
        # Préparation des données d'événement
        event_data = {
            'event_type': 'price_prediction',
            'product_id': str(product_id),
            'current_price': float(current_price),
            'predicted_price': float(predicted_price),
            'price_diff': float(price_diff),
            'price_diff_pct': float(price_diff_pct),
            'is_price_drop_predicted': is_price_drop_predicted,
            'confidence': float(confidence),
            'prediction_date': prediction_date.isoformat(),
            'product_title': product.title,
            'timestamp': timezone.now().isoformat(),
            'source': source_info or 'system',
        }
        
        # Envoi de l'événement au moteur d'évaluation
        return cls.evaluate_event(event_data)
