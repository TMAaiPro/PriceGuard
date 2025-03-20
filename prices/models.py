from django.db import models
from timescale.db.models.models import TimescaleModel

class PricePoint(TimescaleModel):
    """Historique des prix (TimescaleDB)"""
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')
    is_available = models.BooleanField()
    is_deal = models.BooleanField(default=False)
    source = models.CharField(max_length=50, default='scraper')
    
    class Meta:
        db_table = 'price_history'
        indexes = [
            models.Index(fields=['product', 'time']),
        ]