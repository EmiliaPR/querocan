"""Probas do alta de protectoras e da súa validación polo superadmin."""

import pytest
from django.urls import reverse

from contas.models import Protectora

pytestmark = pytest.mark.django_db


def datos_protectora(concello, **cambios):
    datos = {
        "nome": "Os Palleiros",
        "cif": "g-36123456",
        "concello": concello.pk,
        "telefono": "986111222",
        "email_contacto": "ola@palleiros.gal",
    }
    datos.update(cambios)
    return datos


def test_alta_de_protectora_queda_pendente_e_avisa_ao_superadmin(
    client, usuario_protectora, superadmin, concello, mailoutbox
):
    client.force_login(usuario_protectora)
    resposta = client.post(reverse("contas:alta_protectora"), datos_protectora(concello))
    assert resposta.status_code == 302
    protectora = Protectora.objects.get(usuario=usuario_protectora)
    assert protectora.estado == Protectora.Estado.PENDENTE_VALIDACION
    assert protectora.cif == "G36123456"
    assert mailoutbox[0].to == [superadmin.email]


def test_cif_invalido_rexeitase(client, usuario_protectora, concello):
    client.force_login(usuario_protectora)
    resposta = client.post(reverse("contas:alta_protectora"), datos_protectora(concello, cif="123"))
    assert resposta.status_code == 200
    assert not Protectora.objects.exists()


def test_unha_adoptante_non_pode_dar_de_alta_unha_protectora(client, adoptante):
    client.force_login(adoptante)
    assert client.get(reverse("contas:alta_protectora")).status_code == 403


def test_protectora_sen_datos_vai_ao_alta(client, usuario_protectora):
    client.force_login(usuario_protectora)
    resposta = client.get(reverse("animais:protectora_cans"))
    assert resposta.url == reverse("contas:alta_protectora")


def test_protectora_pendente_non_accede_a_xestion_de_cans(client, crear_protectora):
    pendente = crear_protectora(estado=Protectora.Estado.PENDENTE_VALIDACION)
    client.force_login(pendente.usuario)
    resposta = client.get(reverse("animais:protectora_cans"))
    assert resposta.status_code == 200
    assert "Pendente de validación" in resposta.content.decode()
    assert "Os meus cans" not in resposta.content.decode().split("<main")[1]


def test_protectora_activa_accede_a_xestion_de_cans(client, protectora):
    client.force_login(protectora.usuario)
    resposta = client.get(reverse("animais:protectora_cans"))
    assert resposta.status_code == 200
    assert "Pendente de validación" not in resposta.content.decode()


def test_o_superadmin_ve_a_cola_de_pendentes(client, superadmin, crear_protectora):
    pendente = crear_protectora(estado=Protectora.Estado.PENDENTE_VALIDACION, nome="Pendente")
    crear_protectora(nome="Xa activa")
    client.force_login(superadmin)
    html = client.get(reverse("xestion:protectoras")).content.decode()
    assert pendente.nome in html
    assert "Xa activa" not in html


@pytest.mark.parametrize(
    ("accion", "estado_final"),
    [
        ("validar", Protectora.Estado.ACTIVA),
        ("rexeitar", Protectora.Estado.REXEITADA),
        ("desactivar", Protectora.Estado.DESACTIVADA),
    ],
)
def test_o_superadmin_cambia_o_estado_e_avisa(
    client, superadmin, crear_protectora, mailoutbox, accion, estado_final
):
    protectora = crear_protectora(estado=Protectora.Estado.PENDENTE_VALIDACION)
    client.force_login(superadmin)
    client.post(reverse("xestion:cambiar_estado_protectora", args=[protectora.pk, accion]))
    protectora.refresh_from_db()
    assert protectora.estado == estado_final
    assert mailoutbox[-1].to == [protectora.usuario.email]
    if accion == "validar":
        assert protectora.data_validacion is not None


def test_accion_descoñecida_non_cambia_nada(client, superadmin, crear_protectora):
    protectora = crear_protectora(estado=Protectora.Estado.PENDENTE_VALIDACION)
    client.force_login(superadmin)
    client.post(reverse("xestion:cambiar_estado_protectora", args=[protectora.pk, "borrar"]))
    protectora.refresh_from_db()
    assert protectora.estado == Protectora.Estado.PENDENTE_VALIDACION


def test_cambiar_estado_require_post_e_superadmin(client, adoptante, crear_protectora):
    protectora = crear_protectora(estado=Protectora.Estado.PENDENTE_VALIDACION)
    url = reverse("xestion:cambiar_estado_protectora", args=[protectora.pk, "validar"])
    client.force_login(adoptante)
    assert client.post(url).status_code == 403
