import pytest
from django.utils import timezone
from decimal import Decimal
import uuid
import datetime

from django.contrib.auth import get_user_model
from monitoring.models import MonitoringTask, ProductMonitoringConfig, MonitoringResult, MonitoringStats
from products.models import Product, Retailer

User = get_user_model()

@pytest.fixture
def admin_user(db):
    """Crée un utilisateur admin pour les tests"""
    user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='password123'
    )
    return user

@pytest.fixture
def standard_user(db):
    """Crée un utilisateur standard pour les tests"""
    user = User.objects.create_user(
        username='user',
        email='user@example.com',
        password='password123'
    )
    return user

@pytest.fixture
def retailer_factory(db):
    """Factory pour créer des retailers"""
    def create_retailer(**kwargs):
        defaults = {
            'name': f'Test Retailer {uuid.uuid4().hex[:8]}',
            'website': 'https://example.com',
            'logo': 'https://example.com/logo.png',
            'active': True
        }
        defaults.update(kwargs)
        return Retailer.objects.create(**defaults)
    return create_retailer

@pytest.fixture
def product_factory(db, retailer_factory):
    """Factory pour créer des produits"""
    def create_product(**kwargs):
        retailer = kwargs.get('retailer')
        if retailer is None:
            retailer = retailer_factory()
        
        defaults = {
            'title': f'Test Product {uuid.uuid4().hex[:8]}',
            'url': f'https://example.com/product/{uuid.uuid4().hex}',
            'retailer': retailer,
            'current_price': Decimal('99.99'),
            'is_available': True,
            'last_checked': timezone.now(),
            'lowest_price': Decimal('89.99'),
            'highest_price': Decimal('109.99')
        }
        defaults.update(kwargs)
        return Product.objects.create(**defaults)
    return create_product

@pytest.fixture
def monitoring_task_factory(db, product_factory):
    """Factory pour créer des tâches de monitoring"""
    def create_monitoring_task(**kwargs):
        product = kwargs.get('product')
        if product is None:
            product = product_factory()
        
        defaults = {
            'product': product,
            'scheduled_time': timezone.now(),
            'priority': 5,
            'status': 'pending',
            'retry_count': 0,
            'max_retries': 3
        }
        defaults.update(kwargs)
        return MonitoringTask.objects.create(**defaults)
    return create_monitoring_task

@pytest.fixture
def product_monitoring_config_factory(db, product_factory):
    """Factory pour créer des configurations de monitoring de produit"""
    def create_product_monitoring_config(**kwargs):
        product = kwargs.get('product')
        if product is None:
            product = product_factory()
        
        defaults = {
            'product': product,
            'frequency': 'normal',
            'active': True,
            'priority_score': 5.0,
            'manual_priority_boost': 0.0,
            'take_screenshot': True,
            'notify_on_any_change': False,
            'last_monitored': timezone.now() - datetime.timedelta(hours=6),
            'next_scheduled': timezone.now() + datetime.timedelta(hours=6)
        }
        defaults.update(kwargs)
        return ProductMonitoringConfig.objects.create(**defaults)
    return create_product_monitoring_config

@pytest.fixture
def monitoring_result_factory(db, product_factory, monitoring_task_factory):
    """Factory pour créer des résultats de monitoring"""
    def create_monitoring_result(**kwargs):
        product = kwargs.get('product')
        if product is None:
            product = product_factory()
        
        task = kwargs.get('task')
        if task is None and kwargs.get('create_task', True):
            task = monitoring_task_factory(product=product)
        
        defaults = {
            'product': product,
            'task': task,
            'monitored_at': timezone.now(),
            'current_price': Decimal('99.99'),
            'previously_available': True,
            'currently_available': True,
            'price_changed': False,
            'availability_changed': False,
            'is_deal': False,
            'alert_triggered': False
        }
        defaults.update(kwargs)
        if 'create_task' in defaults:
            del defaults['create_task']
        return MonitoringResult.objects.create(**defaults)
    return create_monitoring_result

@pytest.fixture
def monitoring_stats_factory(db):
    """Factory pour créer des statistiques de monitoring"""
    def create_monitoring_stats(**kwargs):
        defaults = {
            'date': timezone.now().date(),
            'total_tasks': 100,
            'completed_tasks': 85,
            'failed_tasks': 15,
            'avg_execution_time': 12.5,
            'max_execution_time': 60.0,
            'min_execution_time': 2.5,
            'price_changes_detected': 25,
            'availability_changes_detected': 10,
            'alerts_triggered': 20,
            'high_priority_tasks': 30,
            'normal_priority_tasks': 50,
            'low_priority_tasks': 20,
            'retailer_distribution': {
                'Amazon': 40,
                'Fnac': 30,
                'Darty': 30
            }
        }
        defaults.update(kwargs)
        return MonitoringStats.objects.create(**defaults)
    return create_monitoring_stats
