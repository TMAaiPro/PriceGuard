import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta

from monitoring.tasks import _perform_monitoring, schedule_monitoring_tasks, process_monitoring_queue
from monitoring.models import MonitoringTask

@pytest.mark.django_db
class TestMonitoringTasks:
    
    @patch('monitoring.tasks.PuppeteerBridge')
    @patch('monitoring.tasks.get_extractor_for_url')
    @patch('monitoring.tasks.MonitoringResultsAnalyzer.analyze_result')
    def test_perform_monitoring(self, mock_analyze, mock_get_extractor, mock_puppeteer, 
                               product_factory, monitoring_task_factory):
        """Teste l'exécution d'une tâche de monitoring"""
        # Configurer les mocks
        mock_puppeteer_instance = MagicMock()
        mock_puppeteer.return_value = mock_puppeteer_instance
        
        mock_extractor = MagicMock()
        mock_get_extractor.return_value = mock_extractor
        
        mock_result = MagicMock()
        mock_result.id = 'test-result-id'
        mock_result.price_changed = True
        mock_result.availability_changed = False
        mock_result.alert_triggered = False
        mock_analyze.return_value = mock_result
        
        # Données extraites simulées
        extracted_data = {
            'price': 99.99,
            'in_stock': True,
            'title': 'Test Product'
        }
        mock_puppeteer_instance.run_async.return_value = extracted_data
        
        # Créer un produit et une tâche
        product = product_factory(url='https://example.com/product')
        task = monitoring_task_factory(product=product)
        
        # Simuler une classe Celery task
        celery_task = MagicMock()
        
        # Exécuter la tâche
        result = _perform_monitoring(celery_task, str(task.id))
        
        # Vérifier que le bridge Puppeteer a été appelé
        mock_puppeteer.assert_called_once()
        mock_puppeteer_instance.run_async.assert_called_once()
        
        # Vérifier que l'extracteur a été récupéré
        mock_get_extractor.assert_called_once_with(product.url)
        
        # Vérifier que le résultat a été analysé
        mock_analyze.assert_called_once_with(product, extracted_data)
        
        # Vérifier le résultat
        assert result['status'] == 'success'
        assert result['result_id'] == 'test-result-id'
        
        # Vérifier que la tâche a été marquée comme terminée
        task.refresh_from_db()
        assert task.status == 'completed'
        
    @patch('monitoring.tasks.MonitoringScheduler.schedule_products_for_monitoring')
    def test_schedule_monitoring_tasks(self, mock_schedule):
        """Teste la tâche de planification des tâches de monitoring"""
        mock_schedule.return_value = 10
        
        result = schedule_monitoring_tasks(batch_size=500)
        
        mock_schedule.assert_called_once_with(500)
        assert result['status'] == 'success'
        assert result['scheduled_count'] == 10
