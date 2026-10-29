"""Probas de rexistro, entrada, saída e control de acceso por rol."""

import pytest
from django.core.management import call_command
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse

from conftest import CONTRASINAL
from contas.decoradores import require_rol
from contas.models import Usuario

pytestmark = pytest.mark.django_db


def test_rexistro_dunha_adoptante_crea_a_conta_e_entra(client):
    resposta = client.post(
        reverse("contas:rexistro"),
        {
            "nome": "Uxía",
            "email": "Uxia@Exemplo.gal",
            "password": CONTRASINAL,
            "rol": "adoptante",
            "acepta_privacidade": "on",
        },
    )
    usuario = Usuario.objects.get(email="uxia@exemplo.gal")
    assert usuario.rol == Usuario.Rol.ADOPTANTE
    assert resposta.status_code == 302
    assert resposta.url == reverse("animais:deck")
    assert client.session["_auth_user_id"] == str(usuario.pk)


def test_rexistro_dunha_protectora_vai_ao_segundo_paso(client):
    resposta = client.post(
        reverse("contas:rexistro"),
        {
            "nome": "Os Palleiros",
            "email": "palleiros@exemplo.gal",
            "password": CONTRASINAL,
            "rol": "protectora",
            "acepta_privacidade": "on",
        },
    )
    assert resposta.url == reverse("contas:alta_protectora")


def test_rexistro_require_aceptar_a_privacidade(client):
    resposta = client.post(
        reverse("contas:rexistro"),
        {"nome": "X", "email": "x@exemplo.gal", "password": CONTRASINAL, "rol": "adoptante"},
    )
    assert resposta.status_code == 200
    assert "política de privacidade" in resposta.content.decode()
    assert not Usuario.objects.filter(email="x@exemplo.gal").exists()


def test_rexistro_non_permite_escoller_o_rol_superadmin(client):
    client.post(
        reverse("contas:rexistro"),
        {
            "nome": "Intrusa",
            "email": "intrusa@exemplo.gal",
            "password": CONTRASINAL,
            "rol": "superadmin",
            "acepta_privacidade": "on",
        },
    )
    assert not Usuario.objects.filter(email="intrusa@exemplo.gal").exists()


def test_rexistro_rexeita_correo_duplicado(client, adoptante):
    resposta = client.post(
        reverse("contas:rexistro"),
        {
            "nome": "Outra",
            "email": adoptante.email.upper(),
            "password": CONTRASINAL,
            "rol": "adoptante",
            "acepta_privacidade": "on",
        },
    )
    assert "Xa hai unha conta con ese correo" in resposta.content.decode()


def test_rexistro_rexeita_contrasinal_feble(client):
    resposta = client.post(
        reverse("contas:rexistro"),
        {
            "nome": "Feble",
            "email": "feble@exemplo.gal",
            "password": "1234",
            "rol": "adoptante",
            "acepta_privacidade": "on",
        },
    )
    assert resposta.status_code == 200
    assert not Usuario.objects.filter(email="feble@exemplo.gal").exists()


@pytest.mark.parametrize(
    ("rol", "destino"),
    [
        (Usuario.Rol.ADOPTANTE, "animais:deck"),
        (Usuario.Rol.PROTECTORA, "animais:protectora_cans"),
        (Usuario.Rol.SUPERADMIN, "xestion:inicio"),
    ],
)
def test_entrar_redirixe_segundo_o_rol(client, crear_usuario, rol, destino):
    usuario = crear_usuario(rol)
    resposta = client.post(
        reverse("contas:entrar"), {"username": usuario.email, "password": CONTRASINAL}
    )
    assert resposta.status_code == 302
    assert resposta.url == reverse(destino)


def test_entrar_respecta_next_interno_pero_non_externo(client, adoptante):
    datos = {"username": adoptante.email, "password": CONTRASINAL}
    resposta = client.post(reverse("contas:entrar") + "?next=/test/", datos)
    assert resposta.url == "/test/"
    client.logout()
    resposta = client.post(reverse("contas:entrar") + "?next=https://malicioso.example/", datos)
    assert resposta.url == reverse("animais:deck")


def test_entrar_con_contrasinal_incorrecto_amosa_erro(client, adoptante):
    resposta = client.post(
        reverse("contas:entrar"), {"username": adoptante.email, "password": "mal"}
    )
    assert resposta.status_code == 200
    assert "non son correctos" in resposta.content.decode()


def test_unha_conta_desactivada_non_pode_entrar(client, adoptante):
    adoptante.is_active = False
    adoptante.save()
    resposta = client.post(
        reverse("contas:entrar"), {"username": adoptante.email, "password": CONTRASINAL}
    )
    assert resposta.status_code == 200
    assert "_auth_user_id" not in client.session


def test_sair_pecha_a_sesion(client, adoptante):
    client.force_login(adoptante)
    resposta = client.post(reverse("contas:sair"))
    assert resposta.status_code == 302
    assert "_auth_user_id" not in client.session


def test_recuperar_contrasinal_envia_un_correo(client, adoptante, mailoutbox):
    client.post(reverse("contas:recuperar"), {"email": adoptante.email})
    assert len(mailoutbox) == 1
    assert "contrasinal" in mailoutbox[0].subject


# --- Decorador require_rol -------------------------------------------------------------


@require_rol(Usuario.Rol.PROTECTORA)
def _vista_so_protectoras(request):
    return HttpResponse("ok")


@pytest.mark.parametrize(
    ("rol", "esperado"),
    [
        (Usuario.Rol.PROTECTORA, 200),
        (Usuario.Rol.ADOPTANTE, 403),
        (Usuario.Rol.SUPERADMIN, 403),
    ],
)
def test_require_rol_segundo_o_rol(crear_usuario, rol, esperado):
    from django.core.exceptions import PermissionDenied

    request = RequestFactory().get("/privado/")
    request.user = crear_usuario(rol)
    if esperado == 200:
        assert _vista_so_protectoras(request).status_code == 200
    else:
        with pytest.raises(PermissionDenied):
            _vista_so_protectoras(request)


def test_require_rol_manda_ao_login_a_quen_non_entrou():
    from django.contrib.auth.models import AnonymousUser

    request = RequestFactory().get("/privado/")
    request.user = AnonymousUser()
    resposta = _vista_so_protectoras(request)
    assert resposta.status_code == 302
    assert "/entrar/?next=/privado/" in resposta.url


@pytest.mark.parametrize("url", ["/xestion/", "/protectora/cans/"])
def test_vistas_privadas_dan_403_a_unha_adoptante(client, adoptante, url):
    client.force_login(adoptante)
    assert client.get(url).status_code == 403


def test_createsuperuser_asigna_o_rol_superadmin(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", CONTRASINAL)
    call_command(
        "createsuperuser", "--noinput", email="admin@exemplo.gal", nome="Admin", verbosity=0
    )
    admin = Usuario.objects.get(email="admin@exemplo.gal")
    assert admin.rol == Usuario.Rol.SUPERADMIN
    assert admin.is_superuser
