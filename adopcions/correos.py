"""
Correos que envía o fluxo de adopción.

Chámanse desde adopcions/estados.py con transaction.on_commit, é dicir, só cando o
cambio de estado xa está gardado (se algo falla, non se envía nada).
En desenvolvemento os correos amósanse na consola do contedor web.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse


def _url(nome, *args):
    return settings.SITIO_URL.rstrip("/") + reverse(nome, args=args)


def _enviar(asunto, texto, destinatario):
    send_mail(f"QueroCan: {asunto}", texto + "\n\nQueroCan", None, [destinatario])


def solicitude_nova(solicitude):
    protectora = solicitude.can.protectora
    _enviar(
        f"nova solicitude para {solicitude.can.nome}",
        f"{solicitude.adoptante.nome} quere adoptar a {solicitude.can.nome} "
        f"({solicitude.porcentaxe} % de compatibilidade).\n"
        f"Revísaa no teu panel: {_url('adopcions:protectora_solicitudes')}",
        protectora.usuario.email,
    )


def solicitude_aceptada(solicitude):
    from .estados import PRAZO_DIAS

    _enviar(
        f"{solicitude.can.protectora.nome} aceptou a túa solicitude!",
        f"Boas noticias: a protectora aceptou a túa solicitude para adoptar a "
        f"{solicitude.can.nome}. Tes {PRAZO_DIAS} días para completar o compromiso de "
        f"responsabilidade e o contrato: {_url('adopcions:minas_solicitudes')}",
        solicitude.adoptante.email,
    )


def solicitude_rexeitada(solicitude):
    _enviar(
        f"solicitude para {solicitude.can.nome}",
        f"A protectora non pode seguir coa túa solicitude para {solicitude.can.nome}. "
        f"Hai moitos máis cans esperando: {_url('animais:deck')}",
        solicitude.adoptante.email,
    )


def solicitude_cancelada(solicitude, actor):
    if actor.pk == solicitude.adoptante_id:
        destinatario = solicitude.can.protectora.usuario.email
        texto = f"{solicitude.adoptante.nome} cancelou a adopción de {solicitude.can.nome}."
    else:
        destinatario = solicitude.adoptante.email
        texto = f"A protectora cancelou a adopción de {solicitude.can.nome}."
    _enviar(f"adopción de {solicitude.can.nome} cancelada", texto, destinatario)


def solicitude_caducada(solicitude):
    texto = (
        f"A adopción de {solicitude.can.nome} caducou porque non se completou o contrato "
        "no prazo. O can volve estar dispoñible."
    )
    _enviar(f"adopción de {solicitude.can.nome} caducada", texto, solicitude.adoptante.email)
    _enviar(
        f"adopción de {solicitude.can.nome} caducada",
        texto,
        solicitude.can.protectora.usuario.email,
    )


def can_adoptado(solicitude):
    _enviar(
        f"{solicitude.can.nome} xa atopou fogar",
        f"{solicitude.can.nome} foi adoptado por outra persoa. Grazas polo teu interese! "
        f"Seguro que hai outro can perfecto para ti: {_url('animais:deck')}",
        solicitude.adoptante.email,
    )


def adopcion_completada(solicitude):
    _enviar(
        f"adopción de {solicitude.can.nome} completada",
        f"{solicitude.adoptante.nome} aceptou o contrato de adopción de {solicitude.can.nome}. "
        f"Ponte en contacto para organizar a entrega: {solicitude.adoptante.email}",
        solicitude.can.protectora.usuario.email,
    )
