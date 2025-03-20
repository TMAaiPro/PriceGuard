from django.db import models
from django.contrib.postgres.fields import JSONField

class Retailer(models.Model):
    """Sites e-commerce suivis"""
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=255)
    logo_url = models.URLField()
    scraping_config = JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'retailers'

class Product(models.Model):
    """Produits suivis par les utilisateurs"""
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=2000)
    image_url = models.URLField(max_length=2000, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    sku = models.CharField(max_length=100, null=True, blank=True)
    retailer = models.ForeignKey('Retailer', on_delete=models.CASCADE)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')
    lowest_price = models.DecimalField(max_digits=10, decimal_places=2)
    highest_price = models.DecimalField(max_digits=10, decimal_places=2)
    last_checked = models.DateTimeField()
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = JSONField(default=dict)
    
    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['url']),
            models.Index(fields=['retailer']),
            models.Index(fields=['is_available']),
        ]

class UserProduct(models.Model):
    """Association entre utilisateurs et produits suivis"""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    alert_on_any_decrease = models.BooleanField(default=False)
    alert_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_products'
        unique_together = ['user', 'product']