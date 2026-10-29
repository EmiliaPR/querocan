"""
Vistas públicas e do adoptante sobre os cans: listado (grella), ficha e deck.

Todas ordenan e anotan os cans coa compatibilidade e a distancia da persoa que mira
(ver animais/consultas.py). Sen test feito, non se amosa porcentaxe.
"""

from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from adopcions.models import Solicitude
from compatibilidade import perfil as almacen
from compatibilidade.forms import FormularioLocalizacion
from contas.models import Protectora

from .consultas import avaliar, cans_avaliados
from .filtros import contexto_filtros, ler_filtros
from .models import Can

CANS_POR_PAXINA = 12


def _contexto_comun(request):
    """Filtros, localización e se a persoa fixo o test (para listado e deck)."""
    return {
        **contexto_filtros(request.GET),
        "localizacion": almacen.descricion_localizacion(request),
        "formulario_localizacion": FormularioLocalizacion(),
        "ten_perfil": almacen.perfil_de(request) is not None,
        "consulta_filtros": request.GET.urlencode(),
    }


def listado(request):
    """Grella de cans dispoñibles con filtros."""
    avaliados = cans_avaliados(request, ler_filtros(request.GET))
    paxina = Paginator(avaliados, CANS_POR_PAXINA).get_page(request.GET.get("paxina"))
    protectoras = Protectora.objects.filter(estado=Protectora.Estado.ACTIVA).count()
    return render(
        request,
        "animais/listado.html",
        {
            **_contexto_comun(request),
            "paxina": paxina,
            "total": len(avaliados),
            "total_protectoras": protectoras,
        },
    )


def ficha(request, pk):
    """Ficha completa dun can, coa compatibilidade e todos os motivos."""
    can = get_object_or_404(
        Can.objects.select_related("protectora__concello").prefetch_related("fotos"), pk=pk
    )
    e_da_protectora = request.user.is_authenticated and can.protectora.usuario_id == request.user.pk
    if not e_da_protectora and (can.estado == Can.Estado.RETIRADO or not can.protectora.activa):
        raise Http404

    perfil = almacen.perfil_de(request)
    avaliado = avaliar([can], perfil, almacen.localizacion_de(request))[0]
    solicitude = None
    if request.user.is_authenticated and request.user.es_adoptante:
        solicitude = (
            Solicitude.objects.filter(adoptante=request.user, can=can)
            .order_by("-data_creacion")
            .first()
        )
    parecidos = cans_avaliados(request, {"tamano": can.tamano}, excluir=[can.pk])[:3]
    return render(
        request,
        "animais/ficha.html",
        {
            "can": can,
            "avaliado": avaliado,
            "motivos": avaliado.resultado.motivos if avaliado.resultado else [],
            "solicitude": solicitude,
            "parecidos": parecidos,
        },
    )


def deck(request):
    """Deck de tarxetas con swipe. As tarxetas cárgaas deck-app.js desde a API."""
    return render(request, "animais/deck.html", _contexto_comun(request))


def proba_deck(request):
    """Deck con datos falsos para probar o xesto en móbil real. Só en desenvolvemento."""
    if not settings.DEBUG:
        raise Http404
    return render(request, "animais/proba_deck.html")
