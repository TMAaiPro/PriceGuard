from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
import uuid

class AlertRule(models.Model):
    """Règle personnalisable pour le déclenchement d'alertes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='alert_rules')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='alert_rules', null=True, blank=True)
    
    # Type de règle
    RULE_TYPES = [
        ('price_drop', 'Baisse de prix'),
        ('price_target', 'Prix cible atteint'),
        ('price_drop_pct', 'Baisse de prix en pourcentage'),
        ('availability', 'Changement de disponibilité'),
        ('lowest_price', 'Prix le plus bas historique'),
        ('price_prediction', 'Prédiction de prix favorable'),
    ]
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    
    # Condition de déclenchement
    condition = JSONField(default=dict)
    
    # Canaux de notification
    channels = JSONField(default=dict)
    
    # Priorité de l'alerte (1-10)
    priority = models.IntegerField(default=5)
    
    # État
    is_active = models.BooleanField(default=True)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Règle d'alerte"
        verbose_name_plural = "Règles d'alerte"
        indexes = [
            models.Index(fields=['user', 'product', 'rule_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        product_name = self.product.title if self.product else "Tous les produits"
        return f"{self.get_rule_type_display()} pour {product_name}"
    
    def evaluate(self, event_data):
        """Évalue si l'événement déclenche cette règle"""
        if not self.is_active:
            return False
            
        # Vérifie le type d'événement
        if event_data.get('event_type') != self.rule_type:
            return False
            
        # Vérifie la correspondance produit
        if self.product and str(self.product.id) != str(event_data.get('product_id')):
            return False
        
        # Évalue la condition
        return self._evaluate_condition(self.condition, event_data)
    
    def _evaluate_condition(self, condition, event_data):
        """Évalue une condition de manière récursive"""
        operator = condition.get('operator')
        
        if operator == 'AND':
            return all(self._evaluate_condition(cond, event_data) for cond in condition.get('conditions', []))
        elif operator == 'OR':
            return any(self._evaluate_condition(cond, event_data) for cond in condition.get('conditions', []))
        elif operator == 'NOT':
            return not self._evaluate_condition(condition.get('condition', {}), event_data)
        elif operator in ['EQ', 'GT', 'LT', 'GTE', 'LTE']:
            field = condition.get('field')
            value = condition.get('value')
            
            if field not in event_data:
                return False
                
            field_value = event_data[field]
            
            if operator == 'EQ':
                return field_value == value
            elif operator == 'GT':
                return field_value > value
            elif operator == 'LT':
                return field_value < value
            elif operator == 'GTE':
                return field_value >= value
            elif operator == 'LTE':
                return field_value <= value
        
        return False


class NotificationDelivery(models.Model):
    """Historique de livraison des notifications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notification_deliveries')
    alert = models.ForeignKey('alerts.Alert', on_delete=models.SET_NULL, null=True, related_name='deliveries')
    
    # Canal utilisé
    channel = models.CharField(max_length=20)
    
    # Contenu
    message_id = models.CharField(max_length=255, blank=True)
    content = JSONField(default=dict)
    
    # Statut livraison
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sent', 'Envoyé'),
        ('delivered', 'Livré'),
        ('failed', 'Échec'),
        ('opened', 'Ouvert'),
        ('clicked', 'Cliqué'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    # Données d'erreur
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Livraison de notification"
        verbose_name_plural = "Livraisons de notifications"
        indexes = [
            models.Index(fields=['user', 'channel', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['alert']),
        ]
    
    def __str__(self):
        return f"Notification {self.channel} pour {self.user.email}"
    
    def mark_as_sent(self):
        """Marque la notification comme envoyée"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_delivered(self):
        """Marque la notification comme livrée"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_as_opened(self):
        """Marque la notification comme ouverte"""
        self.status = 'opened'
        self.opened_at = timezone.now()
        self.save(update_fields=['status', 'opened_at'])
    
    def mark_as_clicked(self):
        """Marque la notification comme cliquée"""
        self.status = 'clicked'
        self.clicked_at = timezone.now()
        self.save(update_fields=['status', 'clicked_at'])
    
    def mark_as_failed(self, error_message):
        """Marque la notification comme échouée"""
        self.status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])


class NotificationBatch(models.Model):
    """Batch de notifications à envoyer"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notification_batches')
    
    # Type de batch
    BATCH_TYPES = [
        ('immediate', 'Immédiat'),
        ('hourly', 'Agrégation horaire'),
        ('daily', 'Résumé quotidien'),
    ]
    batch_type = models.CharField(max_length=20, choices=BATCH_TYPES)
    
    # Canal
    channel = models.CharField(max_length=20)
    
    # Statut
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours'),
        ('sent', 'Envoyé'),
        ('failed', 'Échec'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField()
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Données
    items_count = models.IntegerField(default=0)
    processed_count = models.IntegerField(default=0)
    
    # Données d'erreur
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Batch de notifications"
        verbose_name_plural = "Batchs de notifications"
        indexes = [
            models.Index(fields=['user', 'channel', '-created_at']),
            models.Index(fields=['status', 'scheduled_for']),
        ]
    
    def __str__(self):
        return f"Batch {self.batch_type} via {self.channel} pour {self.user.email}"


class NotificationBatchItem(models.Model):
    """Élément dans un batch de notifications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey('NotificationBatch', on_delete=models.CASCADE, related_name='items')
    alert = models.ForeignKey('alerts.Alert', on_delete=models.SET_NULL, null=True, related_name='batch_items')
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Élément de batch"
        verbose_name_plural = "Éléments de batch"
        indexes = [
            models.Index(fields=['batch']),
            models.Index(fields=['alert']),
        ]
    
    def __str__(self):
        return f"Item pour {self.batch}"


# Modèles pour le tracking d'engagement
class InAppNotification(models.Model):
    """Notifications affichées dans l'application"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='in_app_notifications')
    alert = models.ForeignKey('alerts.Alert', on_delete=models.SET_NULL, null=True, related_name='in_app_notifications')
    
    # Contenu
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = JSONField(default=dict)
    
    # Statut
    is_read = models.BooleanField(default=False)
    is_clicked = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    # Expiration
    expires_at = models.DateTimeField()
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification in-app"
        verbose_name_plural = "Notifications in-app"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Notification in-app pour {self.user.email}: {self.title}"
    
    def mark_as_read(self):
        """Marquer la notification comme lue"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_clicked(self):
        """Marquer la notification comme cliquée"""
        self.is_clicked = True
        self.clicked_at = timezone.now()
        self.save(update_fields=['is_clicked', 'clicked_at'])
        
        # Marquer comme lue également si ce n'est pas déjà fait
        if not self.is_read:
            self.mark_as_read()


class NotificationEngagement(models.Model):
    """Tracking de l'engagement utilisateur avec les notifications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notification_engagements')
    delivery = models.ForeignKey('NotificationDelivery', on_delete=models.CASCADE, related_name='engagements')
    
    # Type d'événement
    EVENT_TYPES = [
        ('delivered', 'Livrée'),
        ('opened', 'Ouverte'),
        ('clicked', 'Cliquée'),
        ('action_taken', 'Action effectuée'),
        ('dismissed', 'Ignorée'),
    ]
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    
    # Données d'événement
    device_type = models.CharField(max_length=50, blank=True)
    platform = models.CharField(max_length=50, blank=True)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Métadonnées
    timestamp = models.DateTimeField(default=timezone.now)
    data = JSONField(default=dict)
    
    class Meta:
        verbose_name = "Engagement notification"
        verbose_name_plural = "Engagements notifications"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['delivery', 'event_type']),
        ]
    
    def __str__(self):
        return f"Engagement {self.event_type} pour {self.user.email}"


class UserEngagementMetrics(models.Model):
    """Métriques d'engagement agrégées par utilisateur"""
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, primary_key=True, related_name='engagement_metrics')
    
    # Compteurs globaux
    total_notifications = models.IntegerField(default=0)
    opened_count = models.IntegerField(default=0)
    clicked_count = models.IntegerField(default=0)
    action_count = models.IntegerField(default=0)
    
    # Taux calculés
    open_rate = models.FloatField(default=0)  # % d'ouverture
    click_rate = models.FloatField(default=0)  # % de clic
    action_rate = models.FloatField(default=0)  # % d'action
    
    # Par canal
    email_metrics = JSONField(default=dict)
    push_metrics = JSONField(default=dict)
    in_app_metrics = JSONField(default=dict)
    
    # Préférences optimales déduites
    optimal_channels = JSONField(default=dict)
    optimal_timing = JSONField(default=dict)
    optimal_frequency = models.CharField(max_length=20, blank=True)
    
    # Métadonnées
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Métriques d'engagement utilisateur"
        verbose_name_plural = "Métriques d'engagement utilisateur"
    
    def __str__(self):
        return f"Métriques d'engagement pour {self.user.email}"
    
    def update_metrics(self):
        """Met à jour les métriques d'engagement"""
        from notifications.services import EngagementService
        
        EngagementService.update_user_metrics(self.user_id)
