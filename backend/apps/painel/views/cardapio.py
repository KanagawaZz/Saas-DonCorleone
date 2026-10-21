from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.forms import inlineformset_factory
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from apps.catalog.models import Category, PizzaCrust, Product, ProductSizePrice
from ..access import painel_view
from ..forms import CategoryFormSet, CrustFormSet, ProductForm, SizePriceForm, SizePriceFormSet
from .common import nav_context

DEFAULT_PIZZA_SIZES = [
    {"size_id": "pequena", "size_name": "Pizza Pequena (25cm)", "slices": 4, "max_flavors": 2},
    {"size_id": "media", "size_name": "Pizza Média (30cm)", "slices": 6, "max_flavors": 2},
    {"size_id": "grande", "size_name": "Pizza Grande (35cm)", "slices": 8, "max_flavors": 3},
]
NewProductSizesFormSet = inlineformset_factory(
    Product, ProductSizePrice, form=SizePriceForm, extra=len(DEFAULT_PIZZA_SIZES), can_delete=True,
)


@painel_view
def lista(request):
    tenant = request.tenant
    products = Product.objects.filter(tenant=tenant).select_related("category").prefetch_related("size_prices")

    busca = request.GET.get("busca", "").strip()
    if busca:
        products = products.filter(Q(name__icontains=busca) | Q(description__icontains=busca))
    categoria = request.GET.get("categoria", "")
    if categoria:
        products = products.filter(category__slug=categoria)
    if request.GET.get("esgotados"):
        products = products.filter(is_available=False)

    categories = Category.objects.filter(tenant=tenant).order_by("display_order", "name")
    grouped = []
    for category in categories:
        items = sorted((p for p in products if p.category_id == category.id), key=lambda p: (p.display_order, p.name))
        if items:
            for p in items:
                p.precos_tamanho = sorted(p.size_prices.all(), key=lambda s: s.price)
            grouped.append({"categoria": category, "produtos": items})

    context = {
        **nav_context(request, "cardapio"),
        "grupos": grouped,
        "categorias": categories,
        "filtros": {"busca": busca, "categoria": categoria, "esgotados": bool(request.GET.get("esgotados"))},
        "qtd_esgotados": Product.objects.filter(tenant=tenant, is_available=False).count(),
    }
    return render(request, "painel/cardapio/lista.html", context)


@painel_view
def alternar_disponibilidade(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    product = get_object_or_404(Product, pk=pk, tenant=request.tenant)
    product.is_available = not product.is_available
    product.save(update_fields=["is_available", "updated_at"])
    if product.is_available:
        messages.success(request, f"{product.name} voltou ao cardápio.")
    else:
        messages.success(request, f"{product.name} marcado como esgotado: some do site até você reativar.")
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("painel:cardapio")


def _product_form_page(request, product=None):
    tenant = request.tenant
    is_new = product is None
    product = product or Product(tenant=tenant)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product, tenant=tenant)
        sizes = SizePriceFormSet(request.POST, instance=product, prefix="tamanhos")
        is_pizza = request.POST.get("product_type") == Product.ProductType.PIZZA
        if form.is_valid() and (not is_pizza or sizes.is_valid()):
            if is_pizza and not any(
                f.cleaned_data and not f.cleaned_data.get("DELETE") for f in sizes.forms
            ):
                form.add_error(None, "Uma pizza precisa de pelo menos um tamanho com preço.")
            else:
                with transaction.atomic():
                    saved = form.save()
                    if is_pizza:
                        sizes.instance = saved
                        sizes.save()
                messages.success(request, f"{saved.name} {'criado' if is_new else 'salvo'}.")
                return redirect("painel:cardapio")
    else:
        initial = {}
        if is_new:
            initial = {"category": request.GET.get("categoria_id"), "is_available": True}
        form = ProductForm(instance=product, tenant=tenant, initial=initial)
        if is_new or not product.size_prices.exists():
            # Pre-filled P/M/G rows: the owner only types the prices
            sizes = NewProductSizesFormSet(instance=product, prefix="tamanhos", initial=DEFAULT_PIZZA_SIZES)
        else:
            sizes = SizePriceFormSet(instance=product, prefix="tamanhos")

    context = {
        **nav_context(request, "cardapio"),
        "form": form,
        "tamanhos": sizes,
        "produto": None if is_new else product,
    }
    return render(request, "painel/cardapio/produto_form.html", context)


@painel_view
def produto_novo(request):
    return _product_form_page(request)


@painel_view
def produto_editar(request, pk):
    return _product_form_page(request, get_object_or_404(Product, pk=pk, tenant=request.tenant))


@painel_view
def bordas(request):
    queryset = PizzaCrust.objects.filter(tenant=request.tenant).order_by("display_order", "price")
    if request.method == "POST":
        formset = CrustFormSet(request.POST, queryset=queryset, tenant=request.tenant, prefix="bordas")
        if formset.is_valid():
            formset.save()
            messages.success(request, "Bordas salvas.")
            return redirect("painel:bordas")
    else:
        formset = CrustFormSet(queryset=queryset, tenant=request.tenant, prefix="bordas")
    return render(request, "painel/cardapio/bordas.html", {**nav_context(request, "cardapio"), "formset": formset})


@painel_view
def categorias(request):
    queryset = Category.objects.filter(tenant=request.tenant).order_by("display_order", "name")
    if request.method == "POST":
        formset = CategoryFormSet(request.POST, queryset=queryset, prefix="categorias")
        if formset.is_valid():
            formset.save()
            messages.success(request, "Categorias salvas.")
            return redirect("painel:categorias")
    else:
        formset = CategoryFormSet(queryset=queryset, prefix="categorias")
    return render(request, "painel/cardapio/categorias.html", {**nav_context(request, "cardapio"), "formset": formset})
