"""Lectura dos filtros do listado e do deck desde a URL (?tamano=...&idade=...)."""

from compatibilidade.calculo import Tamano, opcions

OPCIONS_TAMANO = [("", "Todos"), *opcions(Tamano)]
OPCIONS_IDADE = [("", "Todas"), ("cachorro", "Cachorro"), ("adulto", "Adulto"), ("maior", "Maior")]
OPCIONS_DISTANCIA = [
    ("", "Calquera"),
    ("25", "Ata 25 km"),
    ("50", "Ata 50 km"),
    ("100", "Ata 100 km"),
]


def ler_filtros(parametros):
    """Converte os parámetros da URL nun dicionario de filtros válidos (ignora o resto)."""
    filtros = {}
    if parametros.get("tamano") in {valor for valor, _ in OPCIONS_TAMANO if valor}:
        filtros["tamano"] = parametros["tamano"]
    if parametros.get("idade") in {"cachorro", "adulto", "maior"}:
        filtros["idade"] = parametros["idade"]
    if parametros.get("distancia") in {"25", "50", "100"}:
        filtros["distancia"] = int(parametros["distancia"])
    if parametros.get("urxentes") == "1":
        filtros["urxentes"] = True
    return filtros


def contexto_filtros(parametros):
    """Datos para pintar o formulario de filtros co estado actual."""
    return {
        "filtros": ler_filtros(parametros),
        "parametros": parametros,
        "opcions_tamano": OPCIONS_TAMANO,
        "opcions_idade": OPCIONS_IDADE,
        "opcions_distancia": OPCIONS_DISTANCIA,
    }
