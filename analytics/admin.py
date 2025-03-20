from django.contrib import admin
from .models import PriceInsight, PricePrediction, UserAnalytics

@admin.register(PriceInsight)
class PriceInsightAdmin(admin.ModelAdmin):
    list_display = ('product', 'insight_type', 'created_at')
    list_filter = ('insight_type', 'created_at')
    search_fields = ('product__name',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

@admin.register(PricePrediction)
class PricePredictionAdmin(admin.ModelAdmin):
    list_display = ('product', 'predicted_price', 'prediction_date', 'accuracy', 'created_at')
    list_filter = ('prediction_date', 'created_at')
    search_fields = ('product__name',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

@admin.register(UserAnalytics)
class UserAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_type', 'created_at')
    list_filter = ('action_type', 'created_at')
    search_fields = ('user__email',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
