"""Probas das páxinas públicas de contido e da landing completa."""

import pytest
from django.urls import reverse

from contido.models import Testemuno

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "nome", ["finais_felices", "enlaces", "protectoras", "manual", "privacidade", "contacto"]
)
def test_paxinas_publicas(client, nome):
    assert client.get(reverse(f"contido:{nome}")).status_code == 200


def test_a_landing_amosa_cans_e_testemuños(client, crear_can):
    crear_can(nome="Luna")
    Testemuno.objects.create(nome_persoa="Marta", nome_can="Russ", texto="Grazas!")
    html = client.get("/").content.decode()
    assert "Luna," in html
    assert "Grazas!" in html
    assert "Apadriñar" in html and "data-non-implementado" in html


def test_a_landing_sen_cans(client):
    assert "Axiña haberá cans" in client.get("/").content.decode()


def test_protectoras_amosa_so_as_activas_e_conta_cans(client, crear_protectora, crear_can):
    activa = crear_protectora(nome="Os Palleiros")
    crear_can(protectora=activa)
    crear_protectora(nome="Pendente", estado="pendente")
    html = client.get(reverse("contido:protectoras")).content.decode()
    assert "Os Palleiros" in html and "1 can dispoñible" in html
    assert "Pendente" not in html


def test_o_manual_inclue_os_compromisos_clave(client):
    html = client.get(reverse("contido:manual")).content.decode()
    assert "Exercicio, todos os días" in html and "Identificación" in html


def test_contacto_usa_o_correo_configurado(client, settings):
    settings.CONTACTO_EMAIL = "proba@querocan.gal"
    assert "proba@querocan.gal" in client.get(reverse("contido:contacto")).content.decode()


def test_ningunha_plantilla_di_apadrinar_sen_ñ():
    from pathlib import Path

    from django.conf import settings

    for plantilla in Path(settings.BASE_DIR).rglob("*.html"):
        if "docs" in plantilla.parts:
            continue
        assert "Apadrinar" not in plantilla.read_text(), plantilla
