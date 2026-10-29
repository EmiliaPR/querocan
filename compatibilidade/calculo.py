"""
Cálculo da compatibilidade entre unha persoa adoptante e un can.

Este módulo é Python puro: non usa Django nin a base de datos. Recibe dous obxectos
simples (o perfil da persoa e as necesidades do can) e devolve unha porcentaxe e a
lista de motivos que a explican. Así pódese ler, probar e cambiar sen coñecer Django.

Como funciona
-------------
1. Hai seis dimensións. En cada unha, a persoa di como é a súa vida (no test) e a
   protectora di o que necesita o can (na ficha). Ambas usan os mesmos valores.
2. Cada dimensión puntúa 1 (encaixa), 0,5 (encaixa con reservas) ou 0 (non encaixa).
3. A porcentaxe é a media ponderada polos PESOS: as dimensións que máis afectan ao
   benestar do can (vivenda, horas só, nenos) pesan máis.
4. Se hai unha incompatibilidade forte (p. ex. o can non convive con nenos e na casa
   hai nenos), a porcentaxe nunca supera o TOPE_INCOMPATIBILIDADE (40 %), aínda que o
   resto encaixe moi ben.
5. Cada dimensión xera un motivo («✓ Tes patio» ou «⚠ Non convive con gatos») para que
   a persoa entenda por que un can aparece antes ca outro.
"""

from dataclasses import dataclass, field
from enum import StrEnum

# ---------------------------------------------------------------------------------------
# Valores posibles de cada dimensión (compartidos polo test, a ficha e a base de datos)
# ---------------------------------------------------------------------------------------


class Vivenda(StrEnum):
    PISO = "piso"
    CASA_SEN_PATIO = "casa_sen_patio"
    CASA_CON_PATIO = "casa_con_patio"


class Espazo(StrEnum):
    """O que necesita o can en canto a espazo."""

    INDIFERENTE = "indiferente"
    PATIO_RECOMENDADO = "patio_recomendado"
    PATIO_NECESARIO = "patio_necesario"


class Tamano(StrEnum):
    PEQUENO = "pequeno"
    MEDIANO = "mediano"
    GRANDE = "grande"


class PreferenciaTamano(StrEnum):
    """Tamaño que busca a persoa (pode non importarlle)."""

    PEQUENO = "pequeno"
    MEDIANO = "mediano"
    GRANDE = "grande"
    INDIFERENTE = "indiferente"


class HorasSo(StrEnum):
    """Horas que o can pasaría só na casa nun día normal."""

    MENOS_DE_2 = "menos_de_2"
    DE_2_A_4 = "de_2_a_4"
    DE_4_A_6 = "de_4_a_6"
    MAIS_DE_6 = "mais_de_6"


class Tolerancia(StrEnum):
    """Canto tempo soporta o can estar só sen pasalo mal."""

    BAIXA = "baixa"  # menos de 2 horas
    MEDIA = "media"  # ata 4 horas
    ALTA = "alta"  # ata 6 horas


class Convivencia(StrEnum):
    """Se o can convive ben con nenos, cans ou gatos."""

    SI = "si"
    NON = "non"
    DESCONECIDO = "desconecido"


class OutrosAnimais(StrEnum):
    """Animais que xa hai na casa da persoa adoptante."""

    NINGUN = "ningun"
    CANS = "cans"
    GATOS = "gatos"
    CANS_E_GATOS = "cans_e_gatos"


class Nivel(StrEnum):
    """Nivel de actividade da persoa ou de enerxía do can."""

    BAIXO = "baixo"
    MEDIO = "medio"
    ALTO = "alto"


# Textos para amosar cada valor na interface (formularios, fichas e test).
# Van agrupados por enum porque varios enums comparten valores («indiferente», «pequeno»...)
# e, ao ser StrEnum, nun dicionario plano pisaríanse uns a outros.
ETIQUETAS = {
    Vivenda: {
        Vivenda.PISO: "Piso",
        Vivenda.CASA_SEN_PATIO: "Casa sen patio",
        Vivenda.CASA_CON_PATIO: "Casa con patio ou xardín",
    },
    Espazo: {
        Espazo.INDIFERENTE: "Adáptase a calquera vivenda",
        Espazo.PATIO_RECOMENDADO: "Recoméndase patio",
        Espazo.PATIO_NECESARIO: "Necesita patio",
    },
    Tamano: {
        Tamano.PEQUENO: "Pequeno",
        Tamano.MEDIANO: "Mediano",
        Tamano.GRANDE: "Grande",
    },
    PreferenciaTamano: {
        PreferenciaTamano.PEQUENO: "Pequeno",
        PreferenciaTamano.MEDIANO: "Mediano",
        PreferenciaTamano.GRANDE: "Grande",
        PreferenciaTamano.INDIFERENTE: "Non teño preferencia",
    },
    HorasSo: {
        HorasSo.MENOS_DE_2: "Menos de 2 horas",
        HorasSo.DE_2_A_4: "Entre 2 e 4 horas",
        HorasSo.DE_4_A_6: "Entre 4 e 6 horas",
        HorasSo.MAIS_DE_6: "Máis de 6 horas",
    },
    Tolerancia: {
        Tolerancia.BAIXA: "Baixa (menos de 2 horas)",
        Tolerancia.MEDIA: "Media (ata 4 horas)",
        Tolerancia.ALTA: "Alta (ata 6 horas)",
    },
    Convivencia: {
        Convivencia.SI: "Si",
        Convivencia.NON: "Non",
        Convivencia.DESCONECIDO: "Non se sabe",
    },
    OutrosAnimais: {
        OutrosAnimais.NINGUN: "Ningún",
        OutrosAnimais.CANS: "Cans",
        OutrosAnimais.GATOS: "Gatos",
        OutrosAnimais.CANS_E_GATOS: "Cans e gatos",
    },
    Nivel: {
        Nivel.BAIXO: "Baixo",
        Nivel.MEDIO: "Medio",
        Nivel.ALTO: "Alto",
    },
}


def opcions(enum):
    """Lista de pares (valor, texto) dun enum, lista para usar como `choices` en Django."""
    return [(membro.value, texto) for membro, texto in ETIQUETAS[enum].items()]


def etiqueta(enum, valor):
    """Texto en galego dun valor: etiqueta(Espazo, "indiferente") → «Adáptase…»."""
    return ETIQUETAS[enum][enum(valor)]


# ---------------------------------------------------------------------------------------
# Pesos e regras
# ---------------------------------------------------------------------------------------

# Canto conta cada dimensión na porcentaxe final. Súmanse 14 puntos en total.
PESOS = {
    "vivenda": 3,  # o espazo afecta todos os días ao benestar do can
    "tamano": 1,  # é unha preferencia da persoa, non unha necesidade do can
    "horas_so": 3,  # a soidade prolongada é unha causa habitual de devolución
    "nenos": 3,  # unha mala convivencia con nenos é un risco serio
    "outros_animais": 2,
    "actividade": 2,  # enerxía do can fronte ao ritmo de vida e a experiencia
}

# Porcentaxe máxima cando hai polo menos unha incompatibilidade forte
TOPE_INCOMPATIBILIDADE = 40

# Puntuacións posibles de cada dimensión
ENCAIXA = 1.0
CON_RESERVAS = 0.5
NON_ENCAIXA = 0.0

# Orde dos valores ordenables (para comparar «máis» ou «menos»)
_ORDE_HORAS = [HorasSo.MENOS_DE_2, HorasSo.DE_2_A_4, HorasSo.DE_4_A_6, HorasSo.MAIS_DE_6]
# Último tramo de horas que tolera cada nivel (índice en _ORDE_HORAS)
_LIMITE_TOLERANCIA = {Tolerancia.BAIXA: 0, Tolerancia.MEDIA: 1, Tolerancia.ALTA: 2}
_ORDE_TAMANO = [Tamano.PEQUENO, Tamano.MEDIANO, Tamano.GRANDE]
_ORDE_NIVEL = [Nivel.BAIXO, Nivel.MEDIO, Nivel.ALTO]


# ---------------------------------------------------------------------------------------
# Datos de entrada e saída
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PerfilAdoptante:
    """Como é a vida da persoa adoptante (respostas do test)."""

    vivenda: Vivenda
    tamano: PreferenciaTamano
    horas_so: HorasSo
    ten_nenos: bool
    outros_animais: OutrosAnimais
    actividade: Nivel
    experiencia: bool


@dataclass(frozen=True)
class NecesidadesCan:
    """O que necesita o can (indicado pola protectora na súa ficha)."""

    espazo: Espazo
    tamano: Tamano
    tolerancia_soidade: Tolerancia
    convive_nenos: Convivencia
    convive_cans: Convivencia
    convive_gatos: Convivencia
    enerxia: Nivel
    require_experiencia: bool


@dataclass(frozen=True)
class Motivo:
    """Unha razón pola que o can encaixa (✓) ou non (⚠) coa persoa."""

    texto: str
    encaixa: bool
    dimension: str
    forte: bool = False  # incompatibilidade forte: activa o tope de porcentaxe

    @property
    def icona(self):
        return "✓" if self.encaixa else "⚠"


@dataclass
class Resultado:
    """Porcentaxe de compatibilidade (0–100) e os motivos que a explican."""

    porcentaxe: int
    motivos: list[Motivo] = field(default_factory=list)

    @property
    def ten_incompatibilidade_forte(self):
        return any(m.forte for m in self.motivos)

    def motivos_destacados(self, cantidade=3):
        """Os motivos máis importantes para amosar nunha tarxeta.

        Primeiro as incompatibilidades fortes, despois os avisos e por último os
        encaixes; dentro de cada grupo, os das dimensións con máis peso.
        """

        def prioridade(motivo):
            grupo = 0 if motivo.forte else (1 if not motivo.encaixa else 2)
            return (grupo, -PESOS[motivo.dimension])

        return sorted(self.motivos, key=prioridade)[:cantidade]


# ---------------------------------------------------------------------------------------
# Unha función por dimensión: cada unha devolve (puntuación, motivo ou None)
# ---------------------------------------------------------------------------------------


def _avaliar_vivenda(perfil, can):
    if can.espazo == Espazo.INDIFERENTE:
        return ENCAIXA, Motivo("Adáptase á túa vivenda", True, "vivenda")
    ten_patio = perfil.vivenda == Vivenda.CASA_CON_PATIO
    if ten_patio:
        return ENCAIXA, Motivo("Tes o patio que lle convén", True, "vivenda")
    if can.espazo == Espazo.PATIO_RECOMENDADO:
        return CON_RESERVAS, Motivo("Agradecería ter patio", False, "vivenda")
    # O can necesita patio e a persoa non o ten
    return NON_ENCAIXA, Motivo("Necesita unha casa con patio", False, "vivenda", forte=True)


def _avaliar_tamano(perfil, can):
    if perfil.tamano == PreferenciaTamano.INDIFERENTE:
        return ENCAIXA, None  # non lle importa: non achega motivo
    buscado = _ORDE_TAMANO.index(Tamano(perfil.tamano.value))
    real = _ORDE_TAMANO.index(can.tamano)
    if buscado == real:
        return ENCAIXA, Motivo("É do tamaño que buscas", True, "tamano")
    texto = "É máis grande do que buscas" if real > buscado else "É máis pequeno do que buscas"
    puntos = CON_RESERVAS if abs(real - buscado) == 1 else NON_ENCAIXA
    return puntos, Motivo(texto, False, "tamano")


def _avaliar_horas_so(perfil, can):
    horas = _ORDE_HORAS.index(perfil.horas_so)
    limite = _LIMITE_TOLERANCIA[can.tolerancia_soidade]
    if horas <= limite:
        return ENCAIXA, Motivo("Non pasará demasiado tempo só", True, "horas_so")
    puntos = CON_RESERVAS if horas == limite + 1 else NON_ENCAIXA
    return puntos, Motivo("Pasaría máis tempo só do que lle convén", False, "horas_so")


def _avaliar_nenos(perfil, can):
    if not perfil.ten_nenos:
        return ENCAIXA, None  # sen nenos na casa a dimensión non lle afecta
    if can.convive_nenos == Convivencia.SI:
        return ENCAIXA, Motivo("É bo con nenos", True, "nenos")
    if can.convive_nenos == Convivencia.DESCONECIDO:
        return CON_RESERVAS, Motivo("Non sabemos como se leva con nenos", False, "nenos")
    return NON_ENCAIXA, Motivo("Non convive con nenos", False, "nenos", forte=True)


def _avaliar_un_animal(convivencia, nome):
    """Puntúa a convivencia cun tipo de animal (cans ou gatos) que hai na casa."""
    if convivencia == Convivencia.SI:
        return ENCAIXA, Motivo(f"Convive con {nome}", True, "outros_animais")
    if convivencia == Convivencia.DESCONECIDO:
        texto = f"Non sabemos como se leva con {nome}"
        return CON_RESERVAS, Motivo(texto, False, "outros_animais")
    return NON_ENCAIXA, Motivo(f"Non convive con {nome}", False, "outros_animais", forte=True)


def _avaliar_outros_animais(perfil, can):
    if perfil.outros_animais == OutrosAnimais.NINGUN:
        return ENCAIXA, None
    avaliacions = []
    if perfil.outros_animais in (OutrosAnimais.CANS, OutrosAnimais.CANS_E_GATOS):
        avaliacions.append(_avaliar_un_animal(can.convive_cans, "cans"))
    if perfil.outros_animais in (OutrosAnimais.GATOS, OutrosAnimais.CANS_E_GATOS):
        avaliacions.append(_avaliar_un_animal(can.convive_gatos, "gatos"))
    # Manda o peor caso: se non convive cun dos animais da casa, non encaixa
    return min(avaliacions, key=lambda avaliacion: avaliacion[0])


def _avaliar_actividade(perfil, can):
    diferenza = _ORDE_NIVEL.index(can.enerxia) - _ORDE_NIVEL.index(perfil.actividade)
    if diferenza <= 0:
        puntos = ENCAIXA
        motivo = Motivo("A súa enerxía encaixa co teu ritmo", True, "actividade")
    else:
        puntos = CON_RESERVAS if diferenza == 1 else NON_ENCAIXA
        motivo = Motivo("Necesita máis actividade da que tes", False, "actividade")
    if can.require_experiencia and not perfil.experiencia:
        # A falta de experiencia resta medio punto e o aviso substitúe ao encaixe
        puntos = max(NON_ENCAIXA, puntos - CON_RESERVAS)
        motivo = Motivo("Recoméndase experiencia previa con cans", False, "actividade")
    return puntos, motivo


_AVALIADORES = {
    "vivenda": _avaliar_vivenda,
    "tamano": _avaliar_tamano,
    "horas_so": _avaliar_horas_so,
    "nenos": _avaliar_nenos,
    "outros_animais": _avaliar_outros_animais,
    "actividade": _avaliar_actividade,
}


# ---------------------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------------------


def calcular(perfil: PerfilAdoptante, can: NecesidadesCan) -> Resultado:
    """Calcula a compatibilidade entre unha persoa e un can.

    Devolve un Resultado coa porcentaxe (enteiro de 0 a 100) e os motivos de cada
    dimensión que achega información.
    """
    puntos_ponderados = 0.0
    motivos = []
    for dimension, avaliar in _AVALIADORES.items():
        puntos, motivo = avaliar(perfil, can)
        puntos_ponderados += PESOS[dimension] * puntos
        if motivo is not None:
            motivos.append(motivo)

    porcentaxe = round(100 * puntos_ponderados / sum(PESOS.values()))
    if any(motivo.forte for motivo in motivos):
        porcentaxe = min(porcentaxe, TOPE_INCOMPATIBILIDADE)
    return Resultado(porcentaxe=porcentaxe, motivos=motivos)
