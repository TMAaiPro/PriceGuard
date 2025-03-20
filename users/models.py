from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

from .managers import UserManager


class User(AbstractUser):
    """Custom user model that uses email as the unique identifier instead of username"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # Remove username field
    email = models.EmailField(_('email address'), unique=True)
    
    # Additional fields
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    unread_notifications_count = models.IntegerField(default=0)
    
    # Subscription status
    is_premium = models.BooleanField(default=False)
    premium_until = models.DateTimeField(null=True, blank=True)
    
    # Account status
    email_verified = models.BooleanField(default=False)
    account_deactivated = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']
        db_table = 'pg_users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_premium']),
        ]

    def __str__(self):
        return self.email
    
    def is_premium_active(self):
        """Check if user has an active premium subscription"""
        if not self.is_premium:
            return False
        
        if self.premium_until is None:
            return False
            
        return self.premium_until > timezone.now()
    
    def get_full_name(self):
        """Return the full name of the user"""
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()


class UserPreference(models.Model):
    """User preferences for notifications and alerts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    
    # Alert thresholds
    price_drop_threshold_percentage = models.FloatField(default=5.0, 
                                                      help_text="Minimum price drop percentage to trigger an alert")
    price_drop_threshold_absolute = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                                     help_text="Minimum absolute price drop to trigger an alert")
    
    # Notification settings
    notify_on_price_drop = models.BooleanField(default=True)
    notify_on_availability_change = models.BooleanField(default=True)
    notify_on_price_increase = models.BooleanField(default=False)
    
    # Frequency settings
    notification_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('hourly', 'Hourly digest'),
            ('daily', 'Daily digest'),
        ],
        default='immediate'
    )
    
    # Daily summary hour (for daily digests)
    daily_summary_hour = models.IntegerField(default=9, help_text="Hour of the day for daily summary (0-23)")
    
    # Display preferences
    currency = models.CharField(max_length=3, default='EUR')
    price_display = models.CharField(
        max_length=20,
        choices=[
            ('with_tax', 'With tax'),
            ('without_tax', 'Without tax'),
        ],
        default='with_tax'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pg_user_preferences'
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Preferences for {self.user.email}"


class UserDevice(models.Model):
    """User device for push notifications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    
    # Device information
    device_id = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('ios', 'iOS'),
            ('android', 'Android'),
            ('web', 'Web'),
        ]
    )
    device_name = models.CharField(max_length=255, blank=True)
    
    # Push notification token
    push_token = models.TextField(blank=True)
    
    # Device status
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(default=timezone.now)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pg_user_devices'
        indexes = [
            models.Index(fields=['user', 'device_type']),
            models.Index(fields=['device_id']),
            models.Index(fields=['is_active']),
        ]
        
    def __str__(self):
        return f"{self.device_type} device for {self.user.email}"
