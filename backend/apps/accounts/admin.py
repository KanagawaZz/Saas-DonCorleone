from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, CustomerProfile

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'first_name', 'phone', 'role', 'tenant', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active', 'tenant')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações Operacionais Don Corleone', {'fields': ('role', 'phone', 'tenant')}),
    )

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'whatsapp', 'default_address_neighborhood', 'is_vip', 'total_orders_count', 'total_spent')
    list_filter = ('is_vip', 'default_address_neighborhood')
    search_fields = ('user__first_name', 'user__username', 'whatsapp', 'default_address_neighborhood')
