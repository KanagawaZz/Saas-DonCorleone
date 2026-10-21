from django.db import models
from apps.core.models import TimeStampedModel

class Tenant(TimeStampedModel):
    """Represents a restaurant / establishment (Don Corleone). Prepared for SaaS expansion."""
    name = models.CharField(max_length=150, verbose_name="Nome do Estabelecimento")
    slug = models.SlugField(max_length=150, unique=True, verbose_name="Identificador / Slug")
    segment = models.CharField(max_length=100, default="Pizzaria e Esfiharia", verbose_name="Segmento")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Telefone")
    whatsapp_number = models.CharField(max_length=30, blank=True, verbose_name="WhatsApp")
    address = models.CharField(max_length=255, blank=True, verbose_name="Endereço")
    city = models.CharField(max_length=100, default="Cuiabá", verbose_name="Cidade")
    state = models.CharField(max_length=2, default="MT", verbose_name="Estado")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Estabelecimento"
        verbose_name_plural = "Estabelecimentos"

    def __str__(self):
        return self.name

class TenantModel(TimeStampedModel):
    """Abstract model linking child entities to their tenant for full logical data isolation."""
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_related",
        verbose_name="Estabelecimento"
    )

    class Meta:
        abstract = True
