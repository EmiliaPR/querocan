"""
Vistas da persoa adoptante no fluxo de adopción: solicitar, ver as súas solicitudes,
completar o compromiso de responsabilidade e aceptar o contrato.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from animais.api import CLAVE_CAN_PENDENTE
from animais.models import Can
from contas.decoradores import require_rol
from contas.models import Usuario

from . import estados

so_adoptante = require_rol(Usuario.Rol.ADOPTANTE)


def _crear_e_avisar(request, can):
    """Intenta crear a solicitude e explica o resultado cunha mensaxe."""
    try:
        estados.crear_solicitude(request.user, can)
    except estados.PerfilIncompleto:
        request.session[CLAVE_CAN_PENDENTE] = can.pk
        messages.info(request, "Antes de solicitar a adopción, fai o test de compatibilidade.")
        return redirect("compatibilidade:test")
    except estados.TransicionInvalida as erro:
        messages.error(request, str(erro))
        return None
    messages.success(
        request, f"Enviamos a túa solicitude para {can.nome}. A protectora revisaraa en breve."
    )
    return None


@require_POST
def solicitar(request, pk):
    """Botón «Adoptar» (listado, ficha e resultado): o mesmo ca deslizar á dereita."""
    can = get_object_or_404(Can, pk=pk)
    if not request.user.is_authenticated:
        request.session[CLAVE_CAN_PENDENTE] = can.pk
        messages.info(request, "Entra ou crea unha conta para solicitar a adopción.")
        return redirect(reverse("contas:entrar") + "?next=" + reverse("adopcions:continuar"))
    if not request.user.es_adoptante:
        raise PermissionDenied("Só as persoas adoptantes poden solicitar unha adopción.")

    redireccion = _crear_e_avisar(request, can)
    if redireccion:
        return redireccion
    volver = request.POST.get("volver")
    if volver and url_has_allowed_host_and_scheme(volver, allowed_hosts={request.get_host()}):
        return redirect(volver)
    return redirect("adopcions:minas_solicitudes")


@so_adoptante
def continuar(request):
    """Despois de entrar ou facer o test: crea a solicitude que quedara pendente."""
    can_id = request.session.pop(CLAVE_CAN_PENDENTE, None)
    if can_id is None:
        return redirect("animais:deck")
    can = Can.objects.filter(pk=can_id).first()
    if can is None:
        return redirect("animais:deck")
    redireccion = _crear_e_avisar(request, can)
    return redireccion or redirect("adopcions:minas_solicitudes")


@so_adoptante
def minas_solicitudes(request):
    """Listado das solicitudes da persoa (implementado en T15)."""
    return render(request, "en_construcion.html", {"titulo": "As miñas solicitudes"})
