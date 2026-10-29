"""Vistas públicas e do adoptante sobre os cans (listado, ficha e deck)."""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from contas.decoradores import require_rol
from contas.models import Usuario


def deck(request):
    """Deck de tarxetas con swipe (implementado en T13)."""
    return render(request, "en_construcion.html", {"titulo": "Descubrir cans"})


@require_rol(Usuario.Rol.PROTECTORA)
def protectora_cans(request):
    """Listado de cans da protectora (implementado en T7)."""
    return render(request, "en_construcion.html", {"titulo": "Os meus cans"})


def listado(request):
    """Listado público de cans (implementado en T12)."""
    return render(request, "en_construcion.html", {"titulo": "Animais"})


def proba_deck(request):
    """Deck con datos falsos para probar o xesto en móbil real. Só en desenvolvemento."""
    if not settings.DEBUG:
        raise Http404
    return render(request, "animais/proba_deck.html")
