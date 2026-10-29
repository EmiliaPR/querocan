"""
Probas da máquina de estados das solicitudes (adopcions/estados.py).

Hai unha proba por cada fila da táboa de transicións de SPEC.md e outra por cada
transición que debe rexeitarse.
"""

import threading
from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.utils import timezone

from adopcions import estados
from adopcions.models import Descarte, HistorialSolicitude, Solicitude
from animais.models import Can

Estado = Solicitude.Estado
pytestmark = pytest.mark.django_db


@pytest.fixture
def can(crear_can):
    return crear_can()


@pytest.fixture
def outra_adoptante(crear_usuario, crear_perfil):
    persoa = crear_usuario()
    crear_perfil(persoa)
    return persoa


@pytest.fixture
def solicitude(adoptante_con_perfil, can):
    return estados.crear_solicitude(adoptante_con_perfil, can)


def recargar(*obxectos):
    for obxecto in obxectos:
        obxecto.refresh_from_db()


def aceptada(solicitude, protectora):
    return estados.aceptar(solicitude, protectora.usuario)


# --- Crear ----------------------------------------------------------------------------


def test_crear_solicitude_queda_pendente_con_porcentaxe_e_historial(
    adoptante_con_perfil, can, mailoutbox, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        solicitude = estados.crear_solicitude(adoptante_con_perfil, can)
    assert solicitude.estado == Estado.PENDENTE
    assert solicitude.porcentaxe == 100
    assert solicitude.historial.get().estado_novo == Estado.PENDENTE
    assert mailoutbox[0].to == [can.protectora.usuario.email]


def test_crear_sen_perfil_lanza_perfil_incompleto(adoptante, can):
    with pytest.raises(estados.PerfilIncompleto):
        estados.crear_solicitude(adoptante, can)


def test_so_as_adoptantes_poden_solicitar(usuario_protectora, can):
    with pytest.raises(PermissionDenied):
        estados.crear_solicitude(usuario_protectora, can)


def test_non_se_pode_solicitar_un_can_non_dispoñible(adoptante_con_perfil, crear_can):
    with pytest.raises(estados.TransicionInvalida):
        estados.crear_solicitude(adoptante_con_perfil, crear_can(estado=Can.Estado.RESERVADO))


def test_non_se_pode_solicitar_un_can_de_protectora_inactiva(
    adoptante_con_perfil, crear_can, crear_protectora
):
    inactiva = crear_protectora(estado="desactivada")
    with pytest.raises(estados.TransicionInvalida):
        estados.crear_solicitude(adoptante_con_perfil, crear_can(protectora=inactiva))


def test_so_unha_solicitude_activa_por_persoa_e_can(solicitude, adoptante_con_perfil, can):
    with pytest.raises(estados.TransicionInvalida, match="Xa tes"):
        estados.crear_solicitude(adoptante_con_perfil, can)


def test_solicitar_borra_un_descarte_anterior(adoptante_con_perfil, can):
    estados.descartar(adoptante_con_perfil, can)
    estados.crear_solicitude(adoptante_con_perfil, can)
    assert not Descarte.objects.exists()


# --- Aceptar (match) ------------------------------------------------------------------


def test_aceptar_reserva_o_can_e_pon_en_espera_as_demais(
    solicitude, outra_adoptante, can, protectora, mailoutbox, django_capture_on_commit_callbacks
):
    outra = estados.crear_solicitude(outra_adoptante, can)
    with django_capture_on_commit_callbacks(execute=True):
        aceptada(solicitude, protectora)
    recargar(solicitude, outra, can)
    assert solicitude.estado == Estado.ACEPTADA
    assert solicitude.data_aceptacion is not None
    assert outra.estado == Estado.EN_ESPERA
    assert can.estado == Can.Estado.RESERVADO
    assert mailoutbox[-1].to == [solicitude.adoptante.email]


def test_so_a_protectora_do_can_pode_aceptar(solicitude, crear_protectora, adoptante_con_perfil):
    with pytest.raises(PermissionDenied):
        estados.aceptar(solicitude, crear_protectora().usuario)
    with pytest.raises(PermissionDenied):
        estados.aceptar(solicitude, adoptante_con_perfil)


def test_non_se_pode_aceptar_unha_en_espera(solicitude, outra_adoptante, can, protectora):
    outra = estados.crear_solicitude(outra_adoptante, can)
    aceptada(solicitude, protectora)
    with pytest.raises(estados.TransicionInvalida):
        estados.aceptar(outra, protectora.usuario)


def test_non_se_pode_aceptar_se_o_can_xa_non_esta_dispoñible(solicitude, can, protectora):
    Can.objects.filter(pk=can.pk).update(estado=Can.Estado.ADOPTADO)
    with pytest.raises(estados.TransicionInvalida):
        aceptada(solicitude, protectora)


# --- Rexeitar e retirar ---------------------------------------------------------------


@pytest.mark.parametrize("en_espera", [False, True])
def test_rexeitar_pendente_ou_en_espera(solicitude, outra_adoptante, can, protectora, en_espera):
    obxectivo = solicitude
    if en_espera:
        obxectivo = estados.crear_solicitude(outra_adoptante, can)
        aceptada(solicitude, protectora)
    estados.rexeitar(obxectivo, protectora.usuario)
    recargar(obxectivo)
    assert obxectivo.estado == Estado.REXEITADA
    assert obxectivo.data_peche is not None


def test_non_se_pode_rexeitar_unha_aceptada(solicitude, protectora):
    aceptada(solicitude, protectora)
    with pytest.raises(estados.TransicionInvalida):
        estados.rexeitar(solicitude, protectora.usuario)


def test_a_adoptante_retira_unha_pendente(solicitude, adoptante_con_perfil):
    estados.retirar(solicitude, adoptante_con_perfil)
    recargar(solicitude)
    assert solicitude.estado == Estado.CANCELADA


def test_ninguen_mais_pode_retirar(solicitude, outra_adoptante):
    with pytest.raises(PermissionDenied):
        estados.retirar(solicitude, outra_adoptante)


def test_non_se_pode_retirar_unha_aceptada(solicitude, protectora, adoptante_con_perfil):
    aceptada(solicitude, protectora)
    with pytest.raises(estados.TransicionInvalida):
        estados.retirar(solicitude, adoptante_con_perfil)


# --- Checklist e contrato -------------------------------------------------------------


def test_checklist_so_nunha_aceptada(solicitude, protectora, adoptante_con_perfil):
    with pytest.raises(estados.TransicionInvalida):
        estados.completar_checklist(solicitude, adoptante_con_perfil)
    aceptada(solicitude, protectora)
    estados.completar_checklist(solicitude, adoptante_con_perfil)
    recargar(solicitude)
    assert solicitude.checklist_feito
    assert solicitude.historial.filter(evento="checklist").count() == 1
    # Repetilo non duplica o evento
    estados.completar_checklist(solicitude, adoptante_con_perfil)
    assert solicitude.historial.filter(evento="checklist").count() == 1


def test_completar_adopcion_require_checklist(solicitude, protectora, adoptante_con_perfil):
    aceptada(solicitude, protectora)
    with pytest.raises(estados.TransicionInvalida, match="compromiso"):
        estados.completar_adopcion(solicitude, adoptante_con_perfil)


def test_completar_adopcion(
    solicitude,
    outra_adoptante,
    can,
    protectora,
    adoptante_con_perfil,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    outra = estados.crear_solicitude(outra_adoptante, can)
    aceptada(solicitude, protectora)
    estados.completar_checklist(solicitude, adoptante_con_perfil)
    with django_capture_on_commit_callbacks(execute=True):
        estados.completar_adopcion(solicitude, adoptante_con_perfil)
    recargar(solicitude, outra, can)
    assert solicitude.estado == Estado.COMPLETADA
    assert can.estado == Can.Estado.ADOPTADO
    assert outra.estado == Estado.REXEITADA
    destinatarios = {tuple(m.to) for m in mailoutbox}
    assert (outra_adoptante.email,) in destinatarios
    assert (protectora.usuario.email,) in destinatarios


def test_so_a_propia_adoptante_completa(solicitude, protectora, outra_adoptante):
    aceptada(solicitude, protectora)
    with pytest.raises(PermissionDenied):
        estados.completar_checklist(solicitude, outra_adoptante)


# --- Cancelar unha aceptada -----------------------------------------------------------


@pytest.mark.parametrize("quen", ["protectora", "adoptante"])
def test_cancelar_aceptada_libera_o_can_e_reactiva_as_en_espera(
    solicitude,
    outra_adoptante,
    can,
    protectora,
    adoptante_con_perfil,
    quen,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    outra = estados.crear_solicitude(outra_adoptante, can)
    aceptada(solicitude, protectora)
    actor = protectora.usuario if quen == "protectora" else adoptante_con_perfil
    with django_capture_on_commit_callbacks(execute=True):
        estados.cancelar_aceptada(solicitude, actor)
    recargar(solicitude, outra, can)
    assert solicitude.estado == Estado.CANCELADA
    assert can.estado == Can.Estado.DISPONIBLE
    assert outra.estado == Estado.PENDENTE
    esperado = adoptante_con_perfil.email if quen == "protectora" else protectora.usuario.email
    assert mailoutbox[-1].to == [esperado]


def test_terceiros_non_poden_cancelar(solicitude, protectora, outra_adoptante):
    aceptada(solicitude, protectora)
    with pytest.raises(PermissionDenied):
        estados.cancelar_aceptada(solicitude, outra_adoptante)


def test_non_se_cancela_unha_pendente_como_aceptada(solicitude, protectora):
    with pytest.raises(estados.TransicionInvalida):
        estados.cancelar_aceptada(solicitude, protectora.usuario)


# --- Caducidade -----------------------------------------------------------------------


def test_caduca_aos_7_dias(solicitude, outra_adoptante, can, protectora):
    outra = estados.crear_solicitude(outra_adoptante, can)
    aceptada(solicitude, protectora)
    agora = timezone.now() + timedelta(days=8)
    assert estados.caducar_vencidas(agora) == 1
    recargar(solicitude, outra, can)
    assert solicitude.estado == Estado.CADUCADA
    assert can.estado == Can.Estado.DISPONIBLE
    assert outra.estado == Estado.PENDENTE


def test_non_caduca_antes_de_7_dias(solicitude, protectora):
    aceptada(solicitude, protectora)
    assert estados.caducar_vencidas(timezone.now() + timedelta(days=6)) == 0
    with pytest.raises(estados.TransicionInvalida, match="prazo"):
        estados.caducar(solicitude, timezone.now() + timedelta(days=6))
    recargar(solicitude)
    assert solicitude.estado == Estado.ACEPTADA


def test_caducar_e_idempotente(solicitude, protectora):
    aceptada(solicitude, protectora)
    agora = timezone.now() + timedelta(days=8)
    assert estados.caducar_vencidas(agora) == 1
    assert estados.caducar_vencidas(agora) == 0


def test_caducar_ignora_as_que_cambiaron_mentres_tanto(solicitude, protectora, monkeypatch):
    aceptada(solicitude, protectora)

    def falla(*args, **kwargs):
        raise estados.TransicionInvalida("xa cambiou")

    monkeypatch.setattr(estados, "caducar", falla)
    assert estados.caducar_vencidas(timezone.now() + timedelta(days=8)) == 0


def test_data_limite(solicitude, protectora):
    assert estados.data_limite(solicitude) is None
    aceptada(solicitude, protectora)
    recargar(solicitude)
    assert estados.data_limite(solicitude) == solicitude.data_aceptacion + timedelta(days=7)


# --- Desfacer e descartes -------------------------------------------------------------


def test_desfacer_borra_a_solicitude_pendente(solicitude, adoptante_con_perfil):
    estados.desfacer_solicitude(solicitude, adoptante_con_perfil)
    assert not Solicitude.objects.exists()


def test_non_se_desfai_unha_que_xa_cambiou(
    solicitude, outra_adoptante, can, protectora, adoptante_con_perfil
):
    # A solicitude pasa a «en espera» e volve a «pendente»: xa ten historial
    outra = estados.crear_solicitude(outra_adoptante, can)
    aceptada(outra, protectora)
    estados.cancelar_aceptada(outra, protectora.usuario)
    with pytest.raises(estados.TransicionInvalida):
        estados.desfacer_solicitude(solicitude, adoptante_con_perfil)


def test_descartar_e_desfacer_descarte(adoptante, can):
    estados.descartar(adoptante, can)
    estados.descartar(adoptante, can)  # non duplica
    assert Descarte.objects.count() == 1
    estados.desfacer_descarte(adoptante, can)
    assert not Descarte.objects.exists()


def test_cada_transicion_queda_no_historial(solicitude, protectora, adoptante_con_perfil):
    aceptada(solicitude, protectora)
    estados.completar_checklist(solicitude, adoptante_con_perfil)
    estados.completar_adopcion(solicitude, adoptante_con_perfil)
    historial = list(
        HistorialSolicitude.objects.filter(solicitude=solicitude).values_list(
            "estado_anterior", "estado_novo", "evento"
        )
    )
    assert historial == [
        ("", "pendente", ""),
        ("pendente", "aceptada", ""),
        ("aceptada", "aceptada", "checklist"),
        ("aceptada", "completada", ""),
    ]


# --- Concorrencia ---------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_duas_aceptacions_simultaneas_so_unha_ten_exito(
    crear_can, crear_usuario, crear_perfil, protectora
):
    """Dúas persoas da protectora aceptan á vez dúas solicitudes do mesmo can.

    Cada fío usa a súa propia conexión a MySQL. Grazas a select_for_update, a segunda
    agarda á primeira e despois ve o can xa reservado.
    """
    can = crear_can()
    solicitudes = []
    for _ in range(2):
        persoa = crear_usuario()
        crear_perfil(persoa)
        solicitudes.append(estados.crear_solicitude(persoa, can))

    barreira = threading.Barrier(2)
    resultados = []

    def aceptar_en_paralelo(solicitude):
        try:
            barreira.wait()
            estados.aceptar(solicitude, protectora.usuario)
            resultados.append("ok")
        except estados.TransicionInvalida:
            resultados.append("rexeitada")
        finally:
            connection.close()

    fios = [threading.Thread(target=aceptar_en_paralelo, args=(s,)) for s in solicitudes]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join()

    assert sorted(resultados) == ["ok", "rexeitada"]
    can.refresh_from_db()
    assert can.estado == Can.Estado.RESERVADO
    assert Solicitude.objects.filter(estado=Estado.ACEPTADA).count() == 1
