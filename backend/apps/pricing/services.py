from decimal import Decimal
from apps.catalog.models import Product, PizzaCrust, ProductSizePrice


class PricingError(ValueError):
    """Raised when an order item cannot be priced from the catalog."""


def get_size_price(product: Product, size_id: str) -> ProductSizePrice:
    """Returns the catalog size row (price, name, max flavors) of a pizza flavor."""
    size = ProductSizePrice.objects.filter(product=product, size_id=(size_id or '').lower()).first()
    if not size:
        raise PricingError(f"O sabor {product.name} não está disponível no tamanho escolhido.")
    return size


def calculate_pizza_price(flavor_products: list[Product], size_id: str, crust: PizzaCrust = None) -> tuple[Decimal, ProductSizePrice]:
    """
    Calculates the pizza price from the catalog applying the highest-flavor-price rule
    ('sabor_mais_caro') plus the crust charge. Returns (unit_price, size row of the most
    expensive flavor).
    """
    if not flavor_products:
        raise PricingError("Escolha ao menos um sabor para a pizza.")

    sizes = [get_size_price(prod, size_id) for prod in flavor_products]
    reference = max(sizes, key=lambda s: s.price)

    max_flavors = min(s.max_flavors for s in sizes)
    if len(flavor_products) > max_flavors:
        raise PricingError(f"{reference.size_name} aceita no máximo {max_flavors} sabores.")

    crust_price = crust.price if crust else Decimal('0.00')
    return reference.price + crust_price, reference
