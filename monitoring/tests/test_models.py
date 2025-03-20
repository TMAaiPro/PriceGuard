import pytest
from django.utils import timezone
from datetime import timedelta
import uuid
from decimal import Decimal

from monitoring.models import MonitoringTask, ProductMonitoringConfig, MonitoringResult
from products.models import Product, Retailer

@pytest.mark.django_db
class TestMonitoringTask:
    
    def test_task_creation(self, product_factory):
        """Teste la création d'une tâche de monitoring"""
        product = product_factory()
        
        task = MonitoringTask.objects.create(
            product=product,
            scheduled_time=timezone.now(),
            priority=5
        )
        
        assert task.id is not None
        assert task.status == 'pending'
        assert task.product.id == product.id
        assert task.retry_count == 0
        
    def test_task_state_transitions(self, product_factory):
        """Teste les transitions d'état d'une tâche"""
        product = product_factory()
        
        task = MonitoringTask.objects.create(
            product=product,
            scheduled_time=timezone.now(),
            priority=5
        )
        
        # Marquer comme en cours
        task.mark_as_running()
        task.refresh_from_db()
        
        assert task.status == 'running'
        assert task.started_at is not None
        
        # Marquer comme terminée
        result_data = {'price': 10.99, 'in_stock': True}
        task.mark_as_completed(result_data)
        task.refresh_from_db()
        
        assert task.status == 'completed'
        assert task.completed_at is not None
        assert task.result_data == result_data
        
    def test_task_failure_and_retry(self, product_factory):
        """Teste l'échec et les tentatives de réessai d'une tâche"""
        product = product_factory()
        
        task = MonitoringTask.objects.create(
            product=product,
            scheduled_time=timezone.now(),
            priority=5,
            max_retries=3
        )
        
        # Premier échec - retry possible
        is_final_failure = task.mark_as_failed("Erreur de connexion")
        task.refresh_from_db()
        
        assert not is_final_failure
        assert task.status == 'pending'  # Toujours en attente pour réessai
        assert task.retry_count == 1
        assert task.error_message == "Erreur de connexion"
        
        # Deuxième échec - retry possible
        is_final_failure = task.mark_as_failed("Timeout")
        task.refresh_from_db()
        
        assert not is_final_failure
        assert task.status == 'pending'
        assert task.retry_count == 2
        
        # Troisième échec - retry possible
        is_final_failure = task.mark_as_failed("Erreur serveur")
        task.refresh_from_db()
        
        assert not is_final_failure
        assert task.status == 'pending'
        assert task.retry_count == 3
        
        # Quatrième échec - échec définitif
        is_final_failure = task.mark_as_failed("Erreur fatale")
        task.refresh_from_db()
        
        assert is_final_failure
        assert task.status == 'failed'
        assert task.completed_at is not None
        assert task.error_message == "Erreur fatale"


@pytest.mark.django_db
class TestProductMonitoringConfig:
    
    def test_config_creation(self, product_factory):
        """Teste la création d'une configuration de monitoring"""
        product = product_factory()
        
        config = ProductMonitoringConfig.objects.create(
            product=product,
            frequency='normal',
            active=True
        )
        
        assert config.id is not None
        assert config.frequency == 'normal'
        assert config.priority_score == 5.0
        assert config.active is True
        
    def test_get_monitoring_interval(self, product_factory):
        """Teste le calcul des intervalles de monitoring"""
        product = product_factory()
        
        # Fréquence haute
        config = ProductMonitoringConfig.objects.create(
            product=product,
            frequency='high'
        )
        assert config.get_monitoring_interval() == 4
        
        # Fréquence normale
        config.frequency = 'normal'
        config.save()
        assert config.get_monitoring_interval() == 12
        
        # Fréquence basse
        config.frequency = 'low'
        config.save()
        assert config.get_monitoring_interval() == 24
        
        # Fréquence personnalisée
        config.frequency = 'custom'
        config.custom_frequency_hours = 6
        config.save()
        assert config.get_monitoring_interval() == 6


@pytest.mark.django_db
class TestMonitoringResult:
    
    def test_result_creation(self, product_factory, monitoring_task_factory):
        """Teste la création d'un résultat de monitoring"""
        product = product_factory()
        task = monitoring_task_factory(product=product)
        
        result = MonitoringResult.objects.create(
            product=product,
            task=task,
            monitored_at=timezone.now(),
            current_price=Decimal('99.99'),
            previously_available=True,
            currently_available=True
        )
        
        assert result.id is not None
        assert result.product.id == product.id
        assert result.task.id == task.id
        assert result.price_changed is False
        assert result.availability_changed is False
        
    def test_price_change_detection(self, product_factory, monitoring_task_factory):
        """Teste la détection des changements de prix"""
        product = product_factory(current_price=Decimal('100.00'))
        task = monitoring_task_factory(product=product)
        
        # Créer un résultat avec baisse de prix
        result = MonitoringResult.objects.create(
            product=product,
            task=task,
            monitored_at=timezone.now(),
            previous_price=Decimal('100.00'),
            current_price=Decimal('90.00'),
            previously_available=True,
            currently_available=True,
            price_changed=True,
            price_change_amount=Decimal('-10.00'),
            price_change_percentage=-10.0
        )
        
        assert result.price_changed is True
        assert result.price_change_amount == Decimal('-10.00')
        assert result.price_change_percentage == -10.0
