"""Formularios da protectora para publicar e editar cans."""

from django import forms

from .models import Can

# Campos das necesidades: amósanse como botóns de opción grandes e son obrigatorios
CAMPOS_NECESIDADES = [
    "espazo",
    "tolerancia_soidade",
    "convive_nenos",
    "convive_cans",
    "convive_gatos",
    "enerxia",
]


class FormularioCan(forms.ModelForm):
    """Ficha completa dun can: datos públicos e necesidades de compatibilidade."""

    class Meta:
        model = Can
        fields = [
            "nome",
            "sexo",
            "data_nacemento",
            "tamano",
            "peso_kg",
            "raza",
            "etiquetas",
            "urxente",
            "descricion",
            "vacinado",
            "desparasitado",
            "microchip",
            "esterilizado",
            *CAMPOS_NECESIDADES,
            "require_experiencia",
        ]
        widgets = {
            "sexo": forms.RadioSelect,
            "tamano": forms.RadioSelect,
            "data_nacemento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "descricion": forms.Textarea(attrs={"rows": 6}),
            **{campo: forms.RadioSelect for campo in CAMPOS_NECESIDADES},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Django engade unha opción baleira «---------» aos RadioSelect de campos con
        # choices; quitámola para que a protectora teña que escoller un valor
        for nome in ["sexo", "tamano", *CAMPOS_NECESIDADES]:
            campo = self.fields[nome]
            campo.choices = [(v, t) for v, t in campo.choices if v != ""]
            campo.required = True

    def clean_etiquetas(self):
        etiquetas = [e.strip() for e in self.cleaned_data["etiquetas"].split(",") if e.strip()]
        if len(etiquetas) > 4:
            raise forms.ValidationError("Como moito, catro palabras de carácter.")
        return ", ".join(etiquetas)

    def clean_data_nacemento(self):
        from datetime import date

        data = self.cleaned_data["data_nacemento"]
        if data > date.today():
            raise forms.ValidationError("A data de nacemento non pode ser no futuro.")
        return data


class FormularioFoto(forms.Form):
    """Subida dunha foto. A validación e o redimensionado fanse en imaxes.py."""

    imaxe = forms.ImageField(
        label="Engadir unha foto",
        help_text="JPEG, PNG ou WebP de ata 5 MB. Redimensionámola automaticamente.",
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
    )

    def clean_imaxe(self):
        from .imaxes import preparar_imaxe

        return preparar_imaxe(self.cleaned_data["imaxe"])
