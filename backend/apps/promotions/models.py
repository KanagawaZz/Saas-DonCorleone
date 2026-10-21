from django.db import models
from apps.core.models import TimeStampedModel
from apps.tenants.models import Tenant
from django.utils import timezone
from decimal import Decimal

class Promotion(TimeStampedModel):
    """Parameterized promotion and coupon campaigns."""
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Porcentagem (%)'
        FIXED_AMOUNT = 'fixed', 'Valor Fixo (R$)'

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="promotions", verbose_name="Estabelecimento")
    title = models.CharField(max_length=150, verbose_name="Título da Campanha")
    description = models.TextField(blank=True, verbose_name="Descrição")
    coupon_code = models.CharField(max_length=30, unique=True, blank=True, null=True, verbose_name="Código do Cupom")
    
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE, verbose_name="Tipo de Desconto")
    discount_value = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, verbose_name="Valor do Desconto (% ou R$)")
    
    # Conditions
    min_order_value = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, verbose_name="Pedido Mínimo Elegível (R$)")
    registered_customers_only = models.BooleanField(default=False, verbose_name="Apenas para Clientes Cadastrados")
    weekdays_allowed = models.JSONField(default=list, blank=True, verbose_name="Dias da Semana Permitidos (ex: [1, 2])")
    
    # Validity
    start_date = models.DateField(null=True, blank=True, verbose_name="Data de Início")
    end_date = models.DateField(null=True, blank=True, verbose_name="Data de Término")
    is_active = models.BooleanField(default=True, verbose_name="Ativa")
    
    # Top banner highlight on website
    show_top_banner = models.BooleanField(default=False, verbose_name="Exibir Faixa no Topo do Site")
    banner_text = models.CharField(max_length=255, blank=True, verbose_name="Texto da Faixa no Topo")

    # Usage limits
    max_uses = models.PositiveIntegerField(null=True, blank=True, verbose_name="Limite Máximo de Usos")
    current_uses = models.PositiveIntegerField(default=0, verbose_name="Usos Atuais")

    class Meta:
        verbose_name = "Promoção / Cupom"
        verbose_name_plural = "Promoções e Cupons"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.coupon_code or 'Sem cupom'})"

    def is_currently_valid(self, user=None, order_subtotal=Decimal('0.00')) -> tuple[bool, str]:
        """Validates if promotion can be applied right now."""
        if not self.is_active:
            return False, "Promoção inativa."

        today = timezone.localdate()
        if self.start_date and today < self.start_date:
            return False, "Esta promoção ainda não iniciou."
        if self.end_date and today > self.end_date:
            return False, "Esta promoção já expirou."

        if self.weekdays_allowed:
            # 0=Monday in Python, in our schema let's check current weekday
            current_weekday = today.weekday()  # Mon=0, Sun=6
            if current_weekday not in self.weekdays_allowed:
                return False, "Esta promoção não é válida hoje."

        if self.registered_customers_only:
            if not user or not user.is_authenticated:
                return False, "Promoção exclusiva para clientes cadastrados. Faça seu login ou cadastro!"

        if self.min_order_value and order_subtotal < self.min_order_value:
            return False, f"Pedido mínimo para esta promoção é de R$ {self.min_order_value:.2f}"

        if self.max_uses and self.current_uses >= self.max_uses:
            return False, "Limite de utilizações desta promoção já foi atingido."

        return True, "Promoção válida!"

    def calculate_discount(self, subtotal: Decimal) -> Decimal:
        """Calculates discount amount in Reais."""
        if self.discount_type == self.DiscountType.PERCENTAGE:
            pct = Decimal(str(self.discount_value))
            return ((subtotal * pct) / Decimal('100.00')).quantize(Decimal('0.01'))
        else:
            return min(subtotal, Decimal(str(self.discount_value)))
