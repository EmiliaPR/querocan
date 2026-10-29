"""
Vistas da persoa adoptante no fluxo de adopción: solicitar, ver as súas solicitudes,
completar o compromiso de responsabilidade e aceptar o contrato.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from animais.api import CLAVE_CAN_PENDENTE
from animais.models import Can
from contas.decoradores import require_rol
from contas.models import Usuario

from . import contrato as contrato_mod
from . import estados
from .forms import FormularioChecklist, FormularioContrato
from .models import AceptacionContrato, ItemChecklist, ModeloContrato, Solicitude

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


def _solicitude_propia(request, pk):
    return get_object_or_404(
        Solicitude.objects.select_related("can__protectora"), pk=pk, adoptante=request.user
    )


@so_adoptante
def minas_solicitudes(request):
    """As solicitudes da persoa, das máis recentes ás máis antigas."""
    solicitudes = list(
        Solicitude.objects.filter(adoptante=request.user)
        .select_related("can__protectora")
        .prefetch_related("can__fotos")
    )
    agora = timezone.now()
    for solicitude in solicitudes:
        limite = estados.data_limite(solicitude)
        solicitude.data_limite = limite
        # Días que quedan para completar unha adopción aceptada (redondeando cara arriba)
        solicitude.dias_restantes = (
            max(0, -((agora - limite) // timedelta(days=1))) if limite else None
        )
    return render(request, "adopcions/adoptante/solicitudes.html", {"solicitudes": solicitudes})


@so_adoptante
@require_POST
def retirar(request, pk):
    solicitude = _solicitude_propia(request, pk)
    try:
        if solicitude.estado == Solicitude.Estado.ACEPTADA:
            estados.cancelar_aceptada(solicitude, request.user)
        else:
            estados.retirar(solicitude, request.user)
        messages.success(request, f"Retiraches a solicitude para {solicitude.can.nome}.")
    except estados.TransicionInvalida as erro:
        messages.error(request, str(erro))
    return redirect("adopcions:minas_solicitudes")


@so_adoptante
def checklist(request, pk):
    """Compromiso de responsabilidade: hai que marcar todos os puntos."""
    solicitude = _solicitude_propia(request, pk)
    if solicitude.estado != Solicitude.Estado.ACEPTADA:
        messages.error(request, "Esta solicitude non está aceptada.")
        return redirect("adopcions:minas_solicitudes")
    if solicitude.checklist_feito:
        return redirect("adopcions:contrato", pk=solicitude.pk)

    formulario = FormularioChecklist(
        request.POST or None, items=ItemChecklist.objects.filter(activo=True)
    )
    if request.method == "POST" and formulario.is_valid():
        estados.completar_checklist(solicitude, request.user)
        return redirect("adopcions:contrato", pk=solicitude.pk)
    return render(
        request,
        "adopcions/adoptante/checklist.html",
        {"solicitude": solicitude, "formulario": formulario},
    )


def _ip(request):
    return request.META.get("REMOTE_ADDR")


@so_adoptante
def contrato(request, pk):
    """Contrato de adopción: datos da persoa, texto final e aceptación."""
    solicitude = _solicitude_propia(request, pk)
    if hasattr(solicitude, "contrato"):
        return redirect("adopcions:adopcion_completada", pk=solicitude.pk)
    if solicitude.estado != Solicitude.Estado.ACEPTADA:
        messages.error(request, "Esta solicitude non está aceptada.")
        return redirect("adopcions:minas_solicitudes")
    if not solicitude.checklist_feito:
        return redirect("adopcions:checklist", pk=solicitude.pk)

    inicial = {"nome": request.user.nome, "email": request.user.email}
    formulario = FormularioContrato(request.POST or None, initial=inicial)
    modelo = ModeloContrato.actual()
    if request.method == "POST" and formulario.is_valid():
        try:
            contrato_mod.aceptar(solicitude, request.user, formulario.cleaned_data, _ip(request))
        except estados.TransicionInvalida as erro:
            messages.error(request, str(erro))
            return redirect("adopcions:minas_solicitudes")
        return redirect("adopcions:adopcion_completada", pk=solicitude.pk)

    # Vista previa co texto final (cos datos que xa se coñecen)
    datos_previa = {
        campo: formulario.data.get(campo) or inicial.get(campo) or "…"
        for campo in ("nome", "nif", "enderezo", "telefono", "email")
    }
    previa = contrato_mod.texto_final(modelo, solicitude, datos_previa) if modelo else ""
    return render(
        request,
        "adopcions/adoptante/contrato.html",
        {"solicitude": solicitude, "formulario": formulario, "previa": previa},
    )


@so_adoptante
def adopcion_completada(request, pk):
    """Parabéns! Confirmación e descarga do contrato."""
    solicitude = _solicitude_propia(request, pk)
    aceptacion = get_object_or_404(AceptacionContrato, solicitude=solicitude)
    return render(
        request,
        "adopcions/adoptante/completada.html",
        {"solicitude": solicitude, "aceptacion": aceptacion},
    )


@login_required
def contrato_pdf(request, pk):
    """PDF do contrato. Pódeno descargar a persoa adoptante e a protectora do can."""
    aceptacion = get_object_or_404(
        AceptacionContrato.objects.select_related("solicitude__can__protectora"),
        solicitude__pk=pk,
    )
    solicitude = aceptacion.solicitude
    e_adoptante = solicitude.adoptante_id == request.user.pk
    e_protectora = solicitude.can.protectora.usuario_id == request.user.pk
    if not (e_adoptante or e_protectora or request.user.es_superadmin):
        raise PermissionDenied
    resposta = HttpResponse(contrato_mod.xerar_pdf(aceptacion), content_type="application/pdf")
    nome = f"contrato-adopcion-{slugify(solicitude.can.nome)}-{solicitude.pk}.pdf"
    resposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    return resposta
