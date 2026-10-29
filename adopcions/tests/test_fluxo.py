"""
Probas das pantallas do fluxo de adopción: panel da protectora, solicitudes da
persoa adoptante, checklist, contrato, PDF e caducidade. Inclúe o fluxo completo de
punta a punta (criterio de éxito 2 da SPEC).
"""

import hashlib
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from adopcions import estados
from adopcions.contrato import nif_valido, texto_final
from adopcions.models import (
    AceptacionContrato,
    ContratoInmutable,
    ItemChecklist,
    ModeloContrato,
    Solicitude,
)
from animais.models import Can
from conftest import CONTRASINAL

pytestmark = pytest.mark.django_db

DATOS_CONTRATO = {
    "nome": "Uxía Rivas",
    "nif": "12345678z",
    "enderezo": "Rúa do Príncipe 1, Vigo",
    "telefono": "600 111 222",
    "email": "uxia@exemplo.gal",
    "acepto": "on",
}


@pytest.fixture
def solicitude(adoptante_con_perfil, crear_can):
    return estados.crear_solicitude(adoptante_con_perfil, crear_can())


@pytest.fixture
def aceptada(solicitude, protectora):
    return estados.aceptar(solicitude, protectora.usuario)


def checklist_completo():
    return {f"item_{item.pk}": "on" for item in ItemChecklist.objects.filter(activo=True)}


# --- Panel da protectora --------------------------------------------------------------


def test_panel_amosa_compatibilidade_motivos_e_outras_solicitudes(
    client, protectora, solicitude, crear_can, crear_protectora
):
    outra_protectora = crear_protectora()
    estados.crear_solicitude(solicitude.adoptante, crear_can(protectora=outra_protectora))
    client.force_login(protectora.usuario)
    html = client.get(reverse("adopcions:protectora_solicitudes")).content.decode()
    assert solicitude.adoptante.nome in html
    assert "100%" in html
    assert "Adáptase á túa vivenda" in html
    assert "ten outras 1 solicitude activa" in html


def test_aceptar_desde_o_panel(client, protectora, solicitude, crear_usuario, crear_perfil):
    outra = crear_usuario()
    crear_perfil(outra)
    en_espera = estados.crear_solicitude(outra, solicitude.can)
    client.force_login(protectora.usuario)
    client.post(reverse("adopcions:protectora_accion", args=[solicitude.pk, "aceptar"]))
    solicitude.refresh_from_db()
    en_espera.refresh_from_db()
    assert solicitude.estado == Solicitude.Estado.ACEPTADA
    assert en_espera.estado == Solicitude.Estado.EN_ESPERA
    html = client.get(reverse("adopcions:protectora_solicitudes")).content.decode()
    assert "En espera" in html and "Cancelar a adopción" in html


def test_panel_filtra_por_can_e_estado(client, protectora, solicitude, crear_can):
    outro = estados.crear_solicitude(solicitude.adoptante, crear_can(nome="Outro"))
    estados.rexeitar(outro, protectora.usuario)
    client.force_login(protectora.usuario)
    url = reverse("adopcions:protectora_solicitudes")
    assert "→ Outro" not in client.get(url).content.decode()
    assert "→ Outro" in client.get(url + "?estado=rexeitada").content.decode()
    html = client.get(url + f"?estado=todas&can={solicitude.can_id}").content.decode()
    assert "→ Outro" not in html


def test_unha_protectora_non_actua_sobre_solicitudes_alleas(client, solicitude, crear_protectora):
    client.force_login(crear_protectora().usuario)
    url = reverse("adopcions:protectora_accion", args=[solicitude.pk, "aceptar"])
    assert client.post(url).status_code == 404


def test_accion_descoñecida_ou_invalida(client, protectora, solicitude):
    client.force_login(protectora.usuario)
    client.post(reverse("adopcions:protectora_accion", args=[solicitude.pk, "borrar"]))
    resposta = client.post(
        reverse("adopcions:protectora_accion", args=[solicitude.pk, "cancelar"]), follow=True
    )
    assert "Non se pode facer isto" in resposta.content.decode()
    solicitude.refresh_from_db()
    assert solicitude.estado == Solicitude.Estado.PENDENTE


def test_panel_non_rompe_a_390_px_require_viewport(client, protectora):
    client.force_login(protectora.usuario)
    html = client.get(reverse("adopcions:protectora_solicitudes")).content.decode()
    assert 'name="viewport"' in html


# --- As miñas solicitudes -------------------------------------------------------------


def test_minas_solicitudes_amosa_estado_e_dias_restantes(client, aceptada):
    client.force_login(aceptada.adoptante)
    html = client.get(reverse("adopcions:minas_solicitudes")).content.decode()
    assert "Match!" in html
    assert "Quédanche <strong>7 días</strong>" in html
    assert reverse("adopcions:checklist", args=[aceptada.pk]) in html


def test_retirar_unha_pendente(client, solicitude):
    client.force_login(solicitude.adoptante)
    client.post(reverse("adopcions:retirar", args=[solicitude.pk]))
    solicitude.refresh_from_db()
    assert solicitude.estado == Solicitude.Estado.CANCELADA


def test_cancelar_unha_aceptada_desde_as_miñas_solicitudes(client, aceptada):
    client.force_login(aceptada.adoptante)
    client.post(reverse("adopcions:retirar", args=[aceptada.pk]))
    aceptada.refresh_from_db()
    assert aceptada.estado == Solicitude.Estado.CANCELADA
    assert aceptada.can.estado == Can.Estado.DISPONIBLE


def test_retirar_unha_pechada_avisa(client, solicitude):
    estados.retirar(solicitude, solicitude.adoptante)
    client.force_login(solicitude.adoptante)
    resposta = client.post(reverse("adopcions:retirar", args=[solicitude.pk]), follow=True)
    assert "Non se pode facer isto" in resposta.content.decode()


def test_non_se_ven_solicitudes_doutras_persoas(client, solicitude, crear_usuario):
    client.force_login(crear_usuario())
    assert client.post(reverse("adopcions:retirar", args=[solicitude.pk])).status_code == 404


def test_sen_solicitudes(client, adoptante):
    client.force_login(adoptante)
    assert (
        "Aínda non solicitaches"
        in client.get(reverse("adopcions:minas_solicitudes")).content.decode()
    )


# --- Checklist ------------------------------------------------------------------------


def test_checklist_require_todos_os_compromisos(client, aceptada, datos_adopcion):
    client.force_login(aceptada.adoptante)
    url = reverse("adopcions:checklist", args=[aceptada.pk])
    datos = checklist_completo()
    datos.popitem()
    resposta = client.post(url, datos)
    assert "tes que aceptar todos" in resposta.content.decode()
    aceptada.refresh_from_db()
    assert not aceptada.checklist_feito
    resposta = client.post(url, checklist_completo())
    assert resposta.url == reverse("adopcions:contrato", args=[aceptada.pk])
    # Unha vez feito, volver ao checklist leva ao contrato
    assert client.get(url).url == reverse("adopcions:contrato", args=[aceptada.pk])


def test_checklist_dunha_non_aceptada(client, solicitude, datos_adopcion):
    client.force_login(solicitude.adoptante)
    resposta = client.get(reverse("adopcions:checklist", args=[solicitude.pk]))
    assert resposta.url == reverse("adopcions:minas_solicitudes")


# --- Contrato -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nif", "valido"),
    [
        ("12345678Z", True),
        ("12345678A", False),
        ("X1234567L", True),
        ("Y1234567X", True),
        ("1234", False),
        ("12345678-z", True),
    ],
)
def test_nif_valido(nif, valido):
    assert nif_valido(nif) is valido


def test_contrato_sen_checklist_vai_ao_checklist(client, aceptada, datos_adopcion):
    client.force_login(aceptada.adoptante)
    resposta = client.get(reverse("adopcions:contrato", args=[aceptada.pk]))
    assert resposta.url == reverse("adopcions:checklist", args=[aceptada.pk])


def test_contrato_dunha_non_aceptada(client, solicitude, datos_adopcion):
    client.force_login(solicitude.adoptante)
    resposta = client.get(reverse("adopcions:contrato", args=[solicitude.pk]))
    assert resposta.url == reverse("adopcions:minas_solicitudes")


def test_contrato_amosa_o_texto_cos_datos(client, aceptada, datos_adopcion):
    estados.completar_checklist(aceptada, aceptada.adoptante)
    client.force_login(aceptada.adoptante)
    html = client.get(reverse("adopcions:contrato", args=[aceptada.pk])).content.decode()
    assert aceptada.can.nome in html
    assert aceptada.can.protectora.nome in html
    assert "{can}" not in html


def test_aceptar_contrato_completa_a_adopcion_e_garda_o_hash(client, aceptada, datos_adopcion):
    estados.completar_checklist(aceptada, aceptada.adoptante)
    client.force_login(aceptada.adoptante)
    resposta = client.post(reverse("adopcions:contrato", args=[aceptada.pk]), DATOS_CONTRATO)
    assert resposta.url == reverse("adopcions:adopcion_completada", args=[aceptada.pk])
    aceptada.refresh_from_db()
    assert aceptada.estado == Solicitude.Estado.COMPLETADA
    assert aceptada.can.estado == Can.Estado.ADOPTADO
    aceptacion = AceptacionContrato.objects.get(solicitude=aceptada)
    assert aceptacion.nif == "12345678Z"
    assert aceptacion.telefono == "600111222"
    assert "Uxía Rivas" in aceptacion.texto_final
    esperado = hashlib.sha256(aceptacion.texto_final.encode()).hexdigest()
    assert aceptacion.hash_sha256 == esperado
    # Volver ao contrato leva á páxina de parabéns
    assert client.get(reverse("adopcions:contrato", args=[aceptada.pk])).url == resposta.url
    assert "Parabéns!" in client.get(resposta.url).content.decode()


def test_contrato_con_nif_incorrecto(client, aceptada, datos_adopcion):
    estados.completar_checklist(aceptada, aceptada.adoptante)
    client.force_login(aceptada.adoptante)
    resposta = client.post(
        reverse("adopcions:contrato", args=[aceptada.pk]), {**DATOS_CONTRATO, "nif": "12345678A"}
    )
    assert "non é válido" in resposta.content.decode()
    assert not AceptacionContrato.objects.exists()


def test_contrato_con_telefono_incorrecto(client, aceptada, datos_adopcion):
    estados.completar_checklist(aceptada, aceptada.adoptante)
    client.force_login(aceptada.adoptante)
    resposta = client.post(
        reverse("adopcions:contrato", args=[aceptada.pk]), {**DATOS_CONTRATO, "telefono": "abc"}
    )
    assert "teléfono válido" in resposta.content.decode()


def test_sen_modelo_activo_non_se_completa(client, aceptada, datos_adopcion):
    estados.completar_checklist(aceptada, aceptada.adoptante)
    ModeloContrato.objects.update(activo=False)
    client.force_login(aceptada.adoptante)
    resposta = client.post(
        reverse("adopcions:contrato", args=[aceptada.pk]), DATOS_CONTRATO, follow=True
    )
    assert "Non hai ningún modelo de contrato activo" in resposta.content.decode()
    aceptada.refresh_from_db()
    assert aceptada.estado == Solicitude.Estado.ACEPTADA


def test_a_aceptacion_non_se_pode_modificar_nin_borrar(client, aceptada, datos_adopcion):
    estados.completar_checklist(aceptada, aceptada.adoptante)
    client.force_login(aceptada.adoptante)
    client.post(reverse("adopcions:contrato", args=[aceptada.pk]), DATOS_CONTRATO)
    aceptacion = AceptacionContrato.objects.get()
    aceptacion.texto_final = "Texto cambiado"
    with pytest.raises(ContratoInmutable):
        aceptacion.save()
    with pytest.raises(ContratoInmutable):
        aceptacion.delete()


def test_pdf_do_contrato(client, aceptada, datos_adopcion, crear_usuario):
    estados.completar_checklist(aceptada, aceptada.adoptante)
    client.force_login(aceptada.adoptante)
    client.post(reverse("adopcions:contrato", args=[aceptada.pk]), DATOS_CONTRATO)
    url = reverse("adopcions:contrato_pdf", args=[aceptada.pk])
    resposta = client.get(url)
    assert resposta["Content-Type"] == "application/pdf"
    assert resposta.content.startswith(b"%PDF")
    # A protectora tamén pode descargalo; outra persoa, non
    client.force_login(aceptada.can.protectora.usuario)
    assert client.get(url).status_code == 200
    client.force_login(crear_usuario())
    assert client.get(url).status_code == 403


def test_texto_final_substitue_todos_os_marcadores(aceptada, datos_adopcion):
    texto = texto_final(ModeloContrato.actual(), aceptada, {**DATOS_CONTRATO, "nif": "1Z"})
    assert "{" not in texto


# --- Caducidade -----------------------------------------------------------------------


def test_comando_expirar_solicitudes(aceptada, capsys):
    Solicitude.objects.filter(pk=aceptada.pk).update(
        data_aceptacion=timezone.now() - timedelta(days=8)
    )
    call_command("expirar_solicitudes")
    assert "Solicitudes caducadas: 1" in capsys.readouterr().out
    aceptada.refresh_from_db()
    assert aceptada.estado == Solicitude.Estado.CADUCADA
    call_command("expirar_solicitudes")
    assert "Solicitudes caducadas: 0" in capsys.readouterr().out


# --- Fluxo completo -------------------------------------------------------------------


def test_fluxo_completo_de_punta_a_punta(
    client, protectora, crear_can, datos_adopcion, mailoutbox, django_capture_on_commit_callbacks
):
    """Test sen conta → crear conta → swipe → match → checklist → contrato → PDF."""
    with django_capture_on_commit_callbacks(execute=True):
        _fluxo_completo(client, protectora, crear_can)
    asuntos = " ".join(m.subject for m in mailoutbox)
    assert "nova solicitude" in asuntos and "aceptou" in asuntos and "completada" in asuntos


def _fluxo_completo(client, protectora, crear_can):
    import json

    can = crear_can(nome="Luna")

    # 1. Unha visitante fai o test e crea a conta
    client.post(
        reverse("compatibilidade:test"),
        {
            "vivenda": "casa_con_patio",
            "tamano": "mediano",
            "horas_so": "menos_de_2",
            "ten_nenos": "non",
            "outros_animais": "ningun",
            "actividade": "medio",
            "experiencia": "si",
        },
    )
    client.post(
        reverse("contas:rexistro"),
        {
            "nome": "Uxía",
            "email": "uxia@exemplo.gal",
            "password": CONTRASINAL,
            "rol": "adoptante",
            "acepta_privacidade": "on",
        },
    )

    # 2. Desliza á dereita no deck
    tarxeta = client.get(reverse("animais:api_deck")).json()["cans"][0]
    assert tarxeta["nome"] == "Luna" and tarxeta["porcentaxe"] == 100
    client.post(
        reverse("animais:api_decision"),
        json.dumps({"can": can.pk, "decision": "gustame"}),
        content_type="application/json",
    )
    solicitude = Solicitude.objects.get(can=can)

    # 3. A protectora acepta desde o seu panel
    adoptante = client.session["_auth_user_id"]
    client.force_login(protectora.usuario)
    client.post(reverse("adopcions:protectora_accion", args=[solicitude.pk, "aceptar"]))

    # 4. A adoptante completa o checklist e o contrato
    client.force_login(solicitude.adoptante)
    assert str(solicitude.adoptante.pk) == adoptante
    client.post(reverse("adopcions:checklist", args=[solicitude.pk]), checklist_completo())
    client.post(reverse("adopcions:contrato", args=[solicitude.pk]), DATOS_CONTRATO)

    # 5. Todo quedou rexistrado e o PDF descárgase
    solicitude.refresh_from_db()
    can.refresh_from_db()
    assert solicitude.estado == Solicitude.Estado.COMPLETADA
    assert can.estado == Can.Estado.ADOPTADO
    assert (
        client.get(reverse("adopcions:contrato_pdf", args=[solicitude.pk])).content[:4] == b"%PDF"
    )
    assert list(solicitude.historial.values_list("estado_novo", flat=True)) == [
        "pendente",
        "aceptada",
        "aceptada",
        "completada",
    ]
