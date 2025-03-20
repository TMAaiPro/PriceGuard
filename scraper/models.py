from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import JSONField

class Retailer(models.Model):
    """Détaillant (Amazon, Fnac, etc.)"""
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='retailer_logos/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """Produit à surveiller"""
    url = models.URLField(max_length=1000, unique=True)
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE, related_name='products')
    title = models.CharField(max_length=500)
    image_url = models.URLField(max_length=1000, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    sku = models.CharField(max_length=100, null=True, blank=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')
    lowest_price = models.DecimalField(max_digits=10, decimal_places=2)
    highest_price = models.DecimalField(max_digits=10, decimal_places=2)
    last_checked = models.DateTimeField()
    is_available = models.BooleanField(default=True)
    metadata = JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class PricePoint(models.Model):
    """Point de prix historique pour un produit"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_points')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')
    timestamp = models.DateTimeField(default=timezone.now)
    is_available = models.BooleanField(default=True)
    is_deal = models.BooleanField(default=False)
    source = models.CharField(max_length=50, default='scraper')
    metadata = JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.product.title} - {self.price} {self.currency} ({self.timestamp})"

class Screenshot(models.Model):
    """Capture d'écran d'un produit"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='screenshots')
    price_point = models.ForeignKey(PricePoint, on_delete=models.CASCADE, related_name='screenshots', null=True, blank=True)
    image = models.ImageField(upload_to='screenshots/%Y/%m/%d/')
    type = models.CharField(max_length=50, default='full_page')
    timestamp = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.product.title} - {self.type} ({self.timestamp})"

class ScrapingTask(models.Model):
    """Tâche de scraping à planifier"""
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('processing', 'En cours de traitement'),
        ('completed', 'Terminée'),
        ('failed', 'Échouée'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='scraping_tasks', null=True, blank=True)
    url = models.URLField(max_length=1000, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.PositiveSmallIntegerField(default=5)  # 1=haute, 10=basse
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=36, null=True, blank=True)
    metadata = JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['priority', 'created_at']
    
    def __str__(self):
        if self.product:
            return f"Tâche pour {self.product.title} ({self.status})"
        else:
            return f"Tâche pour {self.url} ({self.status})"
