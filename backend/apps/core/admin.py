from django.contrib import admin
from .models import ErrorEvent


@admin.register(ErrorEvent)
class ErrorEventAdmin(admin.ModelAdmin):
    """Read-only: occurrences are created by the system; support only marks them as resolved."""
    list_display = ("code", "occurred_at", "area", "method", "path", "exception_type", "user_label", "resolved")
    list_filter = ("resolved", "area", "exception_type")
    search_fields = ("code", "path", "exception_type", "message", "user_label")
    list_editable = ("resolved",)
    readonly_fields = [f.name for f in ErrorEvent._meta.fields if f.name != "resolved"]

    def has_add_permission(self, request):
        return False

    def has_module_permission(self, request):
        return request.user.is_superuser  # support only: data may include customers' personal details
