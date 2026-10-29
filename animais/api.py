"""
API JSON do deck de swipe (a usa static/js/deck-app.js).

  GET  /api/deck/            → seguinte tanda de cans ordenados para a persoa
  POST /api/deck/decision/   → {"can": id, "decision": "gustame" | "non"}
  POST /api/deck/desfacer/   → {"can": id, "decision": "gustame" | "non"}

As peticións POST levan o token CSRF na cabeceira X-CSRFToken (Django rexeita as
que non o teñen con un 403). As decisións dos visitantes gárdanse na sesión; as das
persoas adoptantes, na base de datos.
"""

import json

from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from adopcions import estados
from adopcions.models import Descarte, Solicitude

from .consultas import cans_avaliados
from .filtros import ler_filtros
from .models import Can

TANDA = 10
CLAVE_DESCARTES = "descartes_deck"  # descartes dos visitantes (na sesión)
CLAVE_CAN_PENDENTE = "can_pendente"  # can que un visitante quería adoptar antes de entrar


def _e_adoptante(request):
    return request.user.is_authenticated and request.user.es_adoptante


def _xa_decididos(request):
    """Cans que esta persoa xa descartou ou solicitou (non se volven amosar)."""
    if _e_adoptante(request):
        descartados = Descarte.objects.filter(adoptante=request.user).values_list(
            "can_id", flat=True
        )
        solicitados = Solicitude.objects.filter(adoptante=request.user).values_list(
            "can_id", flat=True
        )
        return set(descartados) | set(solicitados)
    return set(request.session.get(CLAVE_DESCARTES, []))


def serializar(avaliado):
    """Datos dunha tarxeta do deck."""
    can = avaliado.can
    foto = can.foto_principal
    return {
        "id": can.pk,
        "nome": can.nome,
        "idade": can.idade_texto(),
        "distancia": avaliado.distancia_texto,
        "protectora": can.protectora.nome,
        "foto": foto.imaxe.url if foto else None,
        "urxente": can.urxente,
        "porcentaxe": avaliado.porcentaxe,
        "motivos": [
            {"icona": m.icona, "texto": m.texto, "encaixa": m.encaixa} for m in avaliado.motivos
        ],
        "etiquetas": can.lista_etiquetas,
        "tamano": can.get_tamano_display(),
        "sexo": can.get_sexo_display(),
        "convivencia": can.convivencia_texto,
        "descricion": can.descricion[:400],
        "url_ficha": reverse("animais:ficha", args=[can.pk]),
    }


@require_GET
def tanda(request):
    """Seguinte tanda de cans. `excluir` son os que o navegador xa ten na pila."""
    excluir = {int(x) for x in request.GET.get("excluir", "").split(",") if x.isdigit()}
    excluir |= _xa_decididos(request)
    avaliados = cans_avaliados(request, ler_filtros(request.GET), excluir=excluir)
    return JsonResponse({"cans": [serializar(a) for a in avaliados[:TANDA]]})


def _ler_corpo(request):
    try:
        datos = json.loads(request.body)
        return int(datos["can"]), datos["decision"]
    except (ValueError, KeyError, TypeError):
        return None, None


@require_POST
def decision(request):
    """Garda unha decisión do deck. «gustame» crea a solicitude de adopción."""
    can_id, que = _ler_corpo(request)
    if que not in {"gustame", "non"}:
        return JsonResponse({"erro": "Decisión non válida."}, status=400)
    can = get_object_or_404(Can, pk=can_id)

    if que == "non":
        if _e_adoptante(request):
            estados.descartar(request.user, can)
        else:
            descartes = request.session.get(CLAVE_DESCARTES, [])
            request.session[CLAVE_DESCARTES] = [*descartes, can.pk]
        return JsonResponse({"ok": True})

    # «Gústame»: hai que ter conta de adoptante e o test feito
    if not request.user.is_authenticated:
        request.session[CLAVE_CAN_PENDENTE] = can.pk
        destino = reverse("contas:entrar") + "?next=" + reverse("adopcions:continuar")
        return JsonResponse({"redirixir": destino})
    if not request.user.es_adoptante:
        raise PermissionDenied
    try:
        solicitude = estados.crear_solicitude(request.user, can)
    except estados.PerfilIncompleto:
        request.session[CLAVE_CAN_PENDENTE] = can.pk
        return JsonResponse({"redirixir": reverse("compatibilidade:test")})
    except estados.TransicionInvalida as erro:
        return JsonResponse({"erro": str(erro)}, status=409)
    return JsonResponse({"ok": True, "solicitude": solicitude.pk})


@require_POST
def desfacer(request):
    """Desfai a última decisión do deck."""
    can_id, que = _ler_corpo(request)
    can = get_object_or_404(Can, pk=can_id)
    if que == "non":
        if _e_adoptante(request):
            estados.desfacer_descarte(request.user, can)
        else:
            descartes = [c for c in request.session.get(CLAVE_DESCARTES, []) if c != can.pk]
            request.session[CLAVE_DESCARTES] = descartes
        return JsonResponse({"ok": True})

    if not _e_adoptante(request):
        return JsonResponse({"erro": "Non hai nada que desfacer."}, status=400)
    solicitude = (
        Solicitude.objects.filter(
            adoptante=request.user, can=can, estado=Solicitude.Estado.PENDENTE
        )
        .order_by("-data_creacion")
        .first()
    )
    if solicitude is None:
        return JsonResponse({"erro": "Non hai ningunha solicitude que desfacer."}, status=409)
    try:
        estados.desfacer_solicitude(solicitude, request.user)
    except estados.TransicionInvalida as erro:
        return JsonResponse({"erro": str(erro)}, status=409)
    return JsonResponse({"ok": True})
