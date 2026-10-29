"""
Funil de adopción para o panel do superadmin.

Conta cantas solicitudes pasaron por cada etapa nun período, a partir do historial
de cambios de estado (HistorialSolicitude). Así unha solicitude creada en xaneiro e
aceptada en febreiro conta como «solicitude» en xaneiro e «aceptada» en febreiro.
"""

from django.db.models import Count, Q

from adopcions.models import HistorialSolicitude, Solicitude

Estado = Solicitude.Estado

# Etapas do funil, na orde na que se pasa por elas, e o filtro que as identifica
ETAPAS = [
    ("solicitudes", "Solicitudes", Q(estado_anterior="", estado_novo=Estado.PENDENTE)),
    (
        "aceptadas",
        "Aceptadas (match)",
        Q(estado_anterior=Estado.PENDENTE, estado_novo=Estado.ACEPTADA),
    ),
    ("checklist", "Compromiso feito", Q(evento="checklist")),
    ("completadas", "Adopcións completadas", Q(estado_novo=Estado.COMPLETADA)),
]
# Peches que non son adopción (amósanse á parte, non son etapas do funil)
PECHES = [
    ("rexeitadas", "Rexeitadas", Q(estado_novo=Estado.REXEITADA)),
    ("canceladas", "Canceladas", Q(estado_novo=Estado.CANCELADA)),
    ("caducadas", "Caducadas", Q(estado_novo=Estado.CADUCADA)),
]


def _historial(protectora=None, desde=None, ata=None):
    consulta = HistorialSolicitude.objects.all()
    if protectora is not None:
        consulta = consulta.filter(solicitude__can__protectora=protectora)
    if desde:
        consulta = consulta.filter(data__date__gte=desde)
    if ata:
        consulta = consulta.filter(data__date__lte=ata)
    return consulta


def _contar(consulta, definicions):
    agregados = consulta.aggregate(
        **{clave: Count("pk", filter=filtro) for clave, _, filtro in definicions}
    )
    return [
        {"clave": clave, "nome": nome, "total": agregados[clave]} for clave, nome, _ in definicions
    ]


def funil(protectora=None, desde=None, ata=None):
    """Etapas do funil con totais e porcentaxe respecto ás solicitudes."""
    consulta = _historial(protectora, desde, ata)
    etapas = _contar(consulta, ETAPAS)
    base = etapas[0]["total"] or 0
    for etapa in etapas:
        etapa["porcentaxe"] = round(100 * etapa["total"] / base) if base else 0
    return {"etapas": etapas, "peches": _contar(consulta, PECHES)}


def funil_por_protectora(protectoras, desde=None, ata=None):
    """Unha fila por protectora co total de cada etapa (para a táboa comparativa)."""
    filas = []
    for protectora in protectoras:
        datos = funil(protectora, desde, ata)
        filas.append({"protectora": protectora, "etapas": datos["etapas"]})
    return filas
