from django.contrib import admin
from .models import Product, Retailer, Category, ProductPrice, ProductImage

class ProductPriceInline(admin.TabularInline):
    model = ProductPrice
    extra = 0
    readonly_fields = ('timestamp',)
    
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'current_price', 'base_price', 'retailer', 'is_active', 'last_checked')
    list_filter = ('retailer', 'is_active', 'categories')
    search_fields = ('name', 'description', 'sku', 'upc')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductPriceInline, ProductImageInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'retailer')
        }),
        ('Product Information', {
            'fields': ('sku', 'upc', 'url', 'image_url', 'categories')
        }),
        ('Pricing', {
            'fields': ('current_price', 'base_price', 'currency')
        }),
        ('Status', {
            'fields': ('is_active', 'last_checked')
        }),
    )

@admin.register(Retailer)
class RetailerAdmin(admin.ModelAdmin):
    list_display = ('name', 'website', 'is_active')
    search_fields = ('name', 'website')
    list_filter = ('is_active',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    list_filter = ('parent',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(ProductPrice)
class ProductPriceAdmin(admin.ModelAdmin):
    list_display = ('product', 'price', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('product__name',)
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)
