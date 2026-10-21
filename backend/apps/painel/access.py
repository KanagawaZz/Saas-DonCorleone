from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from apps.core.tenancy import get_current_tenant


def painel_view(view):
    """
    Panel pages: requires a logged-in staff user (is_staff) and exposes the
    establishment as request.tenant so every query is filtered by it.
    """
    @login_required(login_url="painel:entrar")
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Acesso restrito à equipe da pizzaria.")
        request.tenant = get_current_tenant(request)
        if request.tenant is None:
            raise PermissionDenied("Nenhum estabelecimento configurado. Rode o comando import_legacy_data.")
        return view(request, *args, **kwargs)
    return wrapper
