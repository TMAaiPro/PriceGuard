from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product, ProductPrice

@receiver(post_save, sender=Product)
def create_price_history(sender, instance, created, **kwargs):
    """
    Create a ProductPrice entry when a product is created or its price changes.
    """
    # Only create a price record if it's a new product or if the price has changed
    should_create = created

    if not created:
        # Check if the current_price has changed by comparing with the latest price history
        latest_price = ProductPrice.objects.filter(product=instance).order_by('-timestamp').first()
        if latest_price and latest_price.price != instance.current_price:
            should_create = True

    if should_create:
        ProductPrice.objects.create(
            product=instance,
            price=instance.current_price
        )
