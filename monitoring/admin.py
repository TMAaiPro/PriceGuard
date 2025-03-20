from django.contrib import admin
from django.utils.html import format_html
from .models import MonitoringTask, ProductMonitoringConfig, MonitoringResult, MonitoringStats


@admin.register(MonitoringTask)
class MonitoringTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'status', 'priority', 'scheduled_time', 'started_at', 'completed_at']
    list_filter = ['status', 'priority']
    search_fields = ['product__title', 'error_message']
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'completed_at', 'celery_task_id']
    raw_id_fields = ['product', 'creator']
    date_hierarchy = 'created_at'
    list_per_page = 50


@admin.register(ProductMonitoringConfig)
class ProductMonitoringConfigAdmin(admin.ModelAdmin):
    list_display = ['product', 'frequency', 'priority_score', 'active', 'last_monitored', 'next_scheduled']
    list_filter = ['active', 'frequency']
    search_fields = ['product__title']
    readonly_fields = ['created_at', 'updated_at', 'last_monitored', 'next_scheduled', 'priority_score']
    raw_id_fields = ['product']
    list_per_page = 50


@admin.register(MonitoringResult)
class MonitoringResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'monitored_at', 'current_price', 'price_changed', 'currently_available', 'alert_triggered']
    list_filter = ['price_changed', 'availability_changed', 'alert_triggered', 'is_deal']
    search_fields = ['product__title', 'alert_message']
    readonly_fields = ['created_at', 'monitored_at']
    raw_id_fields = ['product', 'task']
    date_hierarchy = 'monitored_at'
    list_per_page = 50


@admin.register(MonitoringStats)
class MonitoringStatsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_tasks', 'completed_tasks', 'failed_tasks', 'price_changes_detected', 'alerts_triggered']
    list_filter = ['date']
    readonly_fields = ['date']
    date_hierarchy = 'date'
