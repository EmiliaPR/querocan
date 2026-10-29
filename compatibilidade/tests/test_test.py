"""Probas do test de compatibilidade, do resultado e da localización."""

import pytest
from django.urls import reverse

from compatibilidade.perfil import CLAVE_LOCALIZACION, CLAVE_TEST
from conftest import CONTRASINAL
from contas.models import PerfilAdoptante

pytestmark = pytest.mark.django_db

RESPOSTAS = {
    "vivenda": "piso",
    "tamano": "pequeno",
    "horas_so": "de_2_a_4",
    "ten_nenos": "non",
    "outros_animais": "gatos",
    "actividade": "baixo",
    "experiencia": "si",
}


def test_o_test_ten_seis_preguntas(client):
    html = client.get(reverse("compatibilidade:test")).content.decode()
    assert html.count('data-pregunta="') == 6
    assert "Pregunta 2 de 6" in html


def test_visitante_fai_o_test_e_gardase_na_sesion(client):
    resposta = client.post(reverse("compatibilidade:test"), RESPOSTAS)
    assert resposta.url == reverse("compatibilidade:resultado")
    assert client.session[CLAVE_TEST]["vivenda"] == "piso"
    assert client.session[CLAVE_TEST]["ten_nenos"] is False


def test_respostas_incompletas_volven_ao_formulario(client):
    resposta = client.post(reverse("compatibilidade:test"), {"vivenda": "piso"})
    assert resposta.status_code == 200
    assert "Responde todas as preguntas" in resposta.content.decode()


def test_adoptante_garda_o_test_no_perfil(client, adoptante):
    client.force_login(adoptante)
    client.post(reverse("compatibilidade:test"), RESPOSTAS)
    perfil = PerfilAdoptante.objects.get(usuario=adoptante)
    assert perfil.outros_animais == "gatos"
    assert perfil.experiencia is True


def test_repetir_o_test_amosa_as_respostas_anteriores(client, adoptante_con_perfil):
    client.force_login(adoptante_con_perfil)
    html = client.get(reverse("compatibilidade:test")).content.decode()
    assert 'value="casa_con_patio" ' in html and "checked" in html


def test_protectora_non_fai_o_test(client, usuario_protectora):
    client.force_login(usuario_protectora)
    assert client.get(reverse("compatibilidade:test")).url == reverse("contido:landing")


def test_o_test_feito_sen_conta_pasa_ao_perfil_ao_crear_conta(client):
    client.post(reverse("compatibilidade:test"), RESPOSTAS)
    client.post(
        reverse("compatibilidade:localizacion"),
        {"latitude": "42.24", "lonxitude": "-8.72", "volver": "/"},
    )
    client.post(
        reverse("contas:rexistro"),
        {
            "nome": "Iria",
            "email": "iria@exemplo.gal",
            "password": CONTRASINAL,
            "rol": "adoptante",
            "acepta_privacidade": "on",
        },
    )
    perfil = PerfilAdoptante.objects.get(usuario__email="iria@exemplo.gal")
    assert perfil.vivenda == "piso"
    assert perfil.latitude == pytest.approx(42.24)
    assert CLAVE_TEST not in client.session


def test_o_test_feito_sen_conta_pasa_ao_perfil_ao_entrar(client, adoptante_con_perfil):
    client.post(reverse("compatibilidade:test"), RESPOSTAS)
    client.post(
        reverse("contas:entrar"), {"username": adoptante_con_perfil.email, "password": CONTRASINAL}
    )
    adoptante_con_perfil.perfil.refresh_from_db()
    assert adoptante_con_perfil.perfil.vivenda == "piso"  # o test máis recente gaña


def test_resultado_sen_test_vai_ao_test(client):
    assert client.get(reverse("compatibilidade:resultado")).url == reverse("compatibilidade:test")


def test_resultado_amosa_tres_cans_ordenados(client, crear_can):
    crear_can(nome="Encaixa", tamano="pequeno", enerxia="baixo", convive_gatos="si")
    crear_can(nome="Medio", tamano="mediano", enerxia="baixo", convive_gatos="si")
    crear_can(nome="Non", espazo="patio_necesario", convive_gatos="non")
    crear_can(nome="Cuarto", tamano="grande", enerxia="alto")
    client.post(reverse("compatibilidade:test"), RESPOSTAS)
    html = client.get(reverse("compatibilidade:resultado")).content.decode()
    assert html.index("Encaixa") < html.index("Medio")
    assert html.count('class="tarxeta resultado"') == 3
    assert "Garda o teu resultado" in html


# --- Localización ---------------------------------------------------------------------


def test_localizacion_por_concello(client, concello):
    client.post(
        reverse("compatibilidade:localizacion"), {"concello": concello.pk, "volver": "/animais/"}
    )
    assert client.session[CLAVE_LOCALIZACION]["descricion"] == "Vigo"


def test_localizacion_por_gps_na_conta(client, adoptante_con_perfil):
    client.force_login(adoptante_con_perfil)
    client.post(reverse("compatibilidade:localizacion"), {"latitude": "43.0", "lonxitude": "-8.0"})
    adoptante_con_perfil.perfil.refresh_from_db()
    assert adoptante_con_perfil.perfil.latitude == 43.0


def test_localizacion_baleira_avisa(client):
    resposta = client.post(reverse("compatibilidade:localizacion"), {}, follow=True)
    assert "Non puidemos gardar a localización" in resposta.content.decode()


def test_localizacion_non_redirixe_fora(client, concello):
    resposta = client.post(
        reverse("compatibilidade:localizacion"),
        {"concello": concello.pk, "volver": "https://malicioso.example/"},
    )
    assert resposta.url == "/"


def test_latitude_fora_de_rango_rexeitase(client):
    client.post(reverse("compatibilidade:localizacion"), {"latitude": "200", "lonxitude": "0"})
    assert CLAVE_LOCALIZACION not in client.session
