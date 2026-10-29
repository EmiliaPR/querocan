"""
Consultas de cans para o listado, o deck e o resultado do test.

Xunta tres cousas:
  1. Os filtros simples (tamaño, idade, urxentes), que se fan na base de datos.
  2. A compatibilidade co perfil da persoa (compatibilidade/calculo.py).
  3. A distancia desde a súa localización (compatibilidade/distancia.py).

A compatibilidade e a distancia calcúlanse en Python porque dependen de cada persoa.
Co volume dunha plataforma de protectoras (centos de cans) é rápido abondo.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from compatibilidade import perfil as almacen
from compatibilidade.calculo import Resultado, calcular
from compatibilidade.distancia import distancia_km, texto_distancia
from contas.models import Protectora

from .models import Can

# Tramos de idade dos filtros (en anos)
IDADE_ADULTO = 1
IDADE_MAIOR = 8


@dataclass
class CanAvaliado:
    """Un can coa súa compatibilidade e distancia para a persoa que mira."""

    can: Can
    resultado: Resultado | None
    distancia: float | None
    # A persoa xa ten unha solicitude en curso para este can (non se lle ofrece «Adoptar»)
    solicitado: bool = False

    @property
    def porcentaxe(self):
        return self.resultado.porcentaxe if self.resultado else None

    @property
    def motivos(self):
        return self.resultado.motivos_destacados() if self.resultado else []

    @property
    def distancia_texto(self):
        return texto_distancia(self.distancia)


def cans_publicados():
    """Cans que se poden ver: dispoñibles e de protectoras activas."""
    return (
        Can.objects.filter(
            estado=Can.Estado.DISPONIBLE, protectora__estado=Protectora.Estado.ACTIVA
        )
        .select_related("protectora__concello")
        .prefetch_related("fotos")
    )


def aplicar_filtros(consulta, filtros, hoxe=None):
    """Filtros que se resolven na base de datos: tamaño, idade e urxentes."""
    hoxe = hoxe or date.today()
    if filtros.get("tamano"):
        consulta = consulta.filter(tamano=filtros["tamano"])
    idade = filtros.get("idade")
    limite_adulto = hoxe - timedelta(days=365 * IDADE_ADULTO)
    limite_maior = hoxe - timedelta(days=365 * IDADE_MAIOR)
    if idade == "cachorro":
        consulta = consulta.filter(data_nacemento__gt=limite_adulto)
    elif idade == "adulto":
        consulta = consulta.filter(
            data_nacemento__lte=limite_adulto, data_nacemento__gt=limite_maior
        )
    elif idade == "maior":
        consulta = consulta.filter(data_nacemento__lte=limite_maior)
    if filtros.get("urxentes"):
        consulta = consulta.filter(urxente=True)
    return consulta


def avaliar(cans, perfil=None, localizacion=None):
    """Calcula compatibilidade e distancia de cada can."""
    avaliados = []
    for can in cans:
        resultado = calcular(perfil, can.necesidades()) if perfil else None
        distancia = None
        if localizacion:
            concello = can.protectora.concello
            distancia = distancia_km(*localizacion, concello.latitude, concello.lonxitude)
        avaliados.append(CanAvaliado(can, resultado, distancia))
    return avaliados


def ordenar(avaliados):
    """Orde de presentación.

    Con perfil: máis compatibles primeiro; a igualdade, urxentes e despois máis preto.
    Sen perfil: urxentes primeiro e despois máis preto (e máis recentes).
    """

    def clave(avaliado):
        distancia = avaliado.distancia if avaliado.distancia is not None else float("inf")
        porcentaxe = avaliado.porcentaxe if avaliado.porcentaxe is not None else 0
        return (-porcentaxe, not avaliado.can.urxente, distancia, -avaliado.can.pk)

    return sorted(avaliados, key=clave)


def marcar_solicitados(request, avaliados):
    """Marca os cans para os que a persoa xa ten unha solicitude en curso."""
    from adopcions.models import Solicitude

    usuario = request.user
    if not (usuario.is_authenticated and usuario.es_adoptante):
        return avaliados
    solicitados = set(
        Solicitude.objects.filter(adoptante=usuario, estado__in=Solicitude.ACTIVAS).values_list(
            "can_id", flat=True
        )
    )
    for avaliado in avaliados:
        avaliado.solicitado = avaliado.can.pk in solicitados
    return avaliados


def cans_avaliados(request, filtros=None, excluir=()):
    """Cans publicados, filtrados, avaliados para a persoa e ordenados."""
    filtros = filtros or {}
    consulta = aplicar_filtros(cans_publicados(), filtros).exclude(pk__in=excluir)
    localizacion = almacen.localizacion_de(request)
    avaliados = marcar_solicitados(
        request, avaliar(consulta, almacen.perfil_de(request), localizacion)
    )
    distancia_max = filtros.get("distancia")
    if distancia_max and localizacion:
        avaliados = [
            a for a in avaliados if a.distancia is not None and a.distancia <= distancia_max
        ]
    return ordenar(avaliados)
