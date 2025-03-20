from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import JSONField
from django.conf import settings
import uuid

class MonitoringTask(models.Model):
    """
    Modèle pour les tâches de monitoring programmées
    """
    # Identifiants
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='monitoring_tasks')
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                             null=True, blank=True, related_name='created_monitoring_tasks')
    
    # Paramètres de scheduling
    scheduled_time = models.DateTimeField()
    priority = models.IntegerField(default=5)  # 1 (haute) - 10 (basse)
    
    # Statut
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('scheduled', 'Programmée'),
        ('running', 'En cours'),
        ('completed', 'Terminée'),
        ('failed', 'Échouée'),
        ('cancelled', 'Annulée'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Résultats
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    result_data = JSONField(default=dict, blank=True)
    
    # Retry information
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    class Meta:
        ordering = ['priority', 'scheduled_time']
        indexes = [
            models.Index(fields=['status', 'scheduled_time']),
            models.Index(fields=['product', 'status']),
            models.Index(fields=['priority', 'scheduled_time']),
        ]
    
    def __str__(self):
        return f"Task {self.id} - {self.product} ({self.status})"
    
    def mark_as_running(self):
        """Marquer la tâche comme en cours d'exécution"""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def mark_as_completed(self, result_data=None):
        """Marquer la tâche comme terminée avec succès"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if result_data:
            self.result_data = result_data
        self.save(update_fields=['status', 'completed_at', 'result_data', 'updated_at'])
    
    def mark_as_failed(self, error_message):
        """Marquer la tâche comme échouée"""
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.error_message = error_message
            self.save(update_fields=['retry_count', 'error_message', 'updated_at'])
            return False  # Indique qu'un retry est possible
        else:
            self.status = 'failed'
            self.completed_at = timezone.now()
            self.error_message = error_message
            self.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])
            return True  # Indique que c'est un échec définitif


class ProductMonitoringConfig(models.Model):
    """
    Configuration de monitoring spécifique pour un produit
    """
    product = models.OneToOneField('products.Product', on_delete=models.CASCADE, 
                                 related_name='monitoring_config')
    
    # Fréquence de monitoring
    FREQUENCY_CHOICES = (
        ('high', 'Haute (toutes les 4 heures)'),
        ('normal', 'Normale (toutes les 12 heures)'),
        ('low', 'Basse (toutes les 24 heures)'),
        ('custom', 'Personnalisée'),
    )
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='normal')
    custom_frequency_hours = models.PositiveIntegerField(null=True, blank=True, 
                                                      help_text="Nombre d'heures entre chaque vérification")
    
    # Priorité
    priority_score = models.FloatField(default=5.0)  # Score calculé pour priorisation
    manual_priority_boost = models.FloatField(default=0.0)  # Boost manuel de priorité
    
    # Paramètres spécifiques
    take_screenshot = models.BooleanField(default=True)
    notify_on_any_change = models.BooleanField(default=False)
    price_threshold_percentage = models.FloatField(null=True, blank=True)
    price_threshold_absolute = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Planification
    active = models.BooleanField(default=True)
    last_monitored = models.DateTimeField(null=True, blank=True)
    next_scheduled = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['active', 'next_scheduled']),
            models.Index(fields=['frequency']),
            models.Index(fields=['priority_score']),
        ]
    
    def __str__(self):
        return f"Monitoring config for {self.product} ({self.frequency})"
    
    def get_monitoring_interval(self):
        """Obtenir l'intervalle de monitoring en heures"""
        if self.frequency == 'high':
            return 4
        elif self.frequency == 'normal':
            return 12
        elif self.frequency == 'low':
            return 24
        elif self.frequency == 'custom' and self.custom_frequency_hours:
            return self.custom_frequency_hours
        else:
            return 12  # Valeur par défaut


class MonitoringResult(models.Model):
    """
    Résultat d'une tâche de monitoring
    """
    # Identifiants
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='monitoring_results')
    task = models.ForeignKey(MonitoringTask, on_delete=models.SET_NULL, null=True, related_name='results')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    monitored_at = models.DateTimeField()
    
    # Résultats
    previous_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_changed = models.BooleanField(default=False)
    price_change_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_change_percentage = models.FloatField(null=True, blank=True)
    
    # Disponibilité
    previously_available = models.BooleanField(null=True)
    currently_available = models.BooleanField()
    availability_changed = models.BooleanField(default=False)
    
    # Détails
    is_deal = models.BooleanField(default=False)
    screenshots = JSONField(default=dict, blank=True)
    extracted_data = JSONField(default=dict, blank=True)
    raw_data = JSONField(default=dict, blank=True)
    
    # Alerte
    alert_triggered = models.BooleanField(default=False)
    alert_type = models.CharField(max_length=50, null=True, blank=True)
    alert_message = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-monitored_at']
        indexes = [
            models.Index(fields=['product', 'monitored_at']),
            models.Index(fields=['price_changed']),
            models.Index(fields=['availability_changed']),
            models.Index(fields=['alert_triggered']),
        ]
    
    def __str__(self):
        return f"Result for {self.product} at {self.monitored_at}"


class MonitoringStats(models.Model):
    """
    Statistiques sur le monitoring pour aider à l'optimisation
    """
    # Période
    date = models.DateField(unique=True)
    
    # Statistiques globales
    total_tasks = models.IntegerField(default=0)
    completed_tasks = models.IntegerField(default=0)
    failed_tasks = models.IntegerField(default=0)
    
    # Temps d'exécution
    avg_execution_time = models.FloatField(null=True, blank=True)  # en secondes
    max_execution_time = models.FloatField(null=True, blank=True)  # en secondes
    min_execution_time = models.FloatField(null=True, blank=True)  # en secondes
    
    # Détection de changements
    price_changes_detected = models.IntegerField(default=0)
    availability_changes_detected = models.IntegerField(default=0)
    alerts_triggered = models.IntegerField(default=0)
    
    # Par priorité
    high_priority_tasks = models.IntegerField(default=0)
    normal_priority_tasks = models.IntegerField(default=0)
    low_priority_tasks = models.IntegerField(default=0)
    
    # Répartition par retailer
    retailer_distribution = JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name_plural = "Monitoring stats"
        indexes = [
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"Stats for {self.date}"
