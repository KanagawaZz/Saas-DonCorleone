from rest_framework import serializers
from .models import DeliveryZone, OperatingHour, StoreSettings

class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = ['id', 'city', 'neighborhood', 'fee', 'is_active', 'estimated_minutes']

class OperatingHourSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatingHour
        fields = ['weekday', 'name', 'opening_time', 'closing_time', 'cutoff_time', 'is_active']

class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        fields = [
            'minimum_order', 'pix_key', 'pix_type', 'pix_holder', 'pix_instructions',
            'delivery_time_text', 'pickup_time_text', 'emergency_closed', 'emergency_closed_reason'
        ]

class PublicDeliveryConfigSerializer(serializers.Serializer):
    bairros = DeliveryZoneSerializer(many=True)
    horarios = OperatingHourSerializer(many=True)
    configuracoes = StoreSettingsSerializer()
