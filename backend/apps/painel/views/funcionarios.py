"""Staff registry and the advances ("vales") each employee takes during the month."""
from datetime import date
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import TruncMonth
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from apps.delivery.models import Employee, SalaryAdvance
from ..access import painel_view
from ..forms import EmployeeForm, SalaryAdvanceForm
from ..templatetags.painel import brl
from .common import nav_context
from .entregadores import app_access_context

MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
          "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _add_months(day: date, months: int) -> date:
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def _month(request):
    """First day of the month in ?mes=YYYY-MM (current month by default)."""
    try:
        year, month = map(int, request.GET.get("mes", "").split("-"))
        return date(year, month, 1)
    except ValueError:
        return timezone.localdate().replace(day=1)


def month_label(day: date) -> str:
    return f"{MONTHS[day.month - 1]} de {day.year}"


@painel_view
def funcionarios(request):
    tenant = request.tenant
    month = _month(request)
    next_month = _add_months(month, 1)
    advance_form = SalaryAdvanceForm(tenant=tenant, initial={"date": timezone.localdate()})
    employee_form = EmployeeForm(tenant=tenant)

    if request.method == "POST":
        if request.POST.get("acao") == "funcionario":
            employee_form = EmployeeForm(request.POST, tenant=tenant)
            if employee_form.is_valid():
                employee = employee_form.save()
                messages.success(request, f"{employee.name} cadastrado.")
                return redirect(request.get_full_path())
        else:
            advance_form = SalaryAdvanceForm(request.POST, tenant=tenant)
            if advance_form.is_valid():
                advance = advance_form.save(commit=False)
                advance.created_by = request.user
                advance.save()
                messages.success(request, f"Vale de {brl(advance.amount)} lançado para {advance.employee.name}.")
                return redirect(f"{request.path}?mes={advance.date:%Y-%m}")

    advances = (
        SalaryAdvance.objects.filter(tenant=tenant, date__gte=month, date__lt=next_month)
        .select_related("employee", "created_by")
    )
    totals = {
        row["employee"]: row
        for row in advances.values("employee").annotate(qtd=Count("id"), total=Sum("amount"))
    }
    employees = Employee.objects.filter(tenant=tenant).filter(Q(is_active=True) | Q(pk__in=totals.keys()))
    rows = [
        {"funcionario": e, "qtd": totals.get(e.pk, {}).get("qtd", 0), "total": totals.get(e.pk, {}).get("total") or 0}
        for e in employees
    ]
    rows.sort(key=lambda r: (-r["total"], r["funcionario"].name.lower()))

    context = {
        **nav_context(request, "funcionarios"),
        "mes": month,
        "mes_label": month_label(month),
        "mes_anterior": _add_months(month, -1),
        "mes_seguinte": next_month if next_month <= timezone.localdate() else None,
        "form_vale": advance_form,
        "form_funcionario": employee_form,
        "linhas": rows,
        "vales": advances,
        "total_mes": sum(r["total"] for r in rows),
        "qtd_vales": sum(r["qtd"] for r in rows),
        "qtd_com_vale": sum(1 for r in rows if r["qtd"]),
    }
    return render(request, "painel/funcionarios/lista.html", context)


@painel_view
def funcionario(request, pk):
    employee = get_object_or_404(Employee, pk=pk, tenant=request.tenant)
    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee, tenant=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, "Funcionário salvo.")
            return redirect("painel:funcionario", pk=employee.pk)
    else:
        form = EmployeeForm(instance=employee, tenant=request.tenant)

    by_month = (
        employee.advances.annotate(mes=TruncMonth("date")).values("mes")
        .annotate(qtd=Count("id"), total=Sum("amount")).order_by("-mes")[:12]
    )
    context = {
        **nav_context(request, "funcionarios"),
        "funcionario": employee,
        "form": form,
        "por_mes": [{**m, "label": month_label(m["mes"])} for m in by_month],
        "vales": employee.advances.select_related("created_by")[:60],
        **app_access_context(request, employee),
    }
    return render(request, "painel/funcionarios/detalhe.html", context)


@painel_view
def funcionario_excluir(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    employee = get_object_or_404(Employee, pk=pk, tenant=request.tenant)
    try:
        employee.delete()
    except ProtectedError:
        messages.error(request, f"{employee.name} tem vales ou entregas no histórico. "
                                "Para tirar das listas, desmarque \"Na equipe\" e salve.")
        return redirect("painel:funcionario", pk=employee.pk)
    messages.success(request, f"{employee.name} removido.")
    return redirect("painel:funcionarios")


@painel_view
def vale_excluir(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    advance = get_object_or_404(SalaryAdvance, pk=pk, tenant=request.tenant)
    advance.delete()
    messages.success(request, f"Vale de {advance.employee.name} ({advance.date:%d/%m}) excluído.")
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("painel:funcionarios")
