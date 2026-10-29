"""Panel de solicitudes da protectora (implementado en T14)."""

from django.shortcuts import render

from contas.decoradores import require_protectora_activa


@require_protectora_activa
def solicitudes(request):
    return render(request, "en_construcion.html", {"titulo": "Solicitudes"})
