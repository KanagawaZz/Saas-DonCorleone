import uuid
from django.conf import settings
from django.db import models

class UUIDModel(models.Model):
    """Abstract model providing a primary key UUID."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

class TimeStampedModel(UUIDModel):
    """Abstract model providing created_at and updated_at timestamps."""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        abstract = True


class ErrorEvent(models.Model):
    """Unexpected error shown to a user as an occurrence code (see core/errors.py)."""
    code = models.CharField(max_length=20, unique=True, verbose_name="Código da ocorrência")
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Quando")
    area = models.CharField(max_length=20, verbose_name="Área")
    method = models.CharField(max_length=10, verbose_name="Método")
    path = models.CharField(max_length=500, verbose_name="Endereço")
    exception_type = models.CharField(max_length=200, verbose_name="Erro")
    message = models.TextField(blank=True, verbose_name="Mensagem")
    origin = models.CharField(max_length=300, blank=True, verbose_name="Arquivo e linha")
    traceback = models.TextField(verbose_name="Traceback")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Usuário")
    user_label = models.CharField(max_length=150, blank=True, verbose_name="Login")
    ip = models.CharField(max_length=45, blank=True, verbose_name="IP")
    user_agent = models.CharField(max_length=300, blank=True, verbose_name="Navegador")
    request_data = models.JSONField(default=dict, blank=True, verbose_name="Dados enviados")
    resolved = models.BooleanField(default=False, verbose_name="Resolvido")

    class Meta:
        verbose_name = "Ocorrência de erro"
        verbose_name_plural = "Ocorrências de erro"
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"{self.code} · {self.exception_type.rsplit('.', 1)[-1]}"
