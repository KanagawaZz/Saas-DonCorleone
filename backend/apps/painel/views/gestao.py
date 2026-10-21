"""Delivery zones, store settings, customers and promotions pages."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Max, Q, Sum
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from apps.accounts.models import CustomerProfile
from apps.delivery.models import DeliveryZone, OperatingHour, StoreSettings
from apps.orders.models import Order
from apps.promotions.models import Promotion
from ..access import painel_view
from ..forms import DeliveryZoneFormSet, OperatingHourFormSet, PromotionForm, StoreSettingsForm, WEEKDAYS
from .common import nav_context

DAY_NAMES = ["Domingo", "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]


# ---------------------------------------------------------------- Entregas

@painel_view
def entregas(request):
    queryset = DeliveryZone.objects.filter(tenant=request.tenant).order_by("city", "neighborhood")
    busca = request.GET.get("busca", "").strip()
    if busca:
        queryset = queryset.filter(neighborhood__icontains=busca)

    if request.method == "POST":
        formset = DeliveryZoneFormSet(request.POST, queryset=queryset, tenant=request.tenant, prefix="bairros")
        if formset.is_valid():
            formset.save()
            messages.success(request, "Bairros e taxas salvos. O site já mostra os novos valores.")
            return redirect(request.get_full_path())
    else:
        formset = DeliveryZoneFormSet(queryset=queryset, tenant=request.tenant, prefix="bairros")

    context = {
        **nav_context(request, "entregas"),
        "formset": formset,
        "busca": busca,
        "qtd_ativos": DeliveryZone.objects.filter(tenant=request.tenant, is_active=True).count(),
    }
    return render(request, "painel/entregas.html", context)


# ---------------------------------------------------------------- Configurações

@painel_view
def configuracoes(request):
    tenant = request.tenant
    store, _ = StoreSettings.objects.get_or_create(tenant=tenant)
    for weekday, name in enumerate(DAY_NAMES):
        OperatingHour.objects.get_or_create(tenant=tenant, weekday=weekday, defaults={"name": name})
    hours = OperatingHour.objects.filter(tenant=tenant).order_by("weekday")

    if request.method == "POST":
        form = StoreSettingsForm(request.POST, instance=store)
        formset = OperatingHourFormSet(request.POST, queryset=hours, prefix="horarios")
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, "Configurações salvas. O site já usa os novos valores.")
            return redirect("painel:configuracoes")
    else:
        form = StoreSettingsForm(instance=store)
        formset = OperatingHourFormSet(queryset=hours, prefix="horarios")

    return render(request, "painel/configuracoes.html", {
        **nav_context(request, "configuracoes"), "form": form, "formset": formset,
    })


# ---------------------------------------------------------------- Clientes

@painel_view
def clientes(request):
    """Everyone who ordered (grouped by WhatsApp), with Clube VIP data when registered."""
    tenant = request.tenant
    orders = Order.objects.filter(tenant=tenant).exclude(customer_phone="")
    busca = request.GET.get("busca", "").strip()
    if busca:
        digits = "".join(filter(str.isdigit, busca))
        query = Q(customer_name__icontains=busca)
        if len(digits) >= 4:
            query |= Q(customer_phone__contains=digits)
        orders = orders.filter(query)

    rows = (
        orders.exclude(status=Order.Status.CANCELADO)
        .values("customer_phone")
        .annotate(pedidos=Count("id"), total=Sum("total_amount"), ultimo=Max("created_at"))
        .order_by("-ultimo")
    )
    page = Paginator(rows, 30).get_page(request.GET.get("pagina"))

    phones = [row["customer_phone"] for row in page]
    names = {}
    for phone, name in orders.filter(customer_phone__in=phones).order_by("created_at").values_list("customer_phone", "customer_name"):
        names[phone] = name  # most recent name wins
    profiles = {p.whatsapp: p for p in CustomerProfile.objects.filter(tenant=tenant, whatsapp__in=phones)}
    for row in page:
        row["nome"] = names.get(row["customer_phone"], "")
        row["perfil"] = profiles.get(row["customer_phone"])

    vip_profiles = CustomerProfile.objects.filter(tenant=tenant).select_related("user").order_by("-created_at")
    context = {
        **nav_context(request, "clientes"),
        "pagina": page,
        "busca": busca,
        "aba": request.GET.get("aba", "todos"),
        "cadastrados": vip_profiles[:200],
        "qtd_cadastrados": vip_profiles.count(),
        "qtd_vip": vip_profiles.filter(is_vip=True).count(),
    }
    return render(request, "painel/clientes/lista.html", context)


@painel_view
def cliente_detalhe(request, telefone):
    tenant = request.tenant
    digits = "".join(filter(str.isdigit, telefone))
    orders = Order.objects.filter(tenant=tenant, customer_phone=digits).order_by("-created_at")
    profile = CustomerProfile.objects.filter(tenant=tenant, whatsapp=digits).select_related("user").first()
    if profile:
        orders = Order.objects.filter(tenant=tenant).filter(
            Q(customer_phone=digits) | Q(customer_user=profile.user)
        ).order_by("-created_at")
    if not orders.exists() and not profile:
        raise Http404("Cliente não encontrado.")

    valid = orders.exclude(status=Order.Status.CANCELADO)
    summary = valid.aggregate(total=Sum("total_amount"), qtd=Count("id"))
    last = orders.first()
    context = {
        **nav_context(request, "clientes"),
        "telefone": digits,
        "nome": (last.customer_name if last else "") or (profile.user.get_full_name() if profile else ""),
        "perfil": profile,
        "pedidos": orders[:50],
        "total": summary["total"],
        "qtd": summary["qtd"],
        "ticket": (summary["total"] / summary["qtd"]) if summary["qtd"] else None,
        "ultimo_endereco": orders.filter(fulfillment_mode=Order.FulfillmentMode.DELIVERY).first(),
    }
    return render(request, "painel/clientes/detalhe.html", context)


@painel_view
def cliente_alternar_vip(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    profile = get_object_or_404(CustomerProfile, pk=pk, tenant=request.tenant)
    profile.is_vip = not profile.is_vip
    profile.save(update_fields=["is_vip", "updated_at"])
    messages.success(request, f"VIP {'ativado' if profile.is_vip else 'removido'}.")
    return redirect("painel:cliente", telefone=profile.whatsapp)


# ---------------------------------------------------------------- Promoções

@painel_view
def promocoes(request):
    promotions = Promotion.objects.filter(tenant=request.tenant).order_by("-is_active", "-created_at")
    weekday_names = dict(WEEKDAYS)
    for promo in promotions:
        promo.valida_agora, promo.motivo = promo.is_currently_valid()
        promo.dias = ", ".join(weekday_names.get(d, "?") for d in promo.weekdays_allowed) or "Todos os dias"
    return render(request, "painel/promocoes/lista.html", {**nav_context(request, "promocoes"), "promocoes": promotions})


def _promotion_form_page(request, promotion=None):
    is_new = promotion is None
    if request.method == "POST":
        form = PromotionForm(request.POST, instance=promotion)
        if form.is_valid():
            promo = form.save(commit=False)
            promo.tenant = request.tenant
            promo.save()
            messages.success(request, f"Promoção \"{promo.title}\" {'criada' if is_new else 'salva'}.")
            return redirect("painel:promocoes")
    else:
        form = PromotionForm(instance=promotion)
    return render(request, "painel/promocoes/form.html", {
        **nav_context(request, "promocoes"), "form": form, "promocao": promotion,
    })


@painel_view
def promocao_nova(request):
    return _promotion_form_page(request)


@painel_view
def promocao_editar(request, pk):
    return _promotion_form_page(request, get_object_or_404(Promotion, pk=pk, tenant=request.tenant))


@painel_view
def promocao_alternar(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    promo = get_object_or_404(Promotion, pk=pk, tenant=request.tenant)
    promo.is_active = not promo.is_active
    promo.save(update_fields=["is_active", "updated_at"])
    messages.success(request, f"\"{promo.title}\" {'ativada' if promo.is_active else 'pausada'}.")
    return redirect("painel:promocoes")
