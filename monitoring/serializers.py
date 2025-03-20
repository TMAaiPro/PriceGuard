from rest_framework import serializers
from .models import MonitoringTask, ProductMonitoringConfig, MonitoringResult, MonitoringStats


class MonitoringTaskSerializer(serializers.ModelSerializer):
    """Serializer pour les tâches de monitoring"""
    
    class Meta:
        model = MonitoringTask
        fields = [
            'id', 'product', 'status', 'priority', 'scheduled_time',
            'started_at', 'completed_at', 'error_message', 'created_at',
        ]
        read_only_fields = [
            'id', 'status', 'started_at', 'completed_at', 
            'error_message', 'created_at',
        ]


class MonitoringTaskDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour les tâches de monitoring"""
    
    class Meta:
        model = MonitoringTask
        fields = [
            'id', 'product', 'status', 'priority', 'scheduled_time',
            'started_at', 'completed_at', 'error_message', 'result_data',
            'created_at', 'updated_at', 'retry_count', 'max_retries',
            'celery_task_id', 'creator',
        ]
        read_only_fields = [
            'id', 'status', 'started_at', 'completed_at', 'error_message',
            'result_data', 'created_at', 'updated_at', 'retry_count',
            'celery_task_id',
        ]


class ProductMonitoringConfigSerializer(serializers.ModelSerializer):
    """Serializer pour la configuration de monitoring d'un produit"""
    
    class Meta:
        model = ProductMonitoringConfig
        fields = [
            'id', 'product', 'frequency', 'custom_frequency_hours',
            'priority_score', 'manual_priority_boost', 'take_screenshot',
            'notify_on_any_change', 'price_threshold_percentage',
            'price_threshold_absolute', 'active', 'last_monitored',
            'next_scheduled',
        ]
        read_only_fields = [
            'id', 'priority_score', 'last_monitored', 'next_scheduled',
        ]


class MonitoringResultSerializer(serializers.ModelSerializer):
    """Serializer pour les résultats de monitoring"""
    
    class Meta:
        model = MonitoringResult
        fields = [
            'id', 'product', 'task', 'monitored_at', 'current_price',
            'previous_price', 'price_changed', 'price_change_amount',
            'price_change_percentage', 'currently_available',
            'previously_available', 'availability_changed', 'is_deal',
            'alert_triggered', 'alert_type', 'alert_message',
        ]
        read_only_fields = ['id', 'created_at']


class MonitoringResultDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour les résultats de monitoring"""
    
    class Meta:
        model = MonitoringResult
        fields = [
            'id', 'product', 'task', 'monitored_at', 'created_at',
            'current_price', 'previous_price', 'price_changed',
            'price_change_amount', 'price_change_percentage',
            'currently_available', 'previously_available',
            'availability_changed', 'is_deal', 'screenshots',
            'extracted_data', 'alert_triggered', 'alert_type',
            'alert_message',
        ]
        read_only_fields = ['id', 'created_at']


class MonitoringStatsSerializer(serializers.ModelSerializer):
    """Serializer pour les statistiques de monitoring"""
    
    class Meta:
        model = MonitoringStats
        fields = [
            'id', 'date', 'total_tasks', 'completed_tasks', 'failed_tasks',
            'avg_execution_time', 'max_execution_time', 'min_execution_time',
            'price_changes_detected', 'availability_changes_detected',
            'alerts_triggered', 'high_priority_tasks', 'normal_priority_tasks',
            'low_priority_tasks', 'retailer_distribution',
        ]
        read_only_fields = ['id', 'date']
