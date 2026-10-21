from django.contrib import admin
from .models import Promotion

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('title', 'coupon_code', 'discount_type', 'discount_value', 'min_order_value', 'registered_customers_only', 'start_date', 'end_date', 'show_top_banner', 'is_active', 'current_uses')
    list_filter = ('is_active', 'discount_type', 'registered_customers_only', 'show_top_banner')
    search_fields = ('title', 'coupon_code', 'description')
    list_editable = ('is_active', 'show_top_banner')
