"""Probas do comando cargar_demo: idempotente e coa orde de compatibilidade esperada."""

import pytest
from django.core.management import call_command

from adopcions.models import Solicitude
from animais.models import Can, FotoCan
from contas.models import Protectora, Usuario
from querocan.management.commands.cargar_demo import DOMINIO

pytestmark = pytest.mark.django_db


@pytest.fixture
def demo():
    call_command("cargar_demo", stdout=open("/dev/null", "w"))


def test_crea_os_datos_e_e_idempotente(demo):
    contas = Usuario.objects.filter(email__endswith=DOMINIO).count()
    call_command("cargar_demo", stdout=open("/dev/null", "w"))
    assert Usuario.objects.filter(email__endswith=DOMINIO).count() == contas == 8
    assert Can.objects.count() == 30
    assert FotoCan.objects.count() == 30
    assert Protectora.objects.filter(estado=Protectora.Estado.ACTIVA).count() == 3
    assert Solicitude.objects.count() == 8


def test_o_funil_ten_datos_en_todas_as_etapas(demo):
    from xestion.metricas import funil

    datos = funil()
    assert all(etapa["total"] > 0 for etapa in datos["etapas"])
    assert all(peche["total"] > 0 for peche in datos["peches"])


def _top3(persoa):
    from animais.consultas import avaliar
    from contas.models import PerfilAdoptante

    perfil = PerfilAdoptante.objects.get(usuario__email=f"{persoa}@{DOMINIO}").como_perfil()
    avaliados = sorted(avaliar(Can.objects.all(), perfil), key=lambda a: -a.porcentaxe)
    return [a.can for a in avaliados[:3]]


def test_top_3_da_estudante_en_piso(demo):
    """Pasa 4–6 horas fóra: os primeiros cans toleran ben a soidade e non son grandes."""
    for can in _top3("estudante"):
        assert can.tolerancia_soidade == "alta" and can.tamano != "grande", can.nome


def test_top_3_da_familia_con_nenos(demo):
    """Hai nenos e outro can na casa: os primeiros conviven con ambos."""
    for can in _top3("familia"):
        assert can.convive_nenos == "si" and can.convive_cans == "si", can.nome


def test_top_3_da_xubilada(demo):
    """Tranquila e con gatos: os primeiros son de enerxía baixa e conviven con gatos."""
    for can in _top3("xubilada"):
        assert can.enerxia == "baixo" and can.convive_gatos == "si", can.nome
