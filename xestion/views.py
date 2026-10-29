"""Panel do superadmin."""

from django.shortcuts import render

from contas.decoradores import require_rol
from contas.models import Usuario


@require_rol(Usuario.Rol.SUPERADMIN)
def inicio(request):
    """Portada do panel de xestión (implementada en T19)."""
    return render(request, "en_construcion.html", {"titulo": "Xestión"})
