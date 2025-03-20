from rest_framework import serializers
from .models import Alert, AlertType, AlertConfiguration, AlertAction
from products.serializers import ProductListSerializer

class AlertTypeSerializer(serializers.ModelSerializer):
    """Serializer for alert types"""
    class Meta:
        model = AlertType
        fields = ('id', 'name', 'description', 'is_active')
        read_only_fields = ('id',)


class AlertConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for user alert configurations"""
    alert_type_details = AlertTypeSerializer(source='alert_type', read_only=True)
    
    class Meta:
        model = AlertConfiguration
        fields = ('id', 'user', 'alert_type', 'alert_type_details', 
                 'is_active', 'threshold', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        """Create and return a new alert configuration"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AlertActionSerializer(serializers.ModelSerializer):
    """Serializer for alert actions"""
    class Meta:
        model = AlertAction
        fields = ('id', 'alert', 'action', 'timestamp', 'details')
        read_only_fields = ('id', 'timestamp')


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for alerts"""
    alert_type_details = AlertTypeSerializer(source='alert_type', read_only=True)
    product_details = ProductListSerializer(source='product', read_only=True)
    actions = AlertActionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Alert
        fields = ('id', 'user', 'product', 'product_details', 'alert_type', 
                 'alert_type_details', 'status', 'message', 'details', 
                 'created_at', 'updated_at', 'actions')
        read_only_fields = ('id', 'user', 'product', 'alert_type', 'message', 
                          'created_at', 'updated_at')
    
    def update(self, instance, validated_data):
        """Update alert with action if status changes"""
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        # Update the alert
        instance = super().update(instance, validated_data)
        
        # If status changed, create an action record
        if old_status != new_status:
            action_map = {
                'read': 'view',
                'dismissed': 'dismiss',
                'actioned': 'click',
            }
            
            if new_status in action_map:
                AlertAction.objects.create(
                    alert=instance,
                    action=action_map[new_status]
                )
        
        return instance


class AlertListSerializer(serializers.ModelSerializer):
    """Simplified serializer for alert listings"""
    alert_type_name = serializers.CharField(source='alert_type.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.URLField(source='product.image_url', read_only=True)
    
    class Meta:
        model = Alert
        fields = ('id', 'alert_type_name', 'product_name', 'product_image', 
                 'status', 'message', 'created_at')
        read_only_fields = ('id', 'alert_type_name', 'product_name', 
                          'product_image', 'message', 'created_at')
