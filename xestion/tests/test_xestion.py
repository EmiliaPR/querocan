"""Probas do panel do superadmin: usuarios, funil, contido editable e contrato."""

from datetime import date, timedelta

import pytest
from django.urls import reverse

from adopcions import estados
from adopcions.models import AceptacionContrato, ItemChecklist, ModeloContrato
from contas.models import Protectora, Usuario
from contido.models import Enlace, Testemuno
from xestion import metricas

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "nome",
    [
        "xestion:inicio",
        "xestion:usuarios",
        "xestion:funil",
        "xestion:contrato",
        "xestion:protectoras",
    ],
)
def test_so_o_superadmin_entra(client, adoptante, usuario_protectora, superadmin, nome):
    url = reverse(nome)
    for persoa in (adoptante, usuario_protectora):
        client.force_login(persoa)
        assert client.get(url).status_code == 403
    client.force_login(superadmin)
    assert client.get(url).status_code == 200


def test_resumo_da_portada(client, superadmin, crear_protectora, crear_can):
    crear_protectora(estado=Protectora.Estado.PENDENTE_VALIDACION)
    crear_can()
    client.force_login(superadmin)
    html = client.get(reverse("xestion:inicio")).content.decode()
    assert "protectoras pendentes de validar" in html
    assert "cans dispoñibles" in html


# --- Usuarios -------------------------------------------------------------------------


def test_buscar_usuarios(client, superadmin, crear_usuario):
    crear_usuario(nome="Iria Castro", email="iria@exemplo.gal")
    crear_usuario(nome="Brais", email="brais@exemplo.gal")
    client.force_login(superadmin)
    html = client.get(reverse("xestion:usuarios") + "?q=iria").content.decode()
    assert "Iria Castro" in html and "Brais" not in html
    html = client.get(reverse("xestion:usuarios") + "?rol=superadmin").content.decode()
    assert "Iria Castro" not in html


def test_desactivar_usuario_e_non_pode_entrar(client, superadmin, adoptante):
    from conftest import CONTRASINAL

    client.force_login(superadmin)
    client.post(reverse("xestion:cambiar_activo_usuario", args=[adoptante.pk]))
    adoptante.refresh_from_db()
    assert not adoptante.is_active
    client.logout()
    client.post(reverse("contas:entrar"), {"username": adoptante.email, "password": CONTRASINAL})
    assert "_auth_user_id" not in client.session


def test_desactivar_unha_protectora_oculta_os_seus_cans(client, superadmin, protectora, crear_can):
    crear_can(nome="Oculto")
    client.force_login(superadmin)
    client.post(reverse("xestion:cambiar_activo_usuario", args=[protectora.usuario.pk]))
    protectora.refresh_from_db()
    assert protectora.estado == Protectora.Estado.DESACTIVADA
    assert "Oculto" not in client.get(reverse("animais:listado")).content.decode()


def test_non_se_pode_desactivar_a_propia_conta(client, superadmin):
    client.force_login(superadmin)
    resposta = client.post(
        reverse("xestion:cambiar_activo_usuario", args=[superadmin.pk]), follow=True
    )
    assert "propia conta" in resposta.content.decode()
    superadmin.refresh_from_db()
    assert superadmin.is_active


def test_reactivar_usuario(client, superadmin, adoptante):
    Usuario.objects.filter(pk=adoptante.pk).update(is_active=False)
    client.force_login(superadmin)
    client.post(reverse("xestion:cambiar_activo_usuario", args=[adoptante.pk]))
    adoptante.refresh_from_db()
    assert adoptante.is_active


# --- Funil ----------------------------------------------------------------------------


@pytest.fixture
def escenario(crear_can, crear_usuario, crear_perfil, protectora, crear_protectora):
    """4 solicitudes: 1 completada, 1 caducada... para comprobar as cifras do funil."""
    from django.core.management import call_command

    call_command("loaddata", "adopcion_inicial", verbosity=0)
    persoas = []
    for _ in range(4):
        persoa = crear_usuario()
        crear_perfil(persoa)
        persoas.append(persoa)
    can_a, can_b = crear_can(nome="A"), crear_can(nome="B")
    # Completada
    s1 = estados.crear_solicitude(persoas[0], can_a)
    estados.aceptar(s1, protectora.usuario)
    estados.completar_checklist(s1, persoas[0])
    estados.completar_adopcion(s1, persoas[0])
    # Rexeitada (o can xa foi adoptado mentres agardaba)
    estados.crear_solicitude(persoas[1], can_b)
    s3 = estados.crear_solicitude(persoas[2], can_b)
    estados.rexeitar(s3, protectora.usuario)
    # Doutra protectora, cancelada pola persoa
    outra = crear_protectora()
    s4 = estados.crear_solicitude(persoas[3], crear_can(protectora=outra, nome="C"))
    estados.retirar(s4, persoas[3])
    return {"protectora": protectora, "outra": outra}


def totais(datos):
    return {e["clave"]: e["total"] for e in datos["etapas"] + datos["peches"]}


def test_funil_global(escenario):
    assert totais(metricas.funil()) == {
        "solicitudes": 4,
        "aceptadas": 1,
        "checklist": 1,
        "completadas": 1,
        "rexeitadas": 1,
        "canceladas": 1,
        "caducadas": 0,
    }
    assert metricas.funil()["etapas"][1]["porcentaxe"] == 25


def test_funil_por_protectora_e_datas(escenario):
    assert totais(metricas.funil(escenario["outra"]))["solicitudes"] == 1
    manan = date.today() + timedelta(days=1)
    assert totais(metricas.funil(desde=manan))["solicitudes"] == 0
    assert totais(metricas.funil(ata=date.today()))["solicitudes"] == 4
    filas = metricas.funil_por_protectora([escenario["protectora"], escenario["outra"]])
    assert [f["etapas"][0]["total"] for f in filas] == [3, 1]


def test_funil_baleiro_non_divide_por_cero(db):
    assert metricas.funil()["etapas"][1]["porcentaxe"] == 0


def test_paxina_do_funil_ten_grafica_e_taboa(client, superadmin, escenario):
    client.force_login(superadmin)
    html = client.get(reverse("xestion:funil")).content.decode()
    assert 'id="grafica-funil"' in html
    assert 'id="datos-funil"' in html
    assert "<caption" in html and "Adopcións completadas" in html
    html = client.get(
        reverse("xestion:funil") + f"?protectora={escenario['outra'].pk}"
    ).content.decode()
    assert escenario["outra"].nome in html


# --- Contido editable -----------------------------------------------------------------


def test_crear_editar_e_borrar_un_testemuno(client, superadmin):
    client.force_login(superadmin)
    client.post(
        reverse("xestion:contido_novo", args=["testemunos"]),
        {
            "nome_persoa": "Rosa (67 anos)",
            "nome_can": "Pupa",
            "texto": "Somos felices.",
            "publicado": "on",
            "orde": 1,
        },
    )
    testemuno = Testemuno.objects.get()
    assert "Somos felices" in client.get(reverse("contido:finais_felices")).content.decode()
    client.post(
        reverse("xestion:contido_editar", args=["testemunos", testemuno.pk]),
        {"nome_persoa": "Rosa", "nome_can": "Pupa", "texto": "Moi felices.", "orde": 1},
    )
    testemuno.refresh_from_db()
    assert not testemuno.publicado
    assert "Moi felices" not in client.get(reverse("contido:finais_felices")).content.decode()
    client.post(reverse("xestion:contido_borrar", args=["testemunos", testemuno.pk]))
    assert not Testemuno.objects.exists()


def test_testemuno_con_foto(client, superadmin):
    from animais.tests.test_cans_protectora import imaxe

    client.force_login(superadmin)
    client.post(
        reverse("xestion:contido_novo", args=["testemunos"]),
        {
            "nome_persoa": "Marta",
            "nome_can": "Russ",
            "texto": "Ola",
            "orde": 0,
            "publicado": "on",
            "foto": imaxe(2000, 1000),
        },
    )
    assert Testemuno.objects.get().foto.name.endswith(".jpg")


def test_enlaces_e_checklist(client, superadmin):
    client.force_login(superadmin)
    client.post(
        reverse("xestion:contido_novo", args=["enlaces"]),
        {"titulo": "Fundación Affinity", "url": "fundacion-affinity.org", "orde": 0},
    )
    assert Enlace.objects.get().url == "https://fundacion-affinity.org"
    assert "Fundación Affinity" in client.get(reverse("contido:enlaces")).content.decode()
    client.post(
        reverse("xestion:contido_novo", args=["checklist"]),
        {"texto": "Coidareino sempre.", "orde": 1, "activo": "on"},
    )
    assert ItemChecklist.objects.filter(texto="Coidareino sempre.").exists()
    assert (
        "Coidareino"
        in client.get(reverse("xestion:contido_lista", args=["checklist"])).content.decode()
    )


def test_tipo_de_contido_descoñecido_e_404(client, superadmin):
    client.force_login(superadmin)
    assert client.get(reverse("xestion:contido_lista", args=["usuarios"])).status_code == 404


def test_editar_o_contrato_crea_unha_version_nova_sen_tocar_as_aceptadas(
    client, superadmin, adoptante_con_perfil, crear_can, protectora
):
    from django.core.management import call_command

    from adopcions import contrato

    call_command("loaddata", "adopcion_inicial", verbosity=0)
    solicitude = estados.crear_solicitude(adoptante_con_perfil, crear_can())
    estados.aceptar(solicitude, protectora.usuario)
    estados.completar_checklist(solicitude, adoptante_con_perfil)
    datos = {
        "nome": "X",
        "nif": "12345678Z",
        "enderezo": "Y",
        "telefono": "600000000",
        "email": "x@x.gal",
    }
    aceptacion = contrato.aceptar(solicitude, adoptante_con_perfil, datos)
    hash_orixinal = aceptacion.hash_sha256

    client.force_login(superadmin)
    client.post(reverse("xestion:contrato"), {"texto": "Contrato novo para {can}."})
    assert ModeloContrato.actual().version == 2
    assert ModeloContrato.objects.filter(activo=True).count() == 1
    aceptacion = AceptacionContrato.objects.get()
    assert aceptacion.modelo.version == 1
    assert aceptacion.hash_sha256 == hash_orixinal
    assert "v2" in client.get(reverse("xestion:contrato")).content.decode()
