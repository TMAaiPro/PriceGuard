from django.db.models.signals import post_save
from django.dispatch import receiver
from products.models import ProductPrice, UserProduct
from .models import Alert, AlertType

@receiver(post_save, sender=ProductPrice)
def check_price_alerts(sender, instance, created, **kwargs):
    """
    Check if a price change should trigger alerts for users tracking this product
    """
    if not created:
        return
        
    product = instance.product
    current_price = instance.price
    
    # Find the price before this one
    previous_price = ProductPrice.objects.filter(
        product=product,
        timestamp__lt=instance.timestamp
    ).order_by('-timestamp').first()
    
    # If this is the first price or price didn't change, no alert needed
    if not previous_price or previous_price.price == current_price:
        return
        
    # Check if price decreased
    if current_price < previous_price.price:
        price_drop_pct = ((previous_price.price - current_price) / previous_price.price) * 100
        
        # Find users tracking this product who want price drop alerts
        tracking_users = UserProduct.objects.filter(
            product=product,
            notify_price_drop=True
        )
        
        # Get the price drop alert type
        alert_type, _ = AlertType.objects.get_or_create(
            name="Price Drop",
            defaults={
                'description': 'Alert for when a product price drops',
                'is_active': True
            }
        )
        
        # For each user tracking this product
        for user_product in tracking_users:
            user = user_product.user
            
            # Check if user specified a target price and it hasn't been reached
            if user_product.target_price and current_price > user_product.target_price:
                continue
                
            # Create alert
            Alert.objects.create(
                user=user,
                product=product,
                alert_type=alert_type,
                status='new',
                message=f"Price drop: {product.name} is now {current_price} {product.currency} "\
                        f"(was {previous_price.price} {product.currency}, {price_drop_pct:.1f}% drop)",
                details={
                    'previous_price': str(previous_price.price),
                    'current_price': str(current_price),
                    'drop_percentage': float(price_drop_pct),
                    'product_url': product.url,
                    'product_image': product.image_url
                }
            )
