import random
from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.tenants.models import Tenant
from apps.accounts.models import User
from apps.catalog.models import Product, PizzaCrust

CHARSET_SEGURO = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'

def generate_order_code() -> str:
    """Generates unique readable code DC-DDMM-XXX in Cuiabá timezone."""
    now = timezone.localtime()
    day_str = now.strftime('%d')
    month_str = now.strftime('%m')
    rand_part = ''.join(random.choices(CHARSET_SEGURO, k=3))
    return f"DC-{day_str}{month_str}-{rand_part}"

class Order(TimeStampedModel):
    """Primary Order model for Don Corleone."""
    class Status(models.TextChoices):
        NOVO = 'NOVO', 'Pendente'
        # Legacy: confirming now moves the order straight to PREPARO
        CONFIRMADO = 'CONFIRMADO', 'Confirmado'
        PREPARO = 'PREPARO', 'Em preparo'
        SAIU_PARA_ENTREGA = 'SAIU_PARA_ENTREGA', 'Enviado'
        PRONTO_RETIRADA = 'PRONTO_RETIRADA', 'Pronto para retirada'
        CONCLUIDO = 'CONCLUIDO', 'Entregue / Concluído'
        CANCELADO = 'CANCELADO', 'Cancelado'

    class FulfillmentMode(models.TextChoices):
        DELIVERY = 'entrega', 'Entrega (Delivery)'
        PICKUP = 'retirada', 'Retirada no Balcão'

    class PaymentMethod(models.TextChoices):
        PIX = 'pix', 'PIX'
        DINHEIRO = 'dinheiro', 'Dinheiro'
        CARTAO_CREDITO = 'cartao_credito', 'Cartão de Crédito'
        CARTAO_DEBITO = 'cartao_debito', 'Cartão de Débito'

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="orders", verbose_name="Estabelecimento")
    readable_code = models.CharField(max_length=20, unique=True, default=generate_order_code, verbose_name="Código do Pedido")
    idempotency_key = models.CharField(max_length=64, blank=True, null=True, db_index=True, verbose_name="Chave de Idempotência")
    
    # Customer
    customer_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders", verbose_name="Usuário do Cliente")
    customer_name = models.CharField(max_length=150, verbose_name="Nome do Cliente")
    customer_phone = models.CharField(max_length=30, verbose_name="WhatsApp do Cliente")
    
    # Fulfillment & Address
    fulfillment_mode = models.CharField(max_length=20, choices=FulfillmentMode.choices, default=FulfillmentMode.DELIVERY, verbose_name="Modalidade")
    delivery_street = models.CharField(max_length=255, blank=True, verbose_name="Rua / Avenida")
    delivery_number = models.CharField(max_length=50, blank=True, verbose_name="Número")
    delivery_neighborhood = models.CharField(max_length=150, blank=True, verbose_name="Bairro")
    delivery_city = models.CharField(max_length=100, default="Cuiabá", verbose_name="Cidade")
    delivery_reference = models.CharField(max_length=255, blank=True, verbose_name="Ponto de Referência")
    delivery_complement = models.CharField(max_length=150, blank=True, verbose_name="Complemento")
    delivery_zipcode = models.CharField(max_length=10, blank=True, verbose_name="CEP")
    pickup_requested_time = models.CharField(max_length=50, blank=True, verbose_name="Horário Pretendido de Retirada")
    # Who took the order out (set when it goes out for delivery); kept for the riders' payments
    courier = models.ForeignKey("delivery.Employee", null=True, blank=True, on_delete=models.PROTECT, related_name="orders", verbose_name="Entregador")

    # Status
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.NOVO, db_index=True, verbose_name="Status do Pedido")
    
    # Payment
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.PIX, verbose_name="Forma de Pagamento")
    needs_change = models.BooleanField(default=False, verbose_name="Precisa de Troco")
    change_for = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Troco Para (R$)")
    calculated_change = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Troco Calculado a Levar (R$)")
    
    # Totals (Exact historical snapshot)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Subtotal dos Itens (R$)")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Desconto Aplicado (R$)")
    coupon_applied = models.CharField(max_length=50, blank=True, verbose_name="Cupom Utilizado")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Taxa de Entrega (R$)")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total do Pedido (R$)")
    
    notes = models.TextField(blank=True, verbose_name="Observações Gerais")

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.readable_code} - {self.customer_name} ({self.get_status_display()})"

    @property
    def tracking_url(self):
        return f"/?rastreio={self.readable_code}"

class OrderItem(TimeStampedModel):
    """Snapshot item of an order."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Pedido")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Produto de Origem")
    
    product_type_snapshot = models.CharField(max_length=30, default="pizza", verbose_name="Tipo do Produto")
    product_name_snapshot = models.CharField(max_length=150, verbose_name="Nome do Produto")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantidade")
    unit_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Unitário (R$)")
    subtotal_snapshot = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Subtotal do Item (R$)")
    
    # Pizza-specific details
    size_id_snapshot = models.CharField(max_length=50, blank=True, verbose_name="ID do Tamanho")
    size_name_snapshot = models.CharField(max_length=100, blank=True, verbose_name="Nome do Tamanho")
    crust = models.ForeignKey(PizzaCrust, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Borda")
    crust_name_snapshot = models.CharField(max_length=100, blank=True, verbose_name="Nome da Borda")
    crust_price_snapshot = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, verbose_name="Preço da Borda (R$)")
    
    notes = models.CharField(max_length=255, blank=True, verbose_name="Observações do Item")

    class Meta:
        verbose_name = "Item do Pedido"
        verbose_name_plural = "Itens do Pedido"

    def __str__(self):
        return f"{self.quantity}x {self.product_name_snapshot}"

class OrderItemFlavor(TimeStampedModel):
    """Fractional flavor of a customizable pizza."""
    item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="flavors", verbose_name="Item de Pizza")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Sabor Original")
    flavor_name_snapshot = models.CharField(max_length=150, verbose_name="Nome do Sabor")
    proportion = models.CharField(max_length=10, default="1/1", verbose_name="Fração (ex: 1/2, 1/3)")

    class Meta:
        verbose_name = "Sabor da Pizza"
        verbose_name_plural = "Sabores da Pizza"

    def __str__(self):
        return f"{self.proportion} {self.flavor_name_snapshot}"

class OrderStatusHistory(TimeStampedModel):
    """Audit log of status changes for an order."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history", verbose_name="Pedido")
    status = models.CharField(max_length=25, verbose_name="Status")
    notes = models.CharField(max_length=255, blank=True, verbose_name="Nota / Motivo")
    changed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Alterado por")

    class Meta:
        verbose_name = "Histórico de Status"
        verbose_name_plural = "Históricos de Status"
        ordering = ["created_at"]
