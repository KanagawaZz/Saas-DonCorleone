from django.contrib import admin
from .models import Tenant

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'phone', 'whatsapp_number', 'is_active', 'created_at')
    search_fields = ('name', 'city')
