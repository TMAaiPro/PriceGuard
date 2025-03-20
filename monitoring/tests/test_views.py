import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
import uuid
from decimal import Decimal

from monitoring.models import MonitoringTask, ProductMonitoringConfig, MonitoringResult

@pytest.mark.django_db
class TestMonitoringTaskViewSet:
    
    def test_list_tasks(self, admin_user, product_factory, monitoring_task_factory):
        """Teste la récupération de la liste des tâches"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        # Créer des tâches
        product = product_factory()
        task1 = monitoring_task_factory(product=product, status='pending')
        task2 = monitoring_task_factory(product=product, status='completed')
        
        # Récupérer la liste
        url = reverse('monitoringtask-list')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
    
    def test_schedule_product(self, admin_user, product_factory):
        """Teste la planification d'un produit spécifique"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        product = product_factory()
        
        url = reverse('monitoringtask-schedule-product')
        data = {'product_id': product.id, 'priority': 3}
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['product'] == product.id
        assert response.data['priority'] == 3
        
        # Vérifier que la tâche a été créée
        task = MonitoringTask.objects.get(id=response.data['id'])
        assert task.product.id == product.id
    
    def test_task_stats(self, admin_user, product_factory, monitoring_task_factory):
        """Teste la récupération des statistiques de tâches"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        # Créer des tâches avec différents statuts
        product = product_factory()
        monitoring_task_factory(product=product, status='pending', priority=2)
        monitoring_task_factory(product=product, status='running', priority=5)
        monitoring_task_factory(product=product, status='completed', priority=8)
        monitoring_task_factory(product=product, status='failed', priority=3)
        
        url = reverse('monitoringtask-stats')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 4
        assert response.data['pending'] == 1
        assert response.data['running'] == 1
        assert response.data['completed'] == 1
        assert response.data['failed'] == 1
        assert response.data['high_priority'] == 2  # Priority <= 3
        assert response.data['normal_priority'] == 1  # 3 < Priority <= 7
        assert response.data['low_priority'] == 1  # Priority > 7


@pytest.mark.django_db
class TestProductMonitoringConfigViewSet:
    
    def test_update_frequency(self, admin_user, product_factory, product_monitoring_config_factory):
        """Teste la mise à jour de la fréquence de monitoring"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        product = product_factory()
        config = product_monitoring_config_factory(
            product=product,
            frequency='normal'
        )
        
        url = reverse('productmonitoringconfig-update-frequency', args=[config.id])
        data = {'frequency': 'high'}
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['frequency'] == 'high'
        
        # Vérifier que la config a été mise à jour
        config.refresh_from_db()
        assert config.frequency == 'high'
    
    def test_update_priority(self, admin_user, product_factory, product_monitoring_config_factory):
        """Teste la mise à jour manuelle de la priorité"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        product = product_factory()
        config = product_monitoring_config_factory(
            product=product,
            manual_priority_boost=0
        )
        
        url = reverse('productmonitoringconfig-update-priority', args=[config.id])
        data = {'manual_priority_boost': 5.0}
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['manual_priority_boost'] == 5.0
        
        # Vérifier que la config a été mise à jour
        config.refresh_from_db()
        assert config.manual_priority_boost == 5.0

    def test_bulk_update(self, admin_user, product_factory, product_monitoring_config_factory):
        """Teste la mise à jour en masse des configurations"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        # Créer plusieurs produits avec configurations
        product1 = product_factory()
        product2 = product_factory()
        config1 = product_monitoring_config_factory(product=product1, active=True, frequency='normal')
        config2 = product_monitoring_config_factory(product=product2, active=True, frequency='normal')
        
        url = reverse('productmonitoringconfig-bulk-update')
        data = {
            'product_ids': [product1.id, product2.id],
            'update_data': {
                'frequency': 'high',
                'take_screenshot': False
            }
        }
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['updated_count'] == 2
        
        # Vérifier que les configs ont été mises à jour
        config1.refresh_from_db()
        config2.refresh_from_db()
        assert config1.frequency == 'high'
        assert config2.frequency == 'high'
        assert config1.take_screenshot is False
        assert config2.take_screenshot is False


@pytest.mark.django_db
class TestMonitoringResultViewSet:
    
    def test_product_history(self, admin_user, product_factory, monitoring_result_factory):
        """Teste la récupération de l'historique d'un produit"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        product = product_factory()
        result1 = monitoring_result_factory(
            product=product,
            current_price=Decimal('100.00')
        )
        result2 = monitoring_result_factory(
            product=product,
            current_price=Decimal('90.00'),
            price_changed=True
        )
        
        url = reverse('monitoringresult-product-history')
        response = client.get(url, {'product_id': product.id})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
    
    def test_recent_alerts(self, admin_user, product_factory, monitoring_result_factory):
        """Teste la récupération des alertes récentes"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        product = product_factory()
        result1 = monitoring_result_factory(
            product=product,
            alert_triggered=True,
            alert_type='price_drop'
        )
        result2 = monitoring_result_factory(
            product=product,
            alert_triggered=True,
            alert_type='back_in_stock'
        )
        
        url = reverse('monitoringresult-recent-alerts')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert any(item['alert_type'] == 'price_drop' for item in response.data)
        assert any(item['alert_type'] == 'back_in_stock' for item in response.data)

    def test_price_trends(self, admin_user, product_factory, monitoring_result_factory):
        """Teste la récupération des tendances de prix"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        import datetime
        from django.utils import timezone
        
        product = product_factory()
        today = timezone.now()
        yesterday = today - datetime.timedelta(days=1)
        
        result1 = monitoring_result_factory(
            product=product,
            monitored_at=yesterday,
            current_price=Decimal('100.00')
        )
        result2 = monitoring_result_factory(
            product=product,
            monitored_at=today,
            current_price=Decimal('90.00')
        )
        
        url = reverse('monitoringresult-price-trends')
        response = client.get(url, {'product_id': product.id, 'days': 7})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        price_values = [item['price'] for item in response.data]
        assert 100.0 in price_values
        assert 90.0 in price_values


@pytest.mark.django_db
class TestMonitoringStatsViewSet:
    
    def test_stats_summary(self, admin_user, monitoring_stats_factory):
        """Teste la récupération du résumé des statistiques"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        import datetime
        from django.utils import timezone
        
        today = timezone.now().date()
        yesterday = today - datetime.timedelta(days=1)
        
        stats1 = monitoring_stats_factory(
            date=yesterday,
            total_tasks=100,
            completed_tasks=80,
            failed_tasks=20,
            price_changes_detected=15
        )
        stats2 = monitoring_stats_factory(
            date=today,
            total_tasks=120,
            completed_tasks=100,
            failed_tasks=20,
            price_changes_detected=25
        )
        
        url = reverse('monitoringstats-summary')
        response = client.get(url, {'days': 7})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_tasks'] == 220
        assert response.data['completed_tasks'] == 180
        assert response.data['failed_tasks'] == 40
        assert response.data['price_changes_detected'] == 40
        assert len(response.data['daily_data']) == 2
