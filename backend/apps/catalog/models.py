from django.db import models
from apps.core.models import TimeStampedModel
from apps.tenants.models import Tenant

class Category(TimeStampedModel):
    """Product category (e.g. Pizzas Salgadas, Pizzas Doces, Combos, Esfihas, etc.)."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="categories", verbose_name="Estabelecimento")
    name = models.CharField(max_length=100, verbose_name="Nome da Categoria")
    slug = models.SlugField(max_length=100, verbose_name="Slug / Identificador")
    description = models.TextField(blank=True, verbose_name="Descrição")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Ordem de Exibição")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["display_order", "name"]
        unique_together = ("tenant", "slug")

    def __str__(self):
        return self.name

class Product(TimeStampedModel):
    """
    Individual item in the catalog.
    Can be a customizable pizza base, a simple item (esfiha, drink, dessert), or a combo.
    """
    class ProductType(models.TextChoices):
        PIZZA = 'pizza', 'Pizza Artesanal Personalizável'
        SIMPLE = 'simple', 'Produto Simples (Esfiha, Bebida, Sobremesa)'
        COMBO = 'combo', 'Combo Promocional'
        KIT_ESFIHA = 'kit_esfiha', 'Kit de Esfihas'

    class PriceCategory(models.TextChoices):
        TRADITIONAL = 'tradicional', 'Tradicional'
        PREMIUM = 'premium', 'Premium / Especial'
        DOCE = 'doce', 'Doce'
        ESPECIAL = 'especial', 'Especial da Casa'

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="products", verbose_name="Estabelecimento")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products", verbose_name="Categoria")
    name = models.CharField(max_length=150, verbose_name="Nome do Produto")
    slug = models.SlugField(max_length=150, verbose_name="Slug / Identificador")
    description = models.TextField(blank=True, verbose_name="Descrição / Ingredientes")
    product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.SIMPLE, verbose_name="Tipo de Produto")
    price_category = models.CharField(max_length=20, choices=PriceCategory.choices, default=PriceCategory.TRADITIONAL, verbose_name="Categoria de Preço")
    
    # Base price (for simple products, or starting price for pizzas)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Preço Base (R$)")
    price_text = models.CharField(max_length=50, blank=True, verbose_name="Texto de Preço (ex: A partir de R$ 45,90)")
    
    # Marketing and badges
    tag = models.CharField(max_length=50, blank=True, verbose_name="Badge / Tag (ex: Assinatura, Mais Pedida)")
    is_highlight = models.BooleanField(default=False, verbose_name="Destaque na vitrine")
    photo_url = models.CharField(max_length=255, blank=True, verbose_name="URL da Foto")
    image = models.ImageField(upload_to="catalog/", null=True, blank=True, verbose_name="Upload de Imagem")
    
    # Availability toggle for instant owner control
    is_available = models.BooleanField(default=True, verbose_name="Disponível para Pedidos")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Ordem de Exibição")

    # Extra data (e.g. units, volume, distribution)
    extra_details = models.JSONField(default=dict, blank=True, verbose_name="Detalhes Extras (unidades, volume)")

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["display_order", "name"]
        unique_together = ("tenant", "slug")

    def __str__(self):
        return f"{self.name} ({self.get_product_type_display()})"

    @property
    def effective_image_url(self):
        if self.image:
            return self.image.url
        return self.photo_url or "/images/cardapio/calabresa-artesanal.webp"

class ProductSizePrice(TimeStampedModel):
    """Configures pricing by size for pizzas (Pequena, Média, Grande)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="size_prices", verbose_name="Produto")
    size_id = models.CharField(max_length=30, verbose_name="ID do Tamanho (pequena, media, grande)")
    size_name = models.CharField(max_length=50, verbose_name="Nome do Tamanho (ex: Pizza Grande 35cm)")
    slices = models.PositiveIntegerField(default=8, verbose_name="Fatias")
    max_flavors = models.PositiveIntegerField(default=3, verbose_name="Máximo de Sabores")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço (R$)")

    class Meta:
        verbose_name = "Preço por Tamanho"
        verbose_name_plural = "Preços por Tamanho"
        unique_together = ("product", "size_id")

    def __str__(self):
        return f"{self.product.name} - {self.size_name}: R$ {self.price}"

class PizzaCrust(TimeStampedModel):
    """Stuffed crust options (Catupiry, Cheddar, etc.)."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="crusts", verbose_name="Estabelecimento")
    name = models.CharField(max_length=100, verbose_name="Nome da Borda")
    slug = models.SlugField(max_length=100, verbose_name="Slug")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Preço Adicional (R$)")
    price_text = models.CharField(max_length=50, default="Sem adicional", verbose_name="Texto de Preço")
    is_default = models.BooleanField(default=False, verbose_name="Opção Padrão (Sem Borda)")
    is_highlight = models.BooleanField(default=False, verbose_name="Destaque / Grátis")
    is_active = models.BooleanField(default=True, verbose_name="Disponível")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Ordem")

    class Meta:
        verbose_name = "Borda de Pizza"
        verbose_name_plural = "Bordas de Pizza"
        ordering = ["display_order", "price"]

    def __str__(self):
        return f"{self.name} (+R$ {self.price})"
