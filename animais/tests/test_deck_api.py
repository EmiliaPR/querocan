"""Probas da API do deck e do botón «Adoptar»."""

import json

import pytest
from django.test import Client
from django.urls import reverse

from adopcions.models import Descarte, Solicitude
from animais.api import CLAVE_CAN_PENDENTE

pytestmark = pytest.mark.django_db


def post_json(client, nome, datos):
    return client.post(reverse(nome), json.dumps(datos), content_type="application/json")


def ids(resposta):
    return [c["id"] for c in resposta.json()["cans"]]


def test_a_tanda_trae_os_datos_da_tarxeta(client, adoptante_con_perfil, crear_can):
    can = crear_can(etiquetas="Tranquila")
    client.force_login(adoptante_con_perfil)
    tarxeta = client.get(reverse("animais:api_deck")).json()["cans"][0]
    assert tarxeta["id"] == can.pk
    assert tarxeta["porcentaxe"] == 100
    assert tarxeta["etiquetas"] == ["Tranquila"]
    assert tarxeta["url_ficha"] == reverse("animais:ficha", args=[can.pk])
    assert {"icona", "texto", "encaixa"} <= set(tarxeta["motivos"][0])


def test_a_tanda_exclue_os_da_pila_e_os_xa_decididos(client, adoptante_con_perfil, crear_can):
    a, b, c = crear_can(nome="A"), crear_can(nome="B"), crear_can(nome="C")
    client.force_login(adoptante_con_perfil)
    post_json(client, "animais:api_decision", {"can": a.pk, "decision": "non"})
    post_json(client, "animais:api_decision", {"can": b.pk, "decision": "gustame"})
    assert ids(client.get(reverse("animais:api_deck"))) == [c.pk]
    assert ids(client.get(reverse("animais:api_deck") + f"?excluir={c.pk},x")) == []


def test_gustame_crea_a_solicitude(client, adoptante_con_perfil, crear_can):
    can = crear_can()
    client.force_login(adoptante_con_perfil)
    resposta = post_json(client, "animais:api_decision", {"can": can.pk, "decision": "gustame"})
    assert resposta.json()["ok"]
    assert Solicitude.objects.get().can == can


def test_gustame_sen_conta_manda_a_entrar_e_lembra_o_can(client, crear_can):
    can = crear_can()
    resposta = post_json(client, "animais:api_decision", {"can": can.pk, "decision": "gustame"})
    assert resposta.json()["redirixir"].startswith(reverse("contas:entrar"))
    assert client.session[CLAVE_CAN_PENDENTE] == can.pk


def test_gustame_sen_test_manda_ao_test(client, adoptante, crear_can):
    can = crear_can()
    client.force_login(adoptante)
    resposta = post_json(client, "animais:api_decision", {"can": can.pk, "decision": "gustame"})
    assert resposta.json()["redirixir"] == reverse("compatibilidade:test")


def test_gustame_dunha_protectora_e_403(client, protectora, crear_can):
    client.force_login(protectora.usuario)
    resposta = post_json(
        client, "animais:api_decision", {"can": crear_can().pk, "decision": "gustame"}
    )
    assert resposta.status_code == 403


def test_gustame_repetido_devolve_409(client, adoptante_con_perfil, crear_can):
    can = crear_can()
    client.force_login(adoptante_con_perfil)
    post_json(client, "animais:api_decision", {"can": can.pk, "decision": "gustame"})
    resposta = post_json(client, "animais:api_decision", {"can": can.pk, "decision": "gustame"})
    assert resposta.status_code == 409


def test_decision_non_valida(client, crear_can):
    resposta = post_json(client, "animais:api_decision", {"can": crear_can().pk, "decision": "x"})
    assert resposta.status_code == 400
    resposta = client.post(reverse("animais:api_decision"), "non é json", content_type="text/plain")
    assert resposta.status_code == 400


def test_descartes_de_visitante_van_na_sesion(client, crear_can):
    a, b = crear_can(), crear_can()
    post_json(client, "animais:api_decision", {"can": a.pk, "decision": "non"})
    assert ids(client.get(reverse("animais:api_deck"))) == [b.pk]
    post_json(client, "animais:api_desfacer", {"can": a.pk, "decision": "non"})
    assert set(ids(client.get(reverse("animais:api_deck")))) == {a.pk, b.pk}


def test_desfacer_descarte_e_solicitude(client, adoptante_con_perfil, crear_can):
    a, b = crear_can(), crear_can()
    client.force_login(adoptante_con_perfil)
    post_json(client, "animais:api_decision", {"can": a.pk, "decision": "non"})
    post_json(client, "animais:api_desfacer", {"can": a.pk, "decision": "non"})
    assert not Descarte.objects.exists()
    post_json(client, "animais:api_decision", {"can": b.pk, "decision": "gustame"})
    assert post_json(client, "animais:api_desfacer", {"can": b.pk, "decision": "gustame"}).json()[
        "ok"
    ]
    assert not Solicitude.objects.exists()


def test_desfacer_sen_nada_que_desfacer(client, adoptante_con_perfil, crear_can):
    can = crear_can()
    datos = {"can": can.pk, "decision": "gustame"}
    assert post_json(client, "animais:api_desfacer", datos).status_code == 400
    client.force_login(adoptante_con_perfil)
    assert post_json(client, "animais:api_desfacer", datos).status_code == 409


def test_desfacer_unha_solicitude_xa_tocada_devolve_409(
    client, adoptante_con_perfil, crear_can, crear_usuario, crear_perfil, protectora
):
    from adopcions import estados

    can = crear_can()
    client.force_login(adoptante_con_perfil)
    post_json(client, "animais:api_decision", {"can": can.pk, "decision": "gustame"})
    outra = crear_usuario()
    crear_perfil(outra)
    aceptada = estados.aceptar(estados.crear_solicitude(outra, can), protectora.usuario)
    estados.cancelar_aceptada(aceptada, protectora.usuario)  # a nosa pasa a en espera e volve
    resposta = post_json(client, "animais:api_desfacer", {"can": can.pk, "decision": "gustame"})
    assert resposta.status_code == 409


def test_post_sen_csrf_e_403(crear_can):
    client = Client(enforce_csrf_checks=True)
    resposta = post_json(client, "animais:api_decision", {"can": crear_can().pk, "decision": "non"})
    assert resposta.status_code == 403


def test_a_paxina_do_deck(client):
    html = client.get(reverse("animais:deck")).content.decode()
    assert 'data-deck-accion="gustame"' in html
    assert "csrfmiddlewaretoken" in html


# --- Botón «Adoptar» e continuación tras entrar ---------------------------------------


def test_adoptar_desde_a_ficha(client, adoptante_con_perfil, crear_can):
    can = crear_can()
    client.force_login(adoptante_con_perfil)
    url_ficha = reverse("animais:ficha", args=[can.pk])
    resposta = client.post(reverse("adopcions:solicitar", args=[can.pk]), {"volver": url_ficha})
    assert resposta.url == url_ficha
    assert Solicitude.objects.filter(can=can).exists()


def test_visitante_adopta_entra_e_a_solicitude_crease(client, adoptante_con_perfil, crear_can):
    from conftest import CONTRASINAL

    can = crear_can()
    resposta = client.post(reverse("adopcions:solicitar", args=[can.pk]))
    assert "next=" + reverse("adopcions:continuar") in resposta.url
    resposta = client.post(
        resposta.url,
        {"username": adoptante_con_perfil.email, "password": CONTRASINAL},
        follow=True,
    )
    assert Solicitude.objects.filter(adoptante=adoptante_con_perfil, can=can).exists()
    assert "Enviamos a túa solicitude" in resposta.content.decode()


def test_adoptante_sen_test_fai_o_test_e_continua(client, adoptante, crear_can):
    from compatibilidade.tests.test_test import RESPOSTAS

    can = crear_can()
    client.force_login(adoptante)
    resposta = client.post(reverse("adopcions:solicitar", args=[can.pk]))
    assert resposta.url == reverse("compatibilidade:test")
    resposta = client.post(reverse("compatibilidade:test"), RESPOSTAS)
    assert resposta.url == reverse("adopcions:continuar")
    client.get(resposta.url)
    assert Solicitude.objects.filter(adoptante=adoptante, can=can).exists()


def test_continuar_sen_can_pendente_vai_ao_deck(client, adoptante_con_perfil):
    client.force_login(adoptante_con_perfil)
    assert client.get(reverse("adopcions:continuar")).url == reverse("animais:deck")
    session = client.session
    session[CLAVE_CAN_PENDENTE] = 999999
    session.save()
    assert client.get(reverse("adopcions:continuar")).url == reverse("animais:deck")


def test_adoptar_un_can_xa_reservado_avisa(client, adoptante_con_perfil, crear_can):
    can = crear_can(estado="reservado")
    client.force_login(adoptante_con_perfil)
    resposta = client.post(reverse("adopcions:solicitar", args=[can.pk]), follow=True)
    assert "xa non está dispoñible" in resposta.content.decode()


def test_unha_protectora_non_pode_adoptar(client, protectora, crear_can):
    client.force_login(protectora.usuario)
    assert client.post(reverse("adopcions:solicitar", args=[crear_can().pk])).status_code == 403
