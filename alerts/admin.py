from django.contrib import admin
from .models import Alert, AlertType, AlertConfiguration, AlertAction

@admin.register(AlertType)
class AlertTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active')
    search_fields = ('name', 'description')
    list_filter = ('is_active',)

@admin.register(AlertConfiguration)
class AlertConfigurationAdmin(admin.ModelAdmin):
    list_display = ('user', 'alert_type', 'is_active', 'created_at')
    list_filter = ('alert_type', 'is_active')
    search_fields = ('user__email',)
    date_hierarchy = 'created_at'

class AlertActionInline(admin.TabularInline):
    model = AlertAction
    extra = 1

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'alert_type', 'status', 'created_at')
    list_filter = ('alert_type', 'status', 'created_at')
    search_fields = ('user__email', 'product__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('user', 'product', 'alert_type', 'message', 'created_at')
    inlines = [AlertActionInline]
    
    def has_add_permission(self, request):
        return False
