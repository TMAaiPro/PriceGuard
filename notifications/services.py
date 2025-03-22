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
    
    @classmethod
    def evaluate_event(cls, event_data):
        """
        Évalue un événement par rapport à toutes les règles d'alerte
        
        Args:
            event_data: Données de l'événement
        
        Returns:
            List[Alert]: Liste des alertes déclenchées
        """
        logger.info(f"Évaluation événement: {event_data['event_type']} pour produit {event_data.get('product_id')}")
        
        # Récupération des règles potentiellement déclenchables
        rules = AlertRule.objects.filter(
            is_active=True,
            rule_type=event_data['event_type']
        ).select_related('user', 'product')
        
        # Filtrer les règles par produit si un ID produit est spécifié
        product_id = event_data.get('product_id')
        if product_id:
            from django.db import models
            rules = rules.filter(
                # Soit règle globale sans produit spécifié
                # Soit règle spécifique au produit concerné
                models.Q(product__isnull=True) | models.Q(product_id=product_id)
            )
        
        triggered_alerts = []
        
        # Évaluer chaque règle
        for rule in rules:
            if rule.evaluate(event_data):
                # Si la règle est déclenchée, créer une alerte
                alert = cls._create_alert_from_rule(rule, event_data)
                triggered_alerts.append(alert)
                
                # Planifier la notification
                cls._schedule_notifications(rule, alert, event_data)
        
        logger.info(f"Évaluation terminée: {len(triggered_alerts)} alertes déclenchées")
        return triggered_alerts
    
    @classmethod
    def _create_alert_from_rule(cls, rule, event_data):
        """
        Crée une alerte à partir d'une règle déclenchée
        
        Args:
            rule: Règle d'alerte déclenchée
            event_data: Données de l'événement
            
        Returns:
            Alert: Objet alerte créé
        """
        # Déterminer le type d'alerte et les détails
        product_id = event_data.get('product_id')
        product = rule.product or Product.objects.get(id=product_id)
        
        alert_type = event_data['event_type']
        if alert_type == 'price_drop' and event_data.get('is_lowest_price'):
            alert_type = 'lowest_price'
        elif alert_type == 'price_prediction' and event_data.get('is_price_drop_predicted'):
            alert_type = 'price_drop_prediction'
        
        # Préparer les données d'alerte
        alert_data = {
            'user': rule.user,
            'product': product,
            'alert_type': alert_type,
            'message': cls._generate_alert_message(rule, event_data),
        }
        
        # Ajouter les informations de prix si disponibles
        if 'previous_price' in event_data and 'current_price' in event_data:
            alert_data.update({
                'previous_price': event_data['previous_price'],
                'current_price': event_data['current_price'],
                'price_difference': event_data['price_diff'],
                'price_difference_percentage': event_data['price_diff_pct'],
            })
            
        # Créer l'alerte
        with transaction.atomic():
            alert = Alert.objects.create(**alert_data)
            
            # Si l'événement provient d'un point d'historique prix, l'associer
            if 'price_history_id' in event_data:
                try:
                    price_history = PriceHistory.objects.get(id=event_data['price_history_id'])
                    alert.price_history = price_history
                    alert.save(update_fields=['price_history'])
                except PriceHistory.DoesNotExist:
                    pass
        
        return alert
    
    @classmethod
    def _generate_alert_message(cls, rule, event_data):
        """
        Génère le message d'alerte en fonction de la règle et de l'événement
        
        Args:
            rule: Règle d'alerte
            event_data: Données de l'événement
            
        Returns:
            str: Message d'alerte formaté
        """
        product_title = event_data.get('product_title', 'Produit')
        
        if event_data['event_type'] == 'price_drop':
            previous_price = event_data.get('previous_price', 0)
            current_price = event_data.get('current_price', 0)
            diff_pct = event_data.get('price_diff_pct', 0)
            
            if event_data.get('is_lowest_price'):
                return f"🔥 Prix le plus bas jamais vu pour {product_title} ! Maintenant à {current_price:.2f}€ (baisse de {abs(diff_pct):.1f}%)"
            else:
                return f"📉 Le prix de {product_title} a baissé ! Maintenant à {current_price:.2f}€ au lieu de {previous_price:.2f}€ (baisse de {abs(diff_pct):.1f}%)"
        
        elif event_data['event_type'] == 'price_increase':
            previous_price = event_data.get('previous_price', 0)
            current_price = event_data.get('current_price', 0)
            diff_pct = event_data.get('price_diff_pct', 0)
            
            return f"📈 Le prix de {product_title} a augmenté à {current_price:.2f}€ (était {previous_price:.2f}€, hausse de {diff_pct:.1f}%)"
        
        elif event_data['event_type'] == 'availability':
            if event_data.get('became_available'):
                return f"✅ {product_title} est maintenant disponible !"
            elif event_data.get('became_unavailable'):
                return f"❌ {product_title} n'est plus disponible."
        
        elif event_data['event_type'] == 'price_prediction':
            current_price = event_data.get('current_price', 0)
            predicted_price = event_data.get('predicted_price', 0)
            prediction_date = event_data.get('prediction_date', '')
            confidence = event_data.get('confidence', 0) * 100
            
            if event_data.get('is_price_drop_predicted'):
                return f"🔮 Prédiction: Le prix de {product_title} devrait baisser à {predicted_price:.2f}€ (actuellement {current_price:.2f}€) d'ici le {prediction_date} (confiance: {confidence:.0f}%)"
            else:
                return f"🔮 Prédiction: Le prix de {product_title} devrait augmenter à {predicted_price:.2f}€ (actuellement {current_price:.2f}€) d'ici le {prediction_date} (confiance: {confidence:.0f}%)"
        
        # Message par défaut
        return f"Alerte pour {product_title}"
    
    @classmethod
    def _schedule_notifications(cls, rule, alert, event_data):
        """
        Planifie les notifications pour une alerte
        
        Args:
            rule: Règle d'alerte
            alert: Alerte déclenchée
            event_data: Données de l'événement
        """
        from .tasks import schedule_notification_delivery
        
        # Récupérer les canaux configurés
        channels = rule.channels or {
            'email': True,
            'push': rule.user.push_notifications,
            'in_app': True,
        }
        
        # Calculer la priorité de notification
        priority = rule.priority
        
        # Ajuster la priorité selon le type d'événement
        if event_data['event_type'] == 'price_drop':
            # Augmenter la priorité pour grandes baisses de prix
            diff_pct = abs(event_data.get('price_diff_pct', 0))
            if diff_pct > 20:
                priority = min(10, priority + 2)
            elif diff_pct > 10:
                priority = min(10, priority + 1)
            
            # Priorité maximale pour le prix le plus bas historique
            if event_data.get('is_lowest_price'):
                priority = 10
                
        # Planifier les notifications pour chaque canal activé
        for channel, enabled in channels.items():
            if not enabled:
                continue
                
            # Vérifier les préférences utilisateur
            if channel == 'email' and not rule.user.email_notifications:
                continue
            elif channel == 'push' and not rule.user.push_notifications:
                continue
                
            # Déterminer la stratégie de batching
            from django.conf import settings
            batching_config = settings.NOTIFICATION_BATCHING.get(channel, {})
            user_preference = rule.user.preferences.notification_frequency
            
            # Convertir la préférence utilisateur en configuration de batching
            if user_preference == 'immediate':
                batch_type = 'immediate'
            elif user_preference == 'hourly':
                batch_type = 'hourly'
            elif user_preference == 'daily':
                batch_type = 'daily'
            else:
                batch_type = batching_config.get('default', 'immediate')
            
            # Ajuster le batching selon la priorité
            if priority >= 9:  # Priorité très haute
                batch_type = 'immediate'  # Forcer l'envoi immédiat pour alertes critiques
            
            # Planifier la livraison
            schedule_notification_delivery.delay(
                user_id=str(rule.user.id),
                alert_id=str(alert.id),
                channel=channel,
                batch_type=batch_type,
                priority=priority
            )
