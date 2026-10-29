"""
Probas do cálculo de compatibilidade.

Cobren cada regra de cada dimensión, o tope das incompatibilidades fortes e a orde
que producen os tres perfís de demostración sobre un conxunto fixo de cans.
"""

from dataclasses import replace

import pytest

from compatibilidade.calculo import (
    PESOS,
    TOPE_INCOMPATIBILIDADE,
    Convivencia,
    Espazo,
    HorasSo,
    NecesidadesCan,
    Nivel,
    OutrosAnimais,
    PerfilAdoptante,
    PreferenciaTamano,
    Tamano,
    Tolerancia,
    Vivenda,
    calcular,
    etiqueta,
    opcions,
)

# Un perfil e un can que encaixan en todo: as probas cambian só o que necesitan
PERFIL_BASE = PerfilAdoptante(
    vivenda=Vivenda.CASA_CON_PATIO,
    tamano=PreferenciaTamano.MEDIANO,
    horas_so=HorasSo.MENOS_DE_2,
    ten_nenos=False,
    outros_animais=OutrosAnimais.NINGUN,
    actividade=Nivel.ALTO,
    experiencia=True,
)
CAN_BASE = NecesidadesCan(
    espazo=Espazo.INDIFERENTE,
    tamano=Tamano.MEDIANO,
    tolerancia_soidade=Tolerancia.ALTA,
    convive_nenos=Convivencia.SI,
    convive_cans=Convivencia.SI,
    convive_gatos=Convivencia.SI,
    enerxia=Nivel.MEDIO,
    require_experiencia=False,
)


def motivo_de(resultado, dimension):
    return next(m for m in resultado.motivos if m.dimension == dimension)


def test_perfil_e_can_ideais_dan_100():
    resultado = calcular(PERFIL_BASE, CAN_BASE)
    assert resultado.porcentaxe == 100
    assert all(m.encaixa for m in resultado.motivos)
    assert not resultado.ten_incompatibilidade_forte


def test_os_pesos_suman_14():
    assert sum(PESOS.values()) == 14


# --- Vivenda --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("espazo", "vivenda", "porcentaxe", "encaixa", "forte"),
    [
        (Espazo.INDIFERENTE, Vivenda.PISO, 100, True, False),
        (Espazo.PATIO_RECOMENDADO, Vivenda.CASA_CON_PATIO, 100, True, False),
        (Espazo.PATIO_RECOMENDADO, Vivenda.PISO, 89, False, False),  # 12,5/14
        (Espazo.PATIO_RECOMENDADO, Vivenda.CASA_SEN_PATIO, 89, False, False),
        (Espazo.PATIO_NECESARIO, Vivenda.CASA_CON_PATIO, 100, True, False),
        (Espazo.PATIO_NECESARIO, Vivenda.PISO, TOPE_INCOMPATIBILIDADE, False, True),
        (Espazo.PATIO_NECESARIO, Vivenda.CASA_SEN_PATIO, TOPE_INCOMPATIBILIDADE, False, True),
    ],
)
def test_vivenda(espazo, vivenda, porcentaxe, encaixa, forte):
    resultado = calcular(replace(PERFIL_BASE, vivenda=vivenda), replace(CAN_BASE, espazo=espazo))
    motivo = motivo_de(resultado, "vivenda")
    assert resultado.porcentaxe == porcentaxe
    assert motivo.encaixa is encaixa
    assert motivo.forte is forte


# --- Tamaño ---------------------------------------------------------------------------


def test_tamano_indiferente_non_xera_motivo():
    resultado = calcular(replace(PERFIL_BASE, tamano=PreferenciaTamano.INDIFERENTE), CAN_BASE)
    assert resultado.porcentaxe == 100
    assert all(m.dimension != "tamano" for m in resultado.motivos)


@pytest.mark.parametrize(
    ("buscado", "real", "porcentaxe", "texto"),
    [
        (PreferenciaTamano.MEDIANO, Tamano.MEDIANO, 100, "É do tamaño que buscas"),
        (PreferenciaTamano.PEQUENO, Tamano.MEDIANO, 96, "É máis grande do que buscas"),
        (PreferenciaTamano.PEQUENO, Tamano.GRANDE, 93, "É máis grande do que buscas"),
        (PreferenciaTamano.GRANDE, Tamano.PEQUENO, 93, "É máis pequeno do que buscas"),
    ],
)
def test_tamano(buscado, real, porcentaxe, texto):
    resultado = calcular(replace(PERFIL_BASE, tamano=buscado), replace(CAN_BASE, tamano=real))
    assert resultado.porcentaxe == porcentaxe
    assert motivo_de(resultado, "tamano").texto == texto


# --- Horas só -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tolerancia", "horas", "porcentaxe", "encaixa"),
    [
        (Tolerancia.BAIXA, HorasSo.MENOS_DE_2, 100, True),
        (Tolerancia.BAIXA, HorasSo.DE_2_A_4, 89, False),
        (Tolerancia.BAIXA, HorasSo.DE_4_A_6, 79, False),
        (Tolerancia.BAIXA, HorasSo.MAIS_DE_6, 79, False),
        (Tolerancia.MEDIA, HorasSo.DE_2_A_4, 100, True),
        (Tolerancia.MEDIA, HorasSo.DE_4_A_6, 89, False),
        (Tolerancia.ALTA, HorasSo.DE_4_A_6, 100, True),
        (Tolerancia.ALTA, HorasSo.MAIS_DE_6, 89, False),
    ],
)
def test_horas_so(tolerancia, horas, porcentaxe, encaixa):
    resultado = calcular(
        replace(PERFIL_BASE, horas_so=horas), replace(CAN_BASE, tolerancia_soidade=tolerancia)
    )
    assert resultado.porcentaxe == porcentaxe
    assert motivo_de(resultado, "horas_so").encaixa is encaixa


# --- Nenos ----------------------------------------------------------------------------


def test_sen_nenos_a_convivencia_con_nenos_non_importa():
    resultado = calcular(PERFIL_BASE, replace(CAN_BASE, convive_nenos=Convivencia.NON))
    assert resultado.porcentaxe == 100
    assert all(m.dimension != "nenos" for m in resultado.motivos)


@pytest.mark.parametrize(
    ("convivencia", "porcentaxe", "forte"),
    [
        (Convivencia.SI, 100, False),
        (Convivencia.DESCONECIDO, 89, False),
        (Convivencia.NON, TOPE_INCOMPATIBILIDADE, True),
    ],
)
def test_nenos(convivencia, porcentaxe, forte):
    resultado = calcular(
        replace(PERFIL_BASE, ten_nenos=True), replace(CAN_BASE, convive_nenos=convivencia)
    )
    assert resultado.porcentaxe == porcentaxe
    assert motivo_de(resultado, "nenos").forte is forte


# --- Outros animais -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("na_casa", "cans", "gatos", "porcentaxe", "texto"),
    [
        (OutrosAnimais.CANS, Convivencia.SI, Convivencia.NON, 100, "Convive con cans"),
        (OutrosAnimais.GATOS, Convivencia.NON, Convivencia.SI, 100, "Convive con gatos"),
        (
            OutrosAnimais.GATOS,
            Convivencia.SI,
            Convivencia.DESCONECIDO,
            93,
            "Non sabemos como se leva con gatos",
        ),
        (
            OutrosAnimais.CANS_E_GATOS,
            Convivencia.SI,
            Convivencia.NON,
            TOPE_INCOMPATIBILIDADE,
            "Non convive con gatos",
        ),
        (OutrosAnimais.CANS_E_GATOS, Convivencia.SI, Convivencia.SI, 100, "Convive con cans"),
    ],
)
def test_outros_animais(na_casa, cans, gatos, porcentaxe, texto):
    resultado = calcular(
        replace(PERFIL_BASE, outros_animais=na_casa),
        replace(CAN_BASE, convive_cans=cans, convive_gatos=gatos),
    )
    assert resultado.porcentaxe == porcentaxe
    assert motivo_de(resultado, "outros_animais").texto == texto


def test_sen_outros_animais_non_xera_motivo():
    resultado = calcular(PERFIL_BASE, replace(CAN_BASE, convive_gatos=Convivencia.NON))
    assert all(m.dimension != "outros_animais" for m in resultado.motivos)


# --- Actividade e experiencia ---------------------------------------------------------


@pytest.mark.parametrize(
    ("actividade", "enerxia", "porcentaxe", "encaixa"),
    [
        (Nivel.ALTO, Nivel.BAIXO, 100, True),
        (Nivel.MEDIO, Nivel.MEDIO, 100, True),
        (Nivel.MEDIO, Nivel.ALTO, 93, False),
        (Nivel.BAIXO, Nivel.ALTO, 86, False),
    ],
)
def test_actividade(actividade, enerxia, porcentaxe, encaixa):
    resultado = calcular(
        replace(PERFIL_BASE, actividade=actividade), replace(CAN_BASE, enerxia=enerxia)
    )
    assert resultado.porcentaxe == porcentaxe
    assert motivo_de(resultado, "actividade").encaixa is encaixa


def test_falta_de_experiencia_resta_e_avisa():
    resultado = calcular(
        replace(PERFIL_BASE, experiencia=False), replace(CAN_BASE, require_experiencia=True)
    )
    assert resultado.porcentaxe == 93
    assert motivo_de(resultado, "actividade").texto == "Recoméndase experiencia previa con cans"


def test_a_experiencia_non_baixa_de_cero():
    resultado = calcular(
        replace(PERFIL_BASE, experiencia=False, actividade=Nivel.BAIXO),
        replace(CAN_BASE, require_experiencia=True, enerxia=Nivel.ALTO),
    )
    assert resultado.porcentaxe == 86  # 12/14: a actividade xa era 0


def test_con_experiencia_non_hai_aviso():
    resultado = calcular(PERFIL_BASE, replace(CAN_BASE, require_experiencia=True))
    assert resultado.porcentaxe == 100


# --- Tope e motivos destacados --------------------------------------------------------


def test_unha_incompatibilidade_forte_nunca_supera_o_tope():
    """Aínda que todo o demais encaixe, non convivir con nenos limita ao 40 %."""
    resultado = calcular(
        replace(PERFIL_BASE, ten_nenos=True), replace(CAN_BASE, convive_nenos=Convivencia.NON)
    )
    assert resultado.porcentaxe == TOPE_INCOMPATIBILIDADE
    assert resultado.ten_incompatibilidade_forte


def test_o_tope_non_sube_porcentaxes_baixas():
    perfil = replace(
        PERFIL_BASE,
        vivenda=Vivenda.PISO,
        horas_so=HorasSo.MAIS_DE_6,
        ten_nenos=True,
        actividade=Nivel.BAIXO,
        tamano=PreferenciaTamano.PEQUENO,
    )
    can = replace(
        CAN_BASE,
        espazo=Espazo.PATIO_NECESARIO,
        tolerancia_soidade=Tolerancia.BAIXA,
        convive_nenos=Convivencia.NON,
        enerxia=Nivel.ALTO,
        tamano=Tamano.GRANDE,
    )
    # Só puntúa «outros animais» (non hai na casa): 2/14 ≈ 14 %, por debaixo do tope
    assert calcular(perfil, can).porcentaxe == 14


def test_motivos_destacados_priorizan_fortes_e_despois_avisos():
    resultado = calcular(
        replace(PERFIL_BASE, ten_nenos=True, tamano=PreferenciaTamano.PEQUENO),
        replace(CAN_BASE, convive_nenos=Convivencia.NON),
    )
    destacados = resultado.motivos_destacados()
    assert len(destacados) == 3
    assert destacados[0].texto == "Non convive con nenos"
    assert destacados[0].icona == "⚠"
    assert destacados[1].texto == "É máis grande do que buscas"
    assert destacados[2].icona == "✓"
    assert destacados[2].dimension in {"vivenda", "horas_so"}  # encaixes de peso 3


def test_opcions_devolve_pares_para_django():
    assert opcions(Vivenda)[0] == ("piso", "Piso")
    assert ("desconecido", "Non se sabe") in opcions(Convivencia)


def test_valores_compartidos_entre_enums_teñen_cada_un_a_súa_etiqueta():
    """«indiferente» existe en Espazo e en PreferenciaTamano con textos distintos."""
    assert etiqueta(Espazo, "indiferente") == "Adáptase a calquera vivenda"
    assert etiqueta(PreferenciaTamano, "indiferente") == "Non teño preferencia"
    assert dict(opcions(Espazo))["indiferente"] == "Adáptase a calquera vivenda"


# --- Os tres perfís da demostración ---------------------------------------------------

ESTUDANTE_EN_PISO = PerfilAdoptante(
    vivenda=Vivenda.PISO,
    tamano=PreferenciaTamano.PEQUENO,
    horas_so=HorasSo.DE_4_A_6,
    ten_nenos=False,
    outros_animais=OutrosAnimais.NINGUN,
    actividade=Nivel.ALTO,
    experiencia=False,
)
FAMILIA_CON_NENOS = PerfilAdoptante(
    vivenda=Vivenda.CASA_CON_PATIO,
    tamano=PreferenciaTamano.INDIFERENTE,
    horas_so=HorasSo.DE_2_A_4,
    ten_nenos=True,
    outros_animais=OutrosAnimais.CANS,
    actividade=Nivel.MEDIO,
    experiencia=True,
)
XUBILADA = PerfilAdoptante(
    vivenda=Vivenda.PISO,
    tamano=PreferenciaTamano.PEQUENO,
    horas_so=HorasSo.MENOS_DE_2,
    ten_nenos=False,
    outros_animais=OutrosAnimais.GATOS,
    actividade=Nivel.BAIXO,
    experiencia=True,
)

# Cans pensados para encaixar con cada perfil (e un que non encaixa con ninguén ben)
CANS = {
    # Pequeno, independente e activo: ideal para un piso con moitas horas fóra
    "Nina": NecesidadesCan(
        Espazo.INDIFERENTE,
        Tamano.PEQUENO,
        Tolerancia.ALTA,
        Convivencia.DESCONECIDO,
        Convivencia.SI,
        Convivencia.NON,
        Nivel.ALTO,
        False,
    ),
    # Grande, xogador, bo con nenos e cans, pide patio: ideal para a familia
    "Bruno": NecesidadesCan(
        Espazo.PATIO_RECOMENDADO,
        Tamano.GRANDE,
        Tolerancia.MEDIA,
        Convivencia.SI,
        Convivencia.SI,
        Convivencia.DESCONECIDO,
        Nivel.MEDIO,
        False,
    ),
    # Pequena, maior e tranquila, convive con gatos pero non soporta estar soa: xubilada
    "Mel": NecesidadesCan(
        Espazo.INDIFERENTE,
        Tamano.PEQUENO,
        Tolerancia.BAIXA,
        Convivencia.NON,
        Convivencia.SI,
        Convivencia.SI,
        Nivel.BAIXO,
        False,
    ),
    # Moita enerxía, necesita patio e experiencia
    "Trasno": NecesidadesCan(
        Espazo.PATIO_NECESARIO,
        Tamano.GRANDE,
        Tolerancia.MEDIA,
        Convivencia.SI,
        Convivencia.SI,
        Convivencia.NON,
        Nivel.ALTO,
        True,
    ),
}


def orde_para(perfil):
    resultados = {nome: calcular(perfil, can).porcentaxe for nome, can in CANS.items()}
    return sorted(resultados, key=resultados.get, reverse=True)


def test_orde_da_estudante_en_piso():
    assert orde_para(ESTUDANTE_EN_PISO)[0] == "Nina"


def test_orde_da_familia_con_nenos():
    orde = orde_para(FAMILIA_CON_NENOS)
    assert orde[0] in {"Bruno", "Trasno"}
    assert orde[-1] == "Mel"  # Mel non convive con nenos


def test_orde_da_xubilada():
    orde = orde_para(XUBILADA)
    assert orde[0] == "Mel"
    assert orde[-1] == "Trasno"
