from rest_framework import serializers
from .models import PriceInsight, PricePrediction, UserAnalytics
from products.serializers import ProductListSerializer

class PriceInsightSerializer(serializers.ModelSerializer):
    """Serializer for price insights"""
    product_details = ProductListSerializer(source='product', read_only=True)
    insight_type_display = serializers.CharField(source='get_insight_type_display', read_only=True)
    
    class Meta:
        model = PriceInsight
        fields = ('id', 'product', 'product_details', 'insight_type', 
                 'insight_type_display', 'content', 'data', 'created_at')
        read_only_fields = ('id', 'created_at')


class PricePredictionSerializer(serializers.ModelSerializer):
    """Serializer for price predictions"""
    product_details = ProductListSerializer(source='product', read_only=True)
    
    class Meta:
        model = PricePrediction
        fields = ('id', 'product', 'product_details', 'predicted_price', 
                 'prediction_date', 'confidence', 'model_used', 'accuracy', 
                 'features', 'created_at')
        read_only_fields = ('id', 'created_at')


class UserAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for user analytics events"""
    product_details = ProductListSerializer(source='product', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    
    class Meta:
        model = UserAnalytics
        fields = ('id', 'user', 'action_type', 'action_type_display', 'product', 
                 'product_details', 'session_id', 'ip_address', 'user_agent', 
                 'referrer', 'duration', 'details', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def create(self, validated_data):
        """Create and return a new analytics event"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class UserAnalyticsEventSerializer(serializers.ModelSerializer):
    """Simplified serializer for tracking user events"""
    class Meta:
        model = UserAnalytics
        fields = ('action_type', 'product', 'session_id', 'referrer', 'duration', 'details')
