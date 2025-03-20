from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.validators import URLValidator
from core.models import TimeStampedModel

class Retailer(TimeStampedModel):
    """Retailer model where products are sold"""
    name = models.CharField(max_length=255)
    website = models.URLField(max_length=255)
    logo_url = models.URLField(max_length=512, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    scraping_class = models.CharField(max_length=100, blank=True, null=True, 
                                      help_text="Python class used for scraping this retailer")
    
    def __str__(self):
        return self.name

class Category(TimeStampedModel):
    """Product category model"""
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, 
                              on_delete=models.SET_NULL, 
                              related_name='children')
    
    class Meta:
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Product(TimeStampedModel):
    """Product model for tracking prices"""
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=100, blank=True, null=True)
    upc = models.CharField(max_length=100, blank=True, null=True)
    url = models.URLField(max_length=512, validators=[URLValidator()])
    image_url = models.URLField(max_length=512, blank=True, null=True)
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE, related_name='products')
    categories = models.ManyToManyField(Category, related_name='products', blank=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, 
                                   help_text="Original price before any discounts")
    currency = models.CharField(max_length=3, default='USD')
    is_active = models.BooleanField(default=True)
    last_checked = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class ProductPrice(TimeStampedModel):
    """Model for storing price history"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        get_latest_by = 'timestamp'
    
    def __str__(self):
        return f"{self.product.name} - {self.price} ({self.timestamp})"

class ProductImage(TimeStampedModel):
    """Model for storing additional product images"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField(max_length=512)
    alt_text = models.CharField(max_length=255, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.product.name} - Image {self.order}"

class UserProduct(TimeStampedModel):
    """Model for tracking user's product interests"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                            related_name='tracked_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, 
                              related_name='tracking_users')
    target_price = models.DecimalField(max_digits=10, decimal_places=2, 
                                     blank=True, null=True)
    notify_price_drop = models.BooleanField(default=True)
    notify_availability = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('user', 'product')
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name}"
