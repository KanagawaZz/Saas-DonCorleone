from django.contrib import admin
from .models import DeliveryZone, Employee, OperatingHour, SalaryAdvance, StoreSettings

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'phone', 'is_active', 'working_on', 'tenant')
    list_filter = ('role', 'is_active')
    search_fields = ('name', 'phone')

@admin.register(SalaryAdvance)
class SalaryAdvanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'amount', 'date', 'notes', 'created_by')
    list_filter = ('date',)
    search_fields = ('employee__name', 'notes')

@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ('neighborhood', 'city', 'fee', 'is_active', 'estimated_minutes')
    list_filter = ('city', 'is_active')
    search_fields = ('neighborhood', 'city')
    list_editable = ('fee', 'is_active')

@admin.register(OperatingHour)
class OperatingHourAdmin(admin.ModelAdmin):
    list_display = ('weekday', 'name', 'opening_time', 'closing_time', 'cutoff_time', 'is_active')
    list_editable = ('opening_time', 'closing_time', 'cutoff_time', 'is_active')

@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'minimum_order', 'pix_key', 'delivery_time_text', 'pickup_time_text', 'emergency_closed')
