from django.db import models
from django.contrib.postgres.fields import JSONField

class PricePrediction(models.Model):
    """Prédictions de prix générées par l'Analytics Service"""
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    prediction_date = models.DateField()
    min_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_price = models.DecimalField(max_digits=10, decimal_places=2)
    expected_price = models.DecimalField(max_digits=10, decimal_places=2)
    confidence = models.DecimalField(max_digits=5, decimal_places=2)  # 0-100%
    model_version = models.CharField(max_length=50)
    prediction_data = JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'price_predictions'
        unique_together = ['product', 'prediction_date']