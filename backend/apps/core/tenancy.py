from apps.tenants.models import Tenant


def get_current_tenant(request=None) -> Tenant | None:
    """
    Establishment the request belongs to. Staff users carry their tenant; single-store
    deployments (today: Don Corleone) fall back to the only tenant.
    """
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and getattr(user, "tenant_id", None):
        return user.tenant
    return Tenant.objects.order_by("created_at").first()
