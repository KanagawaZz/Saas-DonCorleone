"""
Support lookup for occurrence codes shown on the error pages.
    python manage.py ocorrencia ERR-2110-K7QX     full details of one occurrence
    python manage.py ocorrencia --ultimas 20      latest occurrences
"""
import json
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.core.models import ErrorEvent


class Command(BaseCommand):
    help = "Mostra os detalhes de uma ocorrência de erro (código ERR-...) ou lista as últimas."

    def add_arguments(self, parser):
        parser.add_argument("codigo", nargs="?", help="Código mostrado na tela de erro, ex.: ERR-2110-K7QX")
        parser.add_argument("--ultimas", type=int, default=0, help="Lista as N ocorrências mais recentes")
        parser.add_argument("--resolvida", action="store_true", help="Marca a ocorrência como resolvida")

    def handle(self, *args, codigo=None, ultimas=0, resolvida=False, **options):
        if ultimas or not codigo:
            for event in ErrorEvent.objects.all()[: ultimas or 20]:
                when = timezone.localtime(event.occurred_at)
                status = "resolvida" if event.resolved else "aberta"
                self.stdout.write(f"{event.code}  {when:%d/%m %H:%M}  {status:9}  {event.method} {event.path[:60]}  "
                                  f"{event.exception_type.rsplit('.', 1)[-1]}: {event.message[:60]}")
            return

        event = ErrorEvent.objects.filter(code__iexact=codigo.strip()).first()
        if not event:
            raise CommandError(f"Ocorrência {codigo} não encontrada (são guardadas por 30 dias).")
        if resolvida:
            event.resolved = True
            event.save(update_fields=["resolved"])
            self.stdout.write(self.style.SUCCESS(f"{event.code} marcada como resolvida."))
            return

        when = timezone.localtime(event.occurred_at)
        lines = [
            f"Ocorrência:  {event.code} ({'resolvida' if event.resolved else 'aberta'})",
            f"Quando:      {when:%d/%m/%Y %H:%M:%S}",
            f"Área:        {event.area}",
            f"Requisição:  {event.method} {event.path}",
            f"Usuário:     {event.user_label or 'não logado'}" + (f" (id {event.user_id})" if event.user_id else ""),
            f"IP:          {event.ip}",
            f"Navegador:   {event.user_agent}",
            f"Erro:        {event.exception_type}: {event.message}",
            f"Origem:      {event.origin}",
            "",
            "Dados enviados (senhas e tokens removidos):",
            json.dumps(event.request_data, ensure_ascii=False, indent=2, default=str),
            "",
            "Traceback:",
            event.traceback,
        ]
        self.stdout.write("\n".join(lines))
