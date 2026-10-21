from rest_framework import serializers
from .models import Promotion

class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = [
            'id', 'title', 'description', 'coupon_code', 'discount_type',
            'discount_value', 'min_order_value', 'registered_customers_only',
            'weekdays_allowed', 'start_date', 'end_date', 'is_active',
            'show_top_banner', 'banner_text', 'max_uses', 'current_uses'
        ]

class ValidateCouponSerializer(serializers.Serializer):
    coupon_code = serializers.CharField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
