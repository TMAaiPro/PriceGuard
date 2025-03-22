import logging
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import json

from .models import AlertRule, NotificationDelivery, NotificationBatch
from alerts.models import Alert
from products.models import Product, PriceHistory

logger = logging.getLogger(__name__)

# Classes de services à implémenter
