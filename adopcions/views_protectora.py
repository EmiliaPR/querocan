"""
Panel de solicitudes da protectora.

A protectora ve as solicitudes dos seus cans coa compatibilidade calculada co perfil
actual de cada persoa e os motivos, e decide: aceptar (match), rexeitar ou cancelar
unha adopción aceptada. Todas as accións pasan por adopcions/estados.py.
"""

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from compatibilidade.calculo import calcular
from contas.decoradores import require_protectora_activa

from . import estados
from .models import Solicitude

ACCIONS = {
    "aceptar": (estados.aceptar, "Aceptaches a solicitude de {persoa} para {can}."),
    "rexeitar": (estados.rexeitar, "Rexeitaches a solicitude de {persoa} para {can}."),
    "cancelar": (estados.cancelar_aceptada, "Cancelaches a adopción de {can}."),
}


@require_protectora_activa
def solicitudes(request):
    """Lista de solicitudes filtrable por can e estado (por defecto, as activas)."""
    consulta = (
        Solicitude.objects.filter(can__protectora=request.protectora)
        .select_related("can", "adoptante__perfil")
        .order_by("-data_creacion")
    )
    estado = request.GET.get("estado", "activas")
    if estado == "activas":
        consulta = consulta.filter(estado__in=Solicitude.ACTIVAS)
    elif estado in Solicitude.Estado.values:
        consulta = consulta.filter(estado=estado)
    can_id = request.GET.get("can")
    if can_id and can_id.isdigit():
        consulta = consulta.filter(can_id=can_id)

    # Cantas solicitudes activas ten cada persoa (en calquera protectora)
    adoptantes = {s.adoptante_id for s in consulta}
    activas_por_persoa = dict(
        Solicitude.objects.filter(adoptante_id__in=adoptantes, estado__in=Solicitude.ACTIVAS)
        .values_list("adoptante_id")
        .annotate(total=Count("pk"))
    )

    filas = []
    for solicitude in consulta:
        perfil = getattr(solicitude.adoptante, "perfil", None)
        resultado = calcular(perfil.como_perfil(), solicitude.can.necesidades()) if perfil else None
        filas.append(
            {
                "solicitude": solicitude,
                "resultado": resultado,
                "perfil": perfil,
                "outras_activas": activas_por_persoa.get(solicitude.adoptante_id, 1) - 1,
                "data_limite": estados.data_limite(solicitude),
            }
        )

    cans = request.protectora.cans.annotate(
        activas=Count("solicitudes", filter=Q(solicitudes__estado__in=Solicitude.ACTIVAS))
    ).order_by("nome")
    return render(
        request,
        "adopcions/protectora/solicitudes.html",
        {
            "filas": filas,
            "cans": cans,
            "estado": estado,
            "can_id": can_id,
            "estados_posibles": Solicitude.Estado.choices,
            "seccion": "solicitudes",
        },
    )


@require_protectora_activa
@require_POST
def accion(request, pk, nome):
    """Aplica aceptar / rexeitar / cancelar a unha solicitude dun can propio."""
    solicitude = get_object_or_404(
        Solicitude.objects.select_related("can", "adoptante"),
        pk=pk,
        can__protectora=request.protectora,
    )
    if nome not in ACCIONS:
        return redirect("adopcions:protectora_solicitudes")
    funcion, texto = ACCIONS[nome]
    try:
        funcion(solicitude, request.user)
        messages.success(
            request, texto.format(persoa=solicitude.adoptante.nome, can=solicitude.can.nome)
        )
    except estados.TransicionInvalida as erro:
        messages.error(request, str(erro))
    return redirect(request.POST.get("volver") or "adopcions:protectora_solicitudes")
