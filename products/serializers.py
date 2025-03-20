from rest_framework import serializers
from .models import Product, Retailer, Category, ProductPrice, ProductImage, UserProduct

class CategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories"""
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'parent')
        read_only_fields = ('slug',)


class RetailerSerializer(serializers.ModelSerializer):
    """Serializer for retailers"""
    class Meta:
        model = Retailer
        fields = ('id', 'name', 'website', 'logo_url', 'is_active')


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images"""
    class Meta:
        model = ProductImage
        fields = ('id', 'product', 'image_url', 'alt_text', 'order')
        read_only_fields = ('id',)


class ProductPriceSerializer(serializers.ModelSerializer):
    """Serializer for product price history"""
    class Meta:
        model = ProductPrice
        fields = ('id', 'product', 'price', 'timestamp')
        read_only_fields = ('id', 'timestamp')


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for products"""
    images = ProductImageSerializer(many=True, read_only=True)
    retailer_detail = RetailerSerializer(source='retailer', read_only=True)
    categories_detail = CategorySerializer(source='categories', many=True, read_only=True)
    price_history = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ('id', 'name', 'slug', 'description', 'sku', 'upc', 'url', 
                 'image_url', 'retailer', 'retailer_detail', 'categories', 
                 'categories_detail', 'current_price', 'base_price', 'currency', 
                 'is_active', 'last_checked', 'images', 'price_history', 'created_at', 'updated_at')
        read_only_fields = ('id', 'slug', 'last_checked', 'created_at', 'updated_at')
    
    def get_price_history(self, obj):
        """Return the price history for the product, limited to recent entries"""
        # Limit to last 30 entries to avoid overwhelming the API
        prices = obj.prices.all()[:30]
        return ProductPriceSerializer(prices, many=True).data


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for product list view with fewer fields"""
    retailer_name = serializers.CharField(source='retailer.name', read_only=True)
    
    class Meta:
        model = Product
        fields = ('id', 'name', 'slug', 'image_url', 'current_price', 
                 'base_price', 'currency', 'retailer_name', 'last_checked')
        read_only_fields = ('id', 'slug', 'last_checked')


class UserProductSerializer(serializers.ModelSerializer):
    """Serializer for user tracked products"""
    product_detail = ProductSerializer(source='product', read_only=True)
    
    class Meta:
        model = UserProduct
        fields = ('id', 'user', 'product', 'product_detail', 'target_price', 
                 'notify_price_drop', 'notify_availability', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
        extra_kwargs = {
            'product': {'write_only': True}
        }
    
    def create(self, validated_data):
        """Create and return a new user product tracking"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
