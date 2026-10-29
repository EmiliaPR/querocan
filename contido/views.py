"""
Vistas das páxinas públicas de contido.

Non requiren conta: calquera visitante pode ver a landing, o manual, os enlaces, as
protectoras e os testemuños de Finais felices.
"""

from django.db.models import Count, Q
from django.shortcuts import render

from animais.consultas import cans_avaliados
from animais.models import Can
from contas.models import Protectora

from .models import Enlace, Testemuno

CANS_NA_LANDING = 3


def landing(request):
    """Páxina de inicio: explica QueroCan «coma un Tinder» para adoptar cans."""
    return render(
        request,
        "contido/landing.html",
        {
            "avaliados": cans_avaliados(request)[:CANS_NA_LANDING],
            "testemunos": Testemuno.objects.filter(publicado=True)[:2],
        },
    )


def finais_felices(request):
    testemunos = Testemuno.objects.filter(publicado=True)
    return render(request, "contido/finais_felices.html", {"testemunos": testemunos})


def enlaces(request):
    return render(request, "contido/enlaces.html", {"enlaces": Enlace.objects.all()})


def protectoras(request):
    """Protectoras activas e cantos cans teñen dispoñibles."""
    consulta = (
        Protectora.objects.filter(estado=Protectora.Estado.ACTIVA)
        .select_related("concello")
        .annotate(disponibles=Count("cans", filter=Q(cans__estado=Can.Estado.DISPONIBLE)))
    )
    return render(request, "contido/protectoras.html", {"protectoras": consulta})


def paxina(nome_plantilla):
    """Vista para páxinas de texto fixo (manual, privacidade, contacto)."""

    def vista(request):
        return render(request, f"contido/{nome_plantilla}.html")

    return vista
