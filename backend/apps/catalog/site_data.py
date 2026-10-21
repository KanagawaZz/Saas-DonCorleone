"""
Public data the website needs to render menu, crusts, neighborhoods, hours and payment info.
The output follows the exact shape of the site's local files (cardapio.json, bairros.json,
site.config.js), so the site can swap its bundled data for the database without changing
any component. What the owner edits in the panel shows up on the site without a rebuild.
"""
from django.utils import timezone
from apps.catalog.models import Category, PizzaCrust, Product
from apps.delivery.models import DeliveryZone, OperatingHour, StoreSettings
from apps.promotions.models import Promotion

COMPRE_JUNTO_CATEGORY = "compre-junto"
CLOSED_DAY = {"abertura": "00:00", "fechamento": "00:00", "corte": "00:00"}


def _number(value):
    return float(value) if value is not None else None


def _photo(product: Product, request) -> str:
    if product.image:
        return request.build_absolute_uri(product.image.url) if request else product.image.url
    return product.photo_url


def _item(product: Product, request) -> dict:
    item = {
        "id": product.slug,
        "nome": product.name,
        "descricao": product.description,
        "preco": _number(product.base_price),
        "precoTexto": product.price_text,
        "destaque": product.is_highlight,
        "tag": product.tag,
        "foto": _photo(product, request),
    }
    if product.product_type == Product.ProductType.PIZZA:
        item["categoriaPreco"] = product.price_category
        item["precos"] = {size.size_id: _number(size.price) for size in product.size_prices.all()}
    for key, value in (product.extra_details or {}).items():
        if value not in (None, ""):
            item.setdefault(key, value)
    return item


def _site_promotion(tenant) -> dict:
    """
    The site's top banner promotion (siteConfig.promocao shape). The site applies it to every
    order automatically and sends its coupon, which the server validates again on checkout.
    """
    candidates = Promotion.objects.filter(
        tenant=tenant, is_active=True, show_top_banner=True,
        discount_type=Promotion.DiscountType.PERCENTAGE, registered_customers_only=False,
        min_order_value=0,
    ).exclude(coupon_code__isnull=True).exclude(coupon_code="").order_by("-created_at")
    for promo in candidates:
        valid, _ = promo.is_currently_valid()
        if valid:
            return {
                "ativa": True,
                "titulo": promo.title,
                "texto": promo.banner_text or promo.description,
                "inicio": promo.start_date.isoformat() if promo.start_date else None,
                "fim": promo.end_date.isoformat() if promo.end_date else None,
                "cupom": promo.coupon_code,
                "descontoPercentual": float(promo.discount_value),
            }
    return {"ativa": False, "titulo": "", "texto": "", "inicio": None, "fim": None, "cupom": None, "descontoPercentual": 0}


def build_site_data(tenant, request=None) -> dict:
    categories = (
        Category.objects.filter(tenant=tenant, is_active=True)
        .order_by("display_order", "name")
        .prefetch_related("products__size_prices")
    )
    cardapio = []
    for category in categories:
        products = [p for p in category.products.all() if p.is_available]
        products.sort(key=lambda p: (p.display_order, p.name))
        cardapio.append({
            "id": category.slug,
            "nome": category.name,
            "descricao": category.description,
            "itens": [_item(p, request) for p in products],
        })

    compre_junto = [
        {"id": p.slug, "preco": _number(p.base_price), "disponivel": p.is_available}
        for p in Product.objects.filter(tenant=tenant, category__slug=COMPRE_JUNTO_CATEGORY)
    ]

    bordas = [
        {
            "id": crust.slug,
            "nome": crust.name,
            "preco": _number(crust.price),
            "precoTexto": crust.price_text,
            "padrao": crust.is_default,
            "destaque": crust.is_highlight,
        }
        for crust in PizzaCrust.objects.filter(tenant=tenant, is_active=True).order_by("display_order", "price")
    ]

    bairros = [
        {"cidade": zone.city, "bairro": zone.neighborhood, "taxa": _number(zone.fee)}
        for zone in DeliveryZone.objects.filter(tenant=tenant, is_active=True).order_by("neighborhood")
    ]

    store = StoreSettings.objects.filter(tenant=tenant).first()
    today = (timezone.localdate().weekday() + 1) % 7  # site convention: 0=Sunday
    dias = []
    for hours in OperatingHour.objects.filter(tenant=tenant).order_by("weekday"):
        dia = {
            "dia": hours.weekday,
            "nome": hours.name,
            "abertura": hours.opening_time,
            "fechamento": hours.closing_time,
            "corte": hours.cutoff_time,
        }
        # The site has no "closed day" flag: a 00:00-00:00 window shows the store as closed
        if not hours.is_active or (store and store.emergency_closed and hours.weekday == today):
            dia.update(CLOSED_DAY)
        dias.append(dia)

    data = {
        "promocao": _site_promotion(tenant),
        "cardapio": {"categorias": cardapio},
        "compreJunto": compre_junto,
        "bordas": bordas,
        "bairros": bairros,
        "horario": {"dias": dias},
    }
    if store:
        data["pagamento"] = {
            "pedidoMinimo": _number(store.minimum_order),
            "pix": {
                "chave": store.pix_key,
                "tipo": store.pix_type,
                "titular": store.pix_holder,
                "avisoInstrucao": store.pix_instructions,
            },
        }
        data["operacional"] = {
            "tempoEntrega": store.delivery_time_text,
            "tempoRetirada": store.pickup_time_text,
        }
        data["fechamentoEmergencial"] = {
            "ativo": store.emergency_closed,
            "motivo": store.emergency_closed_reason,
        }
    return data
