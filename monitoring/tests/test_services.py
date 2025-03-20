import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import uuid

from monitoring.models import MonitoringTask, ProductMonitoringConfig, MonitoringResult
from monitoring.services import MonitoringScheduler, MonitoringPrioritizer, MonitoringResultsAnalyzer
from products.models import Product, PricePoint

@pytest.mark.django_db
class TestMonitoringScheduler:
    
    def test_schedule_products_for_monitoring(self, product_factory, product_monitoring_config_factory):
        """Teste la planification des tâches de monitoring"""
        # Créer des produits avec des configurations
        now = timezone.now()
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)
        
        # Produit 1: doit être vérifié (next_scheduled dans le passé)
        product1 = product_factory()
        config1 = product_monitoring_config_factory(
            product=product1,
            active=True,
            next_scheduled=past
        )
        
        # Produit 2: ne doit pas être vérifié (next_scheduled dans le futur)
        product2 = product_factory()
        config2 = product_monitoring_config_factory(
            product=product2,
            active=True,
            next_scheduled=future
        )
        
        # Produit 3: ne doit pas être vérifié (inactif)
        product3 = product_factory()
        config3 = product_monitoring_config_factory(
            product=product3,
            active=False,
            next_scheduled=past
        )
        
        # Exécuter la planification
        tasks_created = MonitoringScheduler.schedule_products_for_monitoring()
        
        # Vérifier qu'une seule tâche a été créée
        assert tasks_created == 1
        
        # Vérifier que la tâche a été créée pour le bon produit
        task = MonitoringTask.objects.filter(product=product1).first()
        assert task is not None
        assert task.status == 'pending'
        
        # Vérifier que la config a été mise à jour
        config1.refresh_from_db()
        assert config1.next_scheduled > now
        
    def test_schedule_specific_product(self, product_factory):
        """Teste la planification immédiate d'un produit spécifique"""
        product = product_factory()
        
        # Planifier le produit
        task = MonitoringScheduler.schedule_specific_product(product.id, priority=2)
        
        # Vérifier que la tâche a été créée
        assert task is not None
        assert task.product.id == product.id
        assert task.priority == 2
        assert task.status == 'pending'
        
        # Vérifier que la config a été créée
        config = ProductMonitoringConfig.objects.get(product=product)
        assert config is not None
        assert config.active is True
        assert config.next_scheduled > timezone.now()
        

@pytest.mark.django_db
class TestMonitoringResultsAnalyzer:
    
    def test_analyze_result_new_product(self, product_factory):
        """Teste l'analyse d'un résultat pour un nouveau produit"""
        product = product_factory(
            current_price=Decimal('100.00'),
            is_available=True
        )
        
        # Données actuelles
        current_data = {
            'price': Decimal('100.00'),
            'in_stock': True,
            'is_deal': False,
            'screenshots': {'full_page': 'path/to/screenshot.jpg'}
        }
        
        # Analyser le résultat
        result = MonitoringResultsAnalyzer.analyze_result(product, current_data)
        
        # Vérifier le résultat
        assert result.id is not None
        assert result.product.id == product.id
        assert result.current_price == Decimal('100.00')
        assert result.currently_available is True
        assert result.price_changed is False  # Pas de changement car premier résultat
        assert result.availability_changed is False
        assert result.alert_triggered is False
        assert result.screenshots == {'full_page': 'path/to/screenshot.jpg'}
        
    def test_analyze_result_price_drop(self, product_factory, monitoring_result_factory):
        """Teste l'analyse d'un résultat avec baisse de prix"""
        product = product_factory(
            current_price=Decimal('100.00'),
            is_available=True
        )
        
        # Créer un résultat précédent
        previous_result = monitoring_result_factory(
            product=product,
            current_price=Decimal('100.00'),
            currently_available=True
        )
        
        # Créer une configuration pour le produit
        config = ProductMonitoringConfig.objects.create(
            product=product,
            active=True,
            notify_on_any_change=True
        )
        
        # Données actuelles avec baisse de prix
        current_data = {
            'price': Decimal('90.00'),
            'in_stock': True,
            'is_deal': True
        }
        
        # Analyser le résultat
        result = MonitoringResultsAnalyzer.analyze_result(product, current_data)
        
        # Vérifier le résultat
        assert result.price_changed is True
        assert result.price_change_amount == Decimal('-10.00')
        assert result.price_change_percentage == -10.0
        assert result.alert_triggered is True
        assert result.alert_type == 'price_drop'
        assert 'Le prix a baissé' in result.alert_message
