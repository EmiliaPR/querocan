"""Vistas públicas e do adoptante sobre os cans (listado, ficha e deck)."""

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
