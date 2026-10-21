import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.tenants.models import Tenant

class DeliveryZone(TimeStampedModel):
    """Delivery neighborhood and its specific fee in Cuiabá or Várzea Grande."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="delivery_zones", verbose_name="Estabelecimento")
    city = models.CharField(max_length=100, default="Cuiabá", verbose_name="Cidade")
    neighborhood = models.CharField(max_length=150, verbose_name="Bairro")
    fee = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Taxa de Entrega (R$)")
    is_active = models.BooleanField(default=True, verbose_name="Ativo / Atendido")
    estimated_minutes = models.PositiveIntegerField(default=50, verbose_name="Tempo Estimado (min)")

    class Meta:
        verbose_name = "Bairro e Taxa de Entrega"
        verbose_name_plural = "Bairros e Taxas de Entrega"
        ordering = ["city", "neighborhood"]
        unique_together = ("tenant", "city", "neighborhood")

    def __str__(self):
        return f"{self.neighborhood} ({self.city}) - R$ {self.fee}"

class OperatingHour(TimeStampedModel):
    """Weekly schedule and cutoff times for kitchen."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="operating_hours", verbose_name="Estabelecimento")
    weekday = models.PositiveSmallIntegerField(verbose_name="Dia da Semana (0=Dom, 6=Sáb)")
    name = models.CharField(max_length=30, verbose_name="Nome do Dia")
    opening_time = models.CharField(max_length=5, default="17:30", verbose_name="Horário de Abertura (HH:MM)")
    closing_time = models.CharField(max_length=5, default="23:00", verbose_name="Horário de Fechamento (HH:MM)")
    cutoff_time = models.CharField(max_length=5, default="22:45", verbose_name="Horário de Corte (HH:MM)")
    is_active = models.BooleanField(default=True, verbose_name="Aberto neste dia")

    class Meta:
        verbose_name = "Horário de Funcionamento"
        verbose_name_plural = "Horários de Funcionamento"
        ordering = ["weekday"]
        unique_together = ("tenant", "weekday")

    def __str__(self):
        return f"{self.name}: {self.opening_time} às {self.closing_time} (Corte {self.cutoff_time})"

class Employee(TimeStampedModel):
    """Staff member. Couriers receive the delivery fee of every order they deliver."""
    class Role(models.TextChoices):
        COURIER = "entregador", "Entregador"
        KITCHEN = "cozinha", "Cozinha"
        SERVICE = "atendimento", "Atendimento / caixa"
        MANAGER = "gerencia", "Gerência"
        OTHER = "outro", "Outro"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="employees", verbose_name="Estabelecimento")
    name = models.CharField(max_length=100, verbose_name="Nome")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.COURIER, verbose_name="Função")
    phone = models.CharField(max_length=30, blank=True, verbose_name="WhatsApp")
    is_active = models.BooleanField(default=True, verbose_name="Na equipe")
    # Couriers only. Stored as a date so the "working today" flag resets by itself the next day
    working_on = models.DateField(null=True, blank=True, verbose_name="Trabalhando em")
    # Couriers only: personal link to the courier app, also the device id in Traccar Client
    access_token = models.CharField(max_length=40, null=True, blank=True, unique=True, verbose_name="Código de acesso ao app")
    # First position received with the current code: Traccar is set up, the app stops showing the setup steps
    traccar_connected_at = models.DateTimeField(null=True, blank=True, verbose_name="Traccar conectado em")

    class Meta:
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"
        ordering = ["name"]
        unique_together = ("tenant", "name")

    def __str__(self):
        return self.name

    @property
    def is_working_today(self) -> bool:
        return self.working_on == timezone.localdate()

    def new_access_token(self) -> str:
        """Creates (or replaces, revoking the old link) the courier's app access code."""
        self.access_token = secrets.token_urlsafe(18)
        self.traccar_connected_at = None  # Traccar must be set up again with the new code
        self.save(update_fields=["access_token", "traccar_connected_at", "updated_at"])
        return self.access_token


class CourierLocation(models.Model):
    """
    Last known position of a courier while on duty. Only one row per courier is kept
    (no route history) and it is deleted when the courier ends the shift.
    """
    courier = models.OneToOneField(Employee, on_delete=models.CASCADE, primary_key=True, related_name="location", verbose_name="Entregador")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.FloatField(null=True, blank=True, verbose_name="Precisão (m)")
    battery = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Bateria (%)")
    recorded_at = models.DateTimeField(verbose_name="Registrada em")

    class Meta:
        verbose_name = "Localização do entregador"
        verbose_name_plural = "Localizações dos entregadores"

    def __str__(self):
        return f"{self.courier} @ {self.latitude},{self.longitude}"


class SalaryAdvance(TimeStampedModel):
    """Advance ("vale") taken by an employee, discounted later from their pay."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="salary_advances", verbose_name="Estabelecimento")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="advances", verbose_name="Funcionário")
    amount = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Valor (R$)")
    date = models.DateField(default=timezone.localdate, verbose_name="Data")
    notes = models.CharField(max_length=150, blank=True, verbose_name="Observação")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Lançado por")

    class Meta:
        verbose_name = "Vale"
        verbose_name_plural = "Vales"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.employee} - R$ {self.amount} ({self.date:%d/%m/%Y})"


class StoreSettings(TimeStampedModel):
    """General restaurant business configuration for Don Corleone."""
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="settings", verbose_name="Estabelecimento")
    minimum_order = models.DecimalField(max_digits=6, decimal_places=2, default=23.00, verbose_name="Pedido Mínimo (R$)")
    pix_key = models.CharField(max_length=100, default="65993605364", verbose_name="Chave PIX")
    pix_type = models.CharField(max_length=50, default="Celular / WhatsApp", verbose_name="Tipo da Chave PIX")
    pix_holder = models.CharField(max_length=150, default="Don Corleone Pizzaria & Esfiharia", verbose_name="Titular da Chave PIX")
    pix_instructions = models.TextField(
        default="Faça o Pix com o valor total. Assim que conferirmos o pagamento, seu pedido é confirmado e entra em preparo.",
        verbose_name="Instruções de PIX"
    )
    delivery_time_text = models.CharField(max_length=50, default="40 a 60 min", verbose_name="Tempo Médio de Entrega")
    pickup_time_text = models.CharField(max_length=50, default="20 a 35 min", verbose_name="Tempo Médio de Retirada")
    emergency_closed = models.BooleanField(default=False, verbose_name="Fechamento Emergencial (Feriado/Chuva)")
    emergency_closed_reason = models.CharField(max_length=255, blank=True, verbose_name="Motivo do Fechamento Emergencial")
    # Evolution API instance that sends this store's WhatsApp messages (set up in the panel)
    whatsapp_instance = models.SlugField(max_length=60, blank=True, verbose_name="Instância do WhatsApp")

    class Meta:
        verbose_name = "Configurações da Loja"
        verbose_name_plural = "Configurações da Loja"

    def __str__(self):
        return f"Configurações - {self.tenant.name}"
