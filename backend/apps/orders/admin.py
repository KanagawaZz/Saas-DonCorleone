from django.contrib import admin
from .models import Order, OrderItem, OrderItemFlavor, OrderStatusHistory

class OrderItemFlavorInline(admin.TabularInline):
    model = OrderItemFlavor
    extra = 0

class OrderItemInline(admin.StackedInline):
    model = OrderItem
    extra = 0

class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('status', 'notes', 'changed_by', 'created_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('readable_code', 'customer_name', 'customer_phone', 'fulfillment_mode', 'delivery_neighborhood', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'fulfillment_mode', 'payment_method', 'delivery_neighborhood', 'created_at')
    search_fields = ('readable_code', 'customer_name', 'customer_phone', 'delivery_street', 'delivery_neighborhood')
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    readonly_fields = ('readable_code', 'created_at', 'updated_at')
