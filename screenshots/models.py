from django.db import models

class Screenshot(models.Model):
    """Captures d'écran comme preuves de prix"""
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    price_point = models.ForeignKey('prices.PricePoint', on_delete=models.CASCADE, null=True)
    image = models.ImageField(upload_to='screenshots/%Y/%m/%d/')
    thumbnail = models.ImageField(upload_to='screenshots/thumbs/%Y/%m/%d/', null=True)
    type = models.CharField(max_length=20, choices=[
        ('full_page', 'Full Page'),
        ('product_detail', 'Product Detail'),
        ('price_element', 'Price Element'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'screenshots'