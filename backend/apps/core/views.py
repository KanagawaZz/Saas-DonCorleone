"""Friendly error pages (handler400/403/404/500): HTML for people, JSON for the API."""
import sys
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from .errors import area_for, new_code, record

# Per area: (title, explanation, next steps, "back" link label, link)
MESSAGES = {
    500: {
        "painel": ("Algo deu errado nesta tela",
                   "Não foi nada que você fez. O sistema registrou o problema e o suporte já consegue ver o que aconteceu.",
                   "Tente de novo em alguns instantes. Se continuar, envie o código abaixo para o suporte.",
                   "Voltar ao início do painel", "/painel/"),
        "entregador": ("Não conseguimos abrir esta tela",
                       "Suas entregas continuam registradas. O problema foi anotado para o suporte.",
                       "Tente de novo em alguns instantes. Se continuar, avise o gerente e passe o código abaixo.",
                       "Voltar para minhas entregas", "/entregador/"),
        "geral": ("Algo deu errado",
                  "Tivemos um problema inesperado. Ele foi registrado e será verificado.",
                  "Tente de novo em alguns instantes. Se continuar, fale com a pizzaria e informe o código abaixo.",
                  "Voltar ao início", "/"),
    },
    404: {
        "painel": ("Página não encontrada", "Este endereço não existe no painel ou foi removido.",
                   "Use o menu para encontrar o que procura.", "Voltar ao início do painel", "/painel/"),
        "entregador": ("Página não encontrada", "Este endereço não existe no app do entregador.",
                       "Abra o app pelo ícone na tela inicial.", "Voltar para minhas entregas", "/entregador/"),
        "geral": ("Página não encontrada", "Este endereço não existe ou foi removido.",
                  "Confira se o endereço foi digitado certo.", "Voltar ao início", "/"),
    },
    403: {
        "painel": ("Acesso não permitido", "Esta área é só para a equipe da pizzaria.",
                   "Entre com um login da equipe ou peça acesso ao responsável.", "Ir para o login", "/painel/entrar/"),
        "entregador": ("Acesso não permitido", "Este endereço não está liberado para você.",
                       "Abra o app pelo seu link pessoal ou peça um novo ao gerente.", "Voltar", "/entregador/"),
        "geral": ("Acesso não permitido", "Você não tem permissão para ver esta página.",
                  "Se acha que é um engano, fale com a pizzaria.", "Voltar ao início", "/"),
    },
    400: {
        "painel": ("Não foi possível concluir o pedido", "Os dados enviados chegaram incompletos ou num formato inesperado.",
                   "Volte, recarregue a página e tente de novo.", "Voltar ao início do painel", "/painel/"),
        "entregador": ("Não foi possível concluir", "Os dados enviados chegaram incompletos.",
                       "Volte e tente de novo.", "Voltar para minhas entregas", "/entregador/"),
        "geral": ("Não foi possível concluir", "Os dados enviados chegaram incompletos ou num formato inesperado.",
                  "Volte e tente de novo.", "Voltar ao início", "/"),
    },
}

API_MESSAGES = {
    500: "Tivemos um problema ao processar sua solicitação. Tente de novo em instantes. "
         "Se continuar, fale com a pizzaria e informe o código {code}.",
    404: "Endereço não encontrado.",
    403: "Acesso não permitido.",
    400: "Requisição inválida.",
}


def error_response(request, status, code=None):
    area = area_for(request.path)
    if area == "api":
        body = {"mensagem": API_MESSAGES[status].format(code=code)}
        if code:
            body["codigoOcorrencia"] = code
        return JsonResponse(body, status=status)

    page_area = area if area in ("painel", "entregador") else "geral"
    title, reason, next_steps, back_label, back_url = MESSAGES[status][page_area]
    context = {
        "status": status, "area": page_area, "titulo": title, "motivo": reason, "proximos_passos": next_steps,
        "voltar_rotulo": back_label, "voltar_url": back_url, "codigo": code, "momento": timezone.localtime(),
    }
    # Standalone template: must render even when the database or the app's base layout is the problem
    return render(request, "core/erro.html", context, status=status)


def handler500(request):
    """Errors that escaped the middleware (e.g. raised by another middleware)."""
    code = getattr(request, "_error_code", None)
    if not code:
        code = new_code()
        exc = sys.exc_info()[1]
        if exc:
            record(request, exc, code)
    return error_response(request, 500, code=code)


def handler404(request, exception=None):
    return error_response(request, 404)


def handler403(request, exception=None):
    return error_response(request, 403)


def handler400(request, exception=None):
    return error_response(request, 400)
