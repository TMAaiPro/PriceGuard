from django.db import models
from django.conf import settings
from core.models import TimeStampedModel

class AlertType(TimeStampedModel):
    """Types of alerts that can be generated"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name


class AlertConfiguration(TimeStampedModel):
    """User-specific alert settings"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                            related_name='alert_configs')
    alert_type = models.ForeignKey(AlertType, on_delete=models.CASCADE,
                                  related_name='configurations')
    is_active = models.BooleanField(default=True)
    threshold = models.JSONField(blank=True, null=True, 
                               help_text="Alert-specific threshold configuration")
    
    class Meta:
        unique_together = ('user', 'alert_type')
    
    def __str__(self):
        return f"{self.user.email} - {self.alert_type.name}"


class Alert(TimeStampedModel):
    """Individual alerts generated for users"""
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('dismissed', 'Dismissed'),
        ('actioned', 'Actioned'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                            related_name='alerts')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE,
                              related_name='alerts')
    alert_type = models.ForeignKey(AlertType, on_delete=models.CASCADE,
                                  related_name='alerts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    message = models.TextField()
    details = models.JSONField(blank=True, null=True, 
                             help_text="Additional alert details")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name} - {self.alert_type.name}"


class AlertAction(TimeStampedModel):
    """Actions taken on alerts"""
    ACTION_CHOICES = [
        ('view', 'Viewed'),
        ('dismiss', 'Dismissed'),
        ('click', 'Clicked Through'),
        ('save', 'Saved For Later'),
        ('purchase', 'Purchased'),
    ]
    
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='actions')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.alert} - {self.get_action_display()}"
