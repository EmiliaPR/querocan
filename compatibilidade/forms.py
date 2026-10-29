"""Formulario do test de compatibilidade (seis preguntas) e de localización."""

from django import forms

from compatibilidade.calculo import (
    HorasSo,
    Nivel,
    OutrosAnimais,
    PerfilAdoptante,
    PreferenciaTamano,
    Vivenda,
    opcions,
)
from contas.forms import CampoConcello

SI_NON = [("si", "Si"), ("non", "Non")]


class FormularioTest(forms.Form):
    """As seis preguntas do test. Cada «pregunta» do deseño agrupa un ou dous campos."""

    # Agrupación en pantallas (unha pregunta por pantalla, como na proposta gráfica)
    PREGUNTAS = [
        ("Onde vives?", ["vivenda"]),
        ("Que tamaño de can encaixa na túa casa?", ["tamano"]),
        ("Cantas horas estaría só o can nun día normal?", ["horas_so"]),
        ("Hai nenos na casa?", ["ten_nenos"]),
        ("Hai outros animais na casa?", ["outros_animais"]),
        ("Como é o teu ritmo de vida?", ["actividade", "experiencia"]),
    ]

    vivenda = forms.ChoiceField(label="Vivenda", choices=opcions(Vivenda), widget=forms.RadioSelect)
    tamano = forms.ChoiceField(
        label="Tamaño", choices=opcions(PreferenciaTamano), widget=forms.RadioSelect
    )
    horas_so = forms.ChoiceField(
        label="Horas só", choices=opcions(HorasSo), widget=forms.RadioSelect
    )
    ten_nenos = forms.ChoiceField(label="Nenos na casa", choices=SI_NON, widget=forms.RadioSelect)
    outros_animais = forms.ChoiceField(
        label="Outros animais", choices=opcions(OutrosAnimais), widget=forms.RadioSelect
    )
    actividade = forms.ChoiceField(
        label="Actividade diaria (paseos, saídas, deporte)",
        choices=[("baixo", "Tranquila"), ("medio", "Moderada"), ("alto", "Moi activa")],
        widget=forms.RadioSelect,
    )
    experiencia = forms.ChoiceField(
        label="Xa tiveches can antes?", choices=SI_NON, widget=forms.RadioSelect
    )

    def preguntas(self):
        """Lista de (número, título, [campos]) para pintar o test pantalla a pantalla."""
        return [
            (numero, titulo, [self[campo] for campo in campos])
            for numero, (titulo, campos) in enumerate(self.PREGUNTAS, start=1)
        ]

    def perfil(self) -> PerfilAdoptante:
        datos = self.cleaned_data
        return PerfilAdoptante(
            vivenda=Vivenda(datos["vivenda"]),
            tamano=PreferenciaTamano(datos["tamano"]),
            horas_so=HorasSo(datos["horas_so"]),
            ten_nenos=datos["ten_nenos"] == "si",
            outros_animais=OutrosAnimais(datos["outros_animais"]),
            actividade=Nivel(datos["actividade"]),
            experiencia=datos["experiencia"] == "si",
        )

    @classmethod
    def inicial_desde(cls, perfil: PerfilAdoptante | None):
        """Valores iniciais para repetir o test coas respostas anteriores marcadas."""
        if perfil is None:
            return {}
        return {
            "vivenda": perfil.vivenda.value,
            "tamano": perfil.tamano.value,
            "horas_so": perfil.horas_so.value,
            "ten_nenos": "si" if perfil.ten_nenos else "non",
            "outros_animais": perfil.outros_animais.value,
            "actividade": perfil.actividade.value,
            "experiencia": "si" if perfil.experiencia else "non",
        }


class FormularioLocalizacion(forms.Form):
    """Localización por GPS (latitude e lonxitude) ou escollendo un concello."""

    latitude = forms.FloatField(required=False, min_value=-90, max_value=90)
    lonxitude = forms.FloatField(required=False, min_value=-180, max_value=180)
    concello = CampoConcello(required=False, label="O teu concello")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["concello"].agrupar()

    def clean(self):
        datos = super().clean()
        con_gps = datos.get("latitude") is not None and datos.get("lonxitude") is not None
        if not con_gps and not datos.get("concello"):
            raise forms.ValidationError("Indica a túa localización ou escolle un concello.")
        return datos
