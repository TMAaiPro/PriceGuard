from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Utilisateur PriceGuard étendu"""
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    notification_email = models.BooleanField(default=True)
    notification_push = models.BooleanField(default=True)
    premium_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'price_users'