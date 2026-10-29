"""
Máquina de estados das solicitudes de adopción.

Toda mudanza de estado dunha solicitude (e do can asociado) pasa por este módulo.
Así as regras do fluxo están nun único sitio e as vistas limítanse a chamar a estas
funcións. Cada función:
  1. Comproba quen fai a acción (actor) e se o estado actual a permite.
  2. Bloquea o can na base de datos (select_for_update) para que dúas accións
     simultáneas non o deixen nun estado incoherente.
  3. Cambia os estados, rexistra o cambio no historial e programa os correos.

Resumo do fluxo (táboa completa en SPEC.md):

    PENDENTE ──aceptar──▶ ACEPTADA ──checklist + contrato──▶ COMPLETADA
       │  ▲                  │
       │  └── EN_ESPERA ◀────┤ (as outras solicitudes do can esperan)
       ▼                     ▼
    REXEITADA / CANCELADA    CADUCADA (7 días) / CANCELADA → o can volve estar dispoñible
"""

from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from animais.models import Can
from compatibilidade.calculo import calcular

from . import correos
from .models import Descarte, HistorialSolicitude, Solicitude

Estado = Solicitude.Estado

# Días que ten a persoa para completar o checklist e o contrato tras o match
PRAZO_DIAS = 7


class TransicionInvalida(Exception):
    """A acción non se pode facer no estado actual (p. ex. aceptar unha xa rexeitada)."""


class PerfilIncompleto(Exception):
    """A persoa aínda non fixo o test de compatibilidade."""


# ---------------------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------------------


def _bloquear(solicitude):
    """Volve ler a solicitude e o seu can bloqueándoos ata o final da transacción."""
    can = Can.objects.select_for_update().get(pk=solicitude.can_id)
    solicitude = (
        Solicitude.objects.select_for_update().select_related("adoptante").get(pk=solicitude.pk)
    )
    solicitude.can = can
    return solicitude, can


def _cambiar(solicitude, novo, actor, campos_extra=()):
    """Cambia o estado dunha solicitude e déixao anotado no historial."""
    anterior = solicitude.estado
    solicitude.estado = novo
    solicitude.save(update_fields=["estado", *campos_extra])
    HistorialSolicitude.objects.create(
        solicitude=solicitude, estado_anterior=anterior, estado_novo=novo, actor=actor
    )


def _esixir_estado(solicitude, *permitidos):
    if solicitude.estado not in permitidos:
        estado = solicitude.get_estado_display()
        raise TransicionInvalida(f"Non se pode facer isto cunha solicitude en estado «{estado}».")


def _esixir_protectora(solicitude, actor):
    if not (actor.es_protectora and solicitude.can.protectora.usuario_id == actor.pk):
        raise PermissionDenied("Só a protectora do can pode facer isto.")


def _esixir_adoptante(solicitude, actor):
    if solicitude.adoptante_id != actor.pk:
        raise PermissionDenied("Só a persoa que fixo a solicitude pode facer isto.")


def _outras_do_can(solicitude, estado):
    return (
        Solicitude.objects.select_for_update()
        .filter(can=solicitude.can, estado=estado)
        .exclude(pk=solicitude.pk)
    )


def _liberar_can(solicitude, can, actor):
    """A adopción en curso non saíu: o can volve estar dispoñible e as que agardaban, tamén."""
    can.estado = Can.Estado.DISPONIBLE
    can.save(update_fields=["estado"])
    for agardando in _outras_do_can(solicitude, Estado.EN_ESPERA):
        _cambiar(agardando, Estado.PENDENTE, actor)


# ---------------------------------------------------------------------------------------
# Accións da persoa adoptante
# ---------------------------------------------------------------------------------------


@transaction.atomic
def crear_solicitude(adoptante, can) -> Solicitude:
    """Swipe á dereita ou botón «Adoptar»: crea unha solicitude PENDENTE."""
    if not adoptante.es_adoptante:
        raise PermissionDenied("Só as persoas adoptantes poden solicitar unha adopción.")
    perfil = getattr(adoptante, "perfil", None)
    if perfil is None:
        raise PerfilIncompleto("Fai o test de compatibilidade antes de solicitar.")

    can = Can.objects.select_for_update().select_related("protectora").get(pk=can.pk)
    if can.estado != Can.Estado.DISPONIBLE or not can.protectora.activa:
        raise TransicionInvalida(f"{can.nome} xa non está dispoñible.")
    if Solicitude.objects.filter(
        adoptante=adoptante, can=can, estado__in=Solicitude.ACTIVAS
    ).exists():
        raise TransicionInvalida(f"Xa tes unha solicitude en curso para {can.nome}.")

    porcentaxe = calcular(perfil.como_perfil(), can.necesidades()).porcentaxe
    solicitude = Solicitude.objects.create(adoptante=adoptante, can=can, porcentaxe=porcentaxe)
    HistorialSolicitude.objects.create(
        solicitude=solicitude, estado_novo=Estado.PENDENTE, actor=adoptante
    )
    # Se antes o descartara, xa non ten sentido gardar ese descarte
    Descarte.objects.filter(adoptante=adoptante, can=can).delete()
    transaction.on_commit(lambda: correos.solicitude_nova(solicitude))
    return solicitude


@transaction.atomic
def desfacer_solicitude(solicitude, actor):
    """«Desfacer» no deck: borra unha solicitude que a protectora aínda non tocou."""
    solicitude, _ = _bloquear(solicitude)
    _esixir_adoptante(solicitude, actor)
    _esixir_estado(solicitude, Estado.PENDENTE)
    if solicitude.historial.count() > 1:
        raise TransicionInvalida("Esta solicitude xa cambiou de estado e non se pode desfacer.")
    solicitude.delete()


@transaction.atomic
def retirar(solicitude, actor):
    """A persoa retira unha solicitude que aínda non foi aceptada."""
    solicitude, _ = _bloquear(solicitude)
    _esixir_adoptante(solicitude, actor)
    _esixir_estado(solicitude, Estado.PENDENTE, Estado.EN_ESPERA)
    solicitude.data_peche = timezone.now()
    _cambiar(solicitude, Estado.CANCELADA, actor, ["data_peche"])
    return solicitude


@transaction.atomic
def completar_checklist(solicitude, actor):
    """A persoa marcou todos os compromisos de responsabilidade."""
    solicitude, _ = _bloquear(solicitude)
    _esixir_adoptante(solicitude, actor)
    _esixir_estado(solicitude, Estado.ACEPTADA)
    if solicitude.checklist_feito:
        return solicitude
    solicitude.data_checklist = timezone.now()
    solicitude.save(update_fields=["data_checklist"])
    HistorialSolicitude.objects.create(
        solicitude=solicitude,
        estado_anterior=Estado.ACEPTADA,
        estado_novo=Estado.ACEPTADA,
        evento="checklist",
        actor=actor,
    )
    return solicitude


@transaction.atomic
def completar_adopcion(solicitude, actor):
    """Contrato aceptado: a adopción complétase e o can queda adoptado.

    Chámase desde adopcions/contrato.py dentro da mesma transacción que garda o contrato.
    """
    solicitude, can = _bloquear(solicitude)
    _esixir_adoptante(solicitude, actor)
    _esixir_estado(solicitude, Estado.ACEPTADA)
    if not solicitude.checklist_feito:
        raise TransicionInvalida("Primeiro hai que completar o compromiso de responsabilidade.")

    solicitude.data_peche = timezone.now()
    _cambiar(solicitude, Estado.COMPLETADA, actor, ["data_peche"])
    can.estado = Can.Estado.ADOPTADO
    can.save(update_fields=["estado"])
    for agardando in _outras_do_can(solicitude, Estado.EN_ESPERA):
        agardando.data_peche = solicitude.data_peche
        _cambiar(agardando, Estado.REXEITADA, None, ["data_peche"])
        transaction.on_commit(lambda s=agardando: correos.can_adoptado(s))
    transaction.on_commit(lambda: correos.adopcion_completada(solicitude))
    return solicitude


# ---------------------------------------------------------------------------------------
# Accións da protectora
# ---------------------------------------------------------------------------------------


@transaction.atomic
def aceptar(solicitude, actor):
    """Match: a protectora acepta. O can queda reservado para esta persoa."""
    solicitude, can = _bloquear(solicitude)
    _esixir_protectora(solicitude, actor)
    _esixir_estado(solicitude, Estado.PENDENTE)
    if can.estado != Can.Estado.DISPONIBLE:
        raise TransicionInvalida(f"{can.nome} xa ten outra adopción en curso.")

    solicitude.data_aceptacion = timezone.now()
    _cambiar(solicitude, Estado.ACEPTADA, actor, ["data_aceptacion"])
    can.estado = Can.Estado.RESERVADO
    can.save(update_fields=["estado"])
    for outra in _outras_do_can(solicitude, Estado.PENDENTE):
        _cambiar(outra, Estado.EN_ESPERA, actor)
    transaction.on_commit(lambda: correos.solicitude_aceptada(solicitude))
    return solicitude


@transaction.atomic
def rexeitar(solicitude, actor):
    """A protectora rexeita unha solicitude que aínda non aceptou."""
    solicitude, _ = _bloquear(solicitude)
    _esixir_protectora(solicitude, actor)
    _esixir_estado(solicitude, Estado.PENDENTE, Estado.EN_ESPERA)
    solicitude.data_peche = timezone.now()
    _cambiar(solicitude, Estado.REXEITADA, actor, ["data_peche"])
    transaction.on_commit(lambda: correos.solicitude_rexeitada(solicitude))
    return solicitude


@transaction.atomic
def cancelar_aceptada(solicitude, actor):
    """A protectora ou a persoa cancelan unha adopción aceptada antes de completala."""
    solicitude, can = _bloquear(solicitude)
    if actor.pk != solicitude.adoptante_id:
        _esixir_protectora(solicitude, actor)
    _esixir_estado(solicitude, Estado.ACEPTADA)
    solicitude.data_peche = timezone.now()
    _cambiar(solicitude, Estado.CANCELADA, actor, ["data_peche"])
    _liberar_can(solicitude, can, actor)
    transaction.on_commit(lambda: correos.solicitude_cancelada(solicitude, actor))
    return solicitude


# ---------------------------------------------------------------------------------------
# Caducidade (executada polo comando expirar_solicitudes)
# ---------------------------------------------------------------------------------------


def data_limite(solicitude):
    """Data na que caduca unha solicitude aceptada."""
    if solicitude.data_aceptacion is None:
        return None
    return solicitude.data_aceptacion + timedelta(days=PRAZO_DIAS)


@transaction.atomic
def caducar(solicitude, agora=None):
    """Pecha unha solicitude aceptada se pasou o prazo sen completar a adopción."""
    agora = agora or timezone.now()
    solicitude, can = _bloquear(solicitude)
    _esixir_estado(solicitude, Estado.ACEPTADA)
    if data_limite(solicitude) > agora:
        raise TransicionInvalida("O prazo aínda non rematou.")
    solicitude.data_peche = agora
    _cambiar(solicitude, Estado.CADUCADA, None, ["data_peche"])
    _liberar_can(solicitude, can, None)
    transaction.on_commit(lambda: correos.solicitude_caducada(solicitude))
    return solicitude


def caducar_vencidas(agora=None):
    """Caduca todas as solicitudes aceptadas cuxo prazo xa pasou. Devolve cantas."""
    agora = agora or timezone.now()
    limite = agora - timedelta(days=PRAZO_DIAS)
    vencidas = Solicitude.objects.filter(estado=Estado.ACEPTADA, data_aceptacion__lte=limite)
    total = 0
    for solicitude in vencidas:
        try:
            caducar(solicitude, agora)
            total += 1
        except TransicionInvalida:
            continue  # outra persoa xa a cambiou mentres tanto
    return total


# ---------------------------------------------------------------------------------------
# Descartes do deck (non son solicitudes, pero tamén os xestiona o deck)
# ---------------------------------------------------------------------------------------


def descartar(adoptante, can):
    """Swipe á esquerda: non volver amosar este can a esta persoa."""
    Descarte.objects.get_or_create(adoptante=adoptante, can=can)


def desfacer_descarte(adoptante, can):
    Descarte.objects.filter(adoptante=adoptante, can=can).delete()
