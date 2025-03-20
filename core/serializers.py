from rest_framework import serializers

# Base serializer classes can be defined here
class BaseModelSerializer(serializers.ModelSerializer):
    """
    Base serializer that includes common functionality for all model serializers.
    """
    
    class Meta:
        abstract = True
