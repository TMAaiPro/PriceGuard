from django.db import models

class Alert(models.Model):
    """Alertes déclenchées pour les utilisateurs"""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    price_point = models.ForeignKey('prices.PricePoint', on_delete=models.CASCADE)
    previous_price = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=20, choices=[
        ('price_drop', 'Price Drop'),
        ('target_reached', 'Target Price Reached'),
        ('back_in_stock', 'Back In Stock'),
        ('lowest_ever', 'Lowest Price Ever'),
    ])
    percentage_drop = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    absolute_drop = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'alerts'
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]