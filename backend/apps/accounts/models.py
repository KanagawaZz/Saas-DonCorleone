import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.models import TimeStampedModel
from apps.tenants.models import Tenant

class User(AbstractUser):
    """
    Custom user model for Don Corleone.
    Serves both administration / kitchen staff and registered customers.
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        OPERATOR = 'operator', 'Operador / Cozinha'
        DRIVER = 'driver', 'Entregador / Motoboy'
        CUSTOMER = 'customer', 'Cliente Cadastrado'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER, verbose_name="Papel / Perfil")
    phone = models.CharField(max_length=30, blank=True, verbose_name="WhatsApp / Telefone")
    tenant = models.ForeignKey(Tenant, null=True, blank=True, on_delete=models.SET_NULL, related_name="users", verbose_name="Estabelecimento")

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_staff_member(self):
        return self.role in [self.Role.ADMIN, self.Role.OPERATOR]

class CustomerProfile(TimeStampedModel):
    """Extended customer profile for registered clients with loyalty benefits and saved addresses."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_profile", verbose_name="Usuário")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="customer_profiles", verbose_name="Estabelecimento")
    whatsapp = models.CharField(max_length=30, verbose_name="WhatsApp")
    default_address_street = models.CharField(max_length=255, blank=True, verbose_name="Rua / Logradouro")
    default_address_number = models.CharField(max_length=50, blank=True, verbose_name="Número")
    default_address_neighborhood = models.CharField(max_length=100, blank=True, verbose_name="Bairro")
    default_address_city = models.CharField(max_length=100, default="Cuiabá", verbose_name="Cidade")
    default_address_reference = models.CharField(max_length=255, blank=True, verbose_name="Ponto de Referência")
    is_vip = models.BooleanField(default=False, verbose_name="Cliente VIP")
    total_orders_count = models.PositiveIntegerField(default=0, verbose_name="Total de Pedidos")
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total Gasto (R$)")

    class Meta:
        verbose_name = "Perfil de Cliente"
        verbose_name_plural = "Perfis de Clientes"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.whatsapp}"
