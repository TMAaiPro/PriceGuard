import logging
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import json

from .models import AlertRule, NotificationDelivery, NotificationBatch, NotificationBatchItem, InAppNotification, NotificationEngagement, UserEngagementMetrics
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


class EngagementService:
    """Service pour le tracking et l'analyse de l'engagement utilisateur"""
    
    @classmethod
    def track_engagement(cls, delivery_id, event_type, request=None, data=None):
        """
        Enregistre un événement d'engagement
        
        Args:
            delivery_id: ID de la livraison
            event_type: Type d'événement
            request: Objet requête HTTP (optionnel)
            data: Données supplémentaires (optionnel)
            
        Returns:
            NotificationEngagement: Objet engagement créé
        """
        try:
            delivery = NotificationDelivery.objects.get(id=delivery_id)
            
            # Préparer les données de l'événement
            event_data = data or {}
            
            # Extraire les informations de la requête si fournie
            device_type = ''
            platform = ''
            client_ip = None
            user_agent = ''
            
            if request:
                client_ip = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                # Détecter le type d'appareil et la plateforme
                if 'mobile' in user_agent.lower():
                    device_type = 'mobile'
                elif 'tablet' in user_agent.lower():
                    device_type = 'tablet'
                else:
                    device_type = 'desktop'
                
                if 'android' in user_agent.lower():
                    platform = 'android'
                elif 'iphone' in user_agent.lower() or 'ipad' in user_agent.lower():
                    platform = 'ios'
                elif 'windows' in user_agent.lower():
                    platform = 'windows'
                elif 'macintosh' in user_agent.lower() or 'mac os' in user_agent.lower():
                    platform = 'macos'
                elif 'linux' in user_agent.lower():
                    platform = 'linux'
            
            # Créer l'engagement
            engagement = NotificationEngagement.objects.create(
                user=delivery.user,
                delivery=delivery,
                event_type=event_type,
                device_type=device_type,
                platform=platform,
                client_ip=client_ip,
                user_agent=user_agent,
                data=event_data
            )
            
            # Mettre à jour le statut de la livraison
            if event_type == 'delivered':
                delivery.mark_as_delivered()
            elif event_type == 'opened':
                delivery.mark_as_opened()
            elif event_type == 'clicked':
                delivery.mark_as_clicked()
            
            # Mettre à jour les métriques d'engagement de l'utilisateur
            cls.update_user_metrics(delivery.user.id)
            
            return engagement
            
        except NotificationDelivery.DoesNotExist:
            logger.error(f"Livraison introuvable: {delivery_id}")
            return None
        except Exception as e:
            logger.exception(f"Erreur lors du tracking d'engagement: {str(e)}")
            return None
    
    @classmethod
    def update_user_metrics(cls, user_id):
        """
        Met à jour les métriques d'engagement pour un utilisateur
        
        Args:
            user_id: ID de l'utilisateur
        """
        from django.contrib.auth import get_user_model
        from django.db.models import Count, Case, When, IntegerField, F, FloatField, Avg
        from django.db.models.functions import TruncHour, TruncDay
        
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
            
            # Récupérer ou créer les métriques d'engagement
            metrics, created = UserEngagementMetrics.objects.get_or_create(user=user)
            
            # Calculer les compteurs globaux
            total_notifications = NotificationDelivery.objects.filter(
                user=user,
                status__in=['sent', 'delivered', 'opened', 'clicked']
            ).count()
            
            opened_count = NotificationDelivery.objects.filter(
                user=user,
                status__in=['opened', 'clicked']
            ).count()
            
            clicked_count = NotificationDelivery.objects.filter(
                user=user,
                status='clicked'
            ).count()
            
            # Compter les actions effectuées suite à une notification
            action_count = NotificationEngagement.objects.filter(
                user=user,
                event_type='action_taken'
            ).count()
            
            # Calculer les taux
            open_rate = (opened_count / total_notifications * 100) if total_notifications > 0 else 0
            click_rate = (clicked_count / total_notifications * 100) if total_notifications > 0 else 0
            action_rate = (action_count / total_notifications * 100) if total_notifications > 0 else 0
            
            # Analyser par canal
            email_metrics = cls._calculate_channel_metrics(user, 'email')
            push_metrics = cls._calculate_channel_metrics(user, 'push')
            in_app_metrics = cls._calculate_channel_metrics(user, 'in_app')
            
            # Déduire les canaux optimaux
            channels = ['email', 'push', 'in_app']
            engagement_rates = [
                (email_metrics.get('open_rate', 0), 'email'),
                (push_metrics.get('open_rate', 0), 'push'),
                (in_app_metrics.get('open_rate', 0), 'in_app')
            ]
            
            # Trier par taux d'engagement
            sorted_channels = sorted(engagement_rates, reverse=True)
            optimal_channels = {
                'primary': sorted_channels[0][1] if sorted_channels else 'email',
                'secondary': sorted_channels[1][1] if len(sorted_channels) > 1 else 'push',
                'rates': {channel: rate for rate, channel in engagement_rates}
            }
            
            # Analyser le timing optimal
            optimal_timing = cls._calculate_optimal_timing(user)
            
            # Déduire la fréquence optimale
            user_batches = NotificationBatch.objects.filter(
                user=user,
                status='sent'
            ).values('batch_type').annotate(
                count=Count('id'),
                open_count=Count(Case(
                    When(items__alert__deliveries__status__in=['opened', 'clicked'], then=1),
                    output_field=IntegerField()
                ))
            )
            
            batch_engagement = {}
            for batch in user_batches:
                batch_type = batch['batch_type']
                open_rate = (batch['open_count'] / batch['count'] * 100) if batch['count'] > 0 else 0
                batch_engagement[batch_type] = open_rate
            
            # Choisir le type de batch avec le meilleur taux d'engagement
            optimal_frequency = max(batch_engagement.items(), key=lambda x: x[1])[0] if batch_engagement else 'daily'
            
            # Mettre à jour les métriques
            metrics.total_notifications = total_notifications
            metrics.opened_count = opened_count
            metrics.clicked_count = clicked_count
            metrics.action_count = action_count
            metrics.open_rate = open_rate
            metrics.click_rate = click_rate
            metrics.action_rate = action_rate
            metrics.email_metrics = email_metrics
            metrics.push_metrics = push_metrics
            metrics.in_app_metrics = in_app_metrics
            metrics.optimal_channels = optimal_channels
            metrics.optimal_timing = optimal_timing
            metrics.optimal_frequency = optimal_frequency
            
            metrics.save()
            
            return metrics
            
        except User.DoesNotExist:
            logger.error(f"Utilisateur introuvable: {user_id}")
            return None
        except Exception as e:
            logger.exception(f"Erreur lors de la mise à jour des métriques d'engagement: {str(e)}")
            return None
    
    @classmethod
    def _calculate_channel_metrics(cls, user, channel):
        """
        Calcule les métriques d'engagement pour un canal spécifique
        
        Args:
            user: Utilisateur
            channel: Canal de notification
            
        Returns:
            dict: Métriques du canal
        """
        # Récupérer toutes les notifications pour ce canal
        notifications = NotificationDelivery.objects.filter(
            user=user,
            channel=channel,
            status__in=['sent', 'delivered', 'opened', 'clicked']
        )
        
        total = notifications.count()
        
        if total == 0:
            return {
                'total': 0,
                'open_rate': 0,
                'click_rate': 0,
                'action_rate': 0
            }
        
        # Compter les différents statuts
        opened = notifications.filter(status__in=['opened', 'clicked']).count()
        clicked = notifications.filter(status='clicked').count()
        
        # Compter les actions effectuées
        actions = NotificationEngagement.objects.filter(
            user=user,
            delivery__channel=channel,
            event_type='action_taken'
        ).count()
        
        # Calculer les taux
        open_rate = (opened / total * 100) if total > 0 else 0
        click_rate = (clicked / total * 100) if total > 0 else 0
        action_rate = (actions / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'opened': opened,
            'clicked': clicked,
            'actions': actions,
            'open_rate': open_rate,
            'click_rate': click_rate,
            'action_rate': action_rate
        }
    
    @classmethod
    def _calculate_optimal_timing(cls, user):
        """
        Analyse les heures d'ouverture et de clic pour déterminer le timing optimal
        
        Args:
            user: Utilisateur
            
        Returns:
            dict: Timing optimal par jour et par heure
        """
        from django.db.models import Count, F, Max
        from django.db.models.functions import TruncHour, TruncDay, Extract
        
        # Analyses par heure de la journée
        hour_engagement = NotificationEngagement.objects.filter(
            user=user,
            event_type__in=['opened', 'clicked']
        ).annotate(
            hour=Extract('timestamp', 'hour')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Analyses par jour de la semaine
        day_engagement = NotificationEngagement.objects.filter(
            user=user,
            event_type__in=['opened', 'clicked']
        ).annotate(
            day=Extract('timestamp', 'dow')  # 0 (Sunday) to 6 (Saturday)
        ).values('day').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Trouver l'heure et le jour les plus actifs
        best_hour = hour_engagement.first()
        best_day = day_engagement.first()
        
        # Convertir en format lisible
        day_names = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        
        optimal_timing = {
            'best_hour': best_hour['hour'] if best_hour else 9,  # Par défaut 9h
            'best_day': day_names[best_day['day']] if best_day else 'monday',  # Par défaut lundi
            'hourly_data': {hour['hour']: hour['count'] for hour in hour_engagement},
            'daily_data': {day_names[day['day']]: day['count'] for day in day_engagement}
        }
        
        return optimal_timing
