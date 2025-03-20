from django.contrib import admin
from django.utils.html import format_html
from .models import Retailer, Product, PricePoint, Screenshot, ScrapingTask

@admin.register(Retailer)
class RetailerAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'domain')
    ordering = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'retailer', 'current_price', 'currency', 'last_checked', 'is_available')
    list_filter = ('retailer', 'is_available', 'currency')
    search_fields = ('title', 'url', 'sku')
    ordering = ('-last_checked',)
    readonly_fields = ('image_preview', 'price_history')
    fieldsets = (
        ('Informations de base', {
            'fields': ('url', 'retailer', 'title', 'sku')
        }),
        ('Prix', {
            'fields': ('current_price', 'currency', 'lowest_price', 'highest_price')
        }),
        ('Détails', {
            'fields': ('description', 'image_url', 'image_preview', 'is_available', 'last_checked')
        }),
        ('Historique', {
            'fields': ('price_history',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 200px;" />', obj.image_url)
        return "Pas d'image"
    image_preview.short_description = 'Aperçu image'
    
    def price_history(self, obj):
        prices = obj.price_points.all()[:10]
        if not prices:
            return "Pas d'historique de prix"
        
        html = '<table style="width:100%"><tr><th>Date</th><th>Prix</th><th>Disponible</th><th>Promo</th></tr>'
        for price in prices:
            html += f'<tr><td>{price.timestamp.strftime("%d/%m/%Y %H:%M")}</td><td>{price.price} {price.currency}</td>'
            html += f'<td>{"Oui" if price.is_available else "Non"}</td><td>{"Oui" if price.is_deal else "Non"}</td></tr>'
        html += '</table>'
        
        html += f'<a href="/admin/scraper/pricepoint/?product__id__exact={obj.id}">Voir tout l\'historique</a>'
        
        return format_html(html)
    price_history.short_description = 'Historique des prix récents'

@admin.register(PricePoint)
class PricePointAdmin(admin.ModelAdmin):
    list_display = ('product_title', 'price', 'currency', 'timestamp', 'is_available', 'is_deal', 'source')
    list_filter = ('is_available', 'is_deal', 'source', 'currency')
    search_fields = ('product__title',)
    ordering = ('-timestamp',)
    raw_id_fields = ('product',)
    
    def product_title(self, obj):
        return obj.product.title
    product_title.short_description = 'Produit'
    product_title.admin_order_field = 'product__title'

@admin.register(Screenshot)
class ScreenshotAdmin(admin.ModelAdmin):
    list_display = ('product_title', 'type', 'timestamp', 'screenshot_preview')
    list_filter = ('type',)
    search_fields = ('product__title',)
    ordering = ('-timestamp',)
    raw_id_fields = ('product', 'price_point')
    
    def product_title(self, obj):
        return obj.product.title
    product_title.short_description = 'Produit'
    product_title.admin_order_field = 'product__title'
    
    def screenshot_preview(self, obj):
        return format_html('<img src="{}" style="max-width: 100px; max-height: 100px;" />', obj.image.url)
    screenshot_preview.short_description = 'Aperçu'

@admin.register(ScrapingTask)
class ScrapingTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'product_or_url', 'status', 'priority', 'created_at', 'completed_at')
    list_filter = ('status', 'priority')
    search_fields = ('product__title', 'url')
    ordering = ('priority', 'created_at')
    actions = ['mark_as_pending']
    
    def product_or_url(self, obj):
        if obj.product:
            return obj.product.title
        return obj.url
    product_or_url.short_description = 'Produit ou URL'
    
    def mark_as_pending(self, request, queryset):
        queryset.update(status='pending', started_at=None, completed_at=None, error_message=None)
        self.message_user(request, f"{queryset.count()} tâches remises en attente.")
    mark_as_pending.short_description = "Marquer les tâches sélectionnées comme en attente"
