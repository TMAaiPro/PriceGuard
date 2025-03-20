# This makes the priceguard directory a Python package

# Import Celery app
from .celery import app as celery_app

__all__ = ['celery_app']
