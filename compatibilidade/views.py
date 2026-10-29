"""
Vistas do test de compatibilidade e da localización.

O test pódese facer sen conta: as respostas gárdanse na sesión e pasan ao perfil
cando a persoa crea a conta ou entra (ver compatibilidade/perfil.py).
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from animais.api import CLAVE_CAN_PENDENTE
from animais.consultas import cans_avaliados

from . import perfil as almacen
from .forms import FormularioLocalizacion, FormularioTest

CANS_NO_RESULTADO = 3


def test(request):
    """As seis preguntas. Ao enviar, garda as respostas e amosa o resultado."""
    if request.user.is_authenticated and not request.user.es_adoptante:
        messages.info(request, "O test de compatibilidade é para as persoas adoptantes.")
        return redirect("contido:landing")

    if request.method == "POST":
        formulario = FormularioTest(request.POST)
        if formulario.is_valid():
            almacen.gardar_perfil(request, formulario.perfil())
            # Se viña de premer «Adoptar» sen test feito, retomamos esa solicitude
            if request.user.is_authenticated and request.session.get(CLAVE_CAN_PENDENTE):
                return redirect("adopcions:continuar")
            return redirect("compatibilidade:resultado")
    else:
        inicial = FormularioTest.inicial_desde(almacen.perfil_de(request))
        formulario = FormularioTest(initial=inicial)
    return render(request, "compatibilidade/test.html", {"formulario": formulario})


def resultado(request):
    """Os tres cans dispoñibles máis compatibles coas respostas do test."""
    perfil = almacen.perfil_de(request)
    if perfil is None:
        return redirect("compatibilidade:test")
    mellores = cans_avaliados(request)[:CANS_NO_RESULTADO]
    return render(request, "compatibilidade/resultado.html", {"avaliados": mellores})


@require_POST
def localizacion(request):
    """Garda a localización (GPS ou concello) e volve á páxina de orixe."""
    formulario = FormularioLocalizacion(request.POST)
    if formulario.is_valid():
        datos = formulario.cleaned_data
        concello = datos.get("concello")
        if datos.get("latitude") is not None and datos.get("lonxitude") is not None:
            almacen.gardar_localizacion(request, datos["latitude"], datos["lonxitude"])
        else:
            almacen.gardar_localizacion(request, concello.latitude, concello.lonxitude, concello)
    else:
        messages.error(request, "Non puidemos gardar a localización. Escolle o teu concello.")

    volver = request.POST.get("volver", "/")
    if not url_has_allowed_host_and_scheme(volver, allowed_hosts={request.get_host()}):
        volver = "/"
    return redirect(volver)
