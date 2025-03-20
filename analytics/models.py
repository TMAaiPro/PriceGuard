from django.db import models
from django.conf import settings
from core.models import TimeStampedModel

class PriceInsight(TimeStampedModel):
    """Model for storing insights about product prices"""
    INSIGHT_TYPES = [
        ('volatility', 'Price Volatility'),
        ('trend', 'Price Trend'),
        ('seasonality', 'Seasonality'),
        ('comparison', 'Market Comparison'),
        ('anomaly', 'Price Anomaly'),
    ]
    
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE,
                              related_name='price_insights')
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPES)
    content = models.TextField()
    data = models.JSONField(blank=True, null=True,
                          help_text="Structured data supporting the insight")
    
    def __str__(self):
        return f"{self.product.name} - {self.get_insight_type_display()}"


class PricePrediction(TimeStampedModel):
    """Model for price predictions"""
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE,
                              related_name='price_predictions')
    predicted_price = models.DecimalField(max_digits=10, decimal_places=2)
    prediction_date = models.DateField(help_text="Date for which price is predicted")
    confidence = models.FloatField(default=0.0, 
                                 help_text="Confidence level (0-1)")
    model_used = models.CharField(max_length=100, blank=True, null=True,
                                help_text="Name of prediction model used")
    accuracy = models.FloatField(null=True, blank=True,
                               help_text="Accuracy of prediction (populated after actual price is known)")
    features = models.JSONField(blank=True, null=True,
                              help_text="Features used for prediction")
    
    class Meta:
        ordering = ['-prediction_date']
    
    def __str__(self):
        return f"{self.product.name} - {self.prediction_date} - {self.predicted_price}"


class UserAnalytics(TimeStampedModel):
    """Model for tracking user interactions for analytics"""
    ACTION_TYPES = [
        ('search', 'Product Search'),
        ('view', 'Product View'),
        ('track', 'Start Tracking'),
        ('untrack', 'Stop Tracking'),
        ('alert_view', 'Alert View'),
        ('alert_action', 'Alert Action'),
        ('settings', 'Change Settings'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                           related_name='analytics_events')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL,
                              related_name='user_events', null=True, blank=True)
    session_id = models.CharField(max_length=100, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    referrer = models.URLField(blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True,
                                 help_text="Duration of action in seconds")
    details = models.JSONField(blank=True, null=True,
                             help_text="Additional event details")
    
    class Meta:
        verbose_name_plural = 'User analytics'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_action_type_display()}"
