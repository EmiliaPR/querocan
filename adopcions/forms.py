"""Formularios do fluxo de adopción: checklist e datos do contrato."""

from django import forms

from .contrato import nif_valido


class FormularioChecklist(forms.Form):
    """Un checkbox obrigatorio por cada compromiso activo."""

    def __init__(self, *args, items, **kwargs):
        super().__init__(*args, **kwargs)
        for item in items:
            self.fields[f"item_{item.pk}"] = forms.BooleanField(
                label=item.texto,
                error_messages={"required": "Tes que aceptar este compromiso."},
            )


class FormularioContrato(forms.Form):
    """Datos da persoa adoptante que aparecen no contrato."""

    nome = forms.CharField(label="Nome e apelidos", max_length=150)
    nif = forms.CharField(label="NIF ou NIE", max_length=10, help_text="Por exemplo: 12345678Z")
    enderezo = forms.CharField(label="Enderezo completo", max_length=250)
    telefono = forms.CharField(label="Teléfono de contacto", max_length=20)
    email = forms.EmailField(label="Correo electrónico")
    acepto = forms.BooleanField(
        label="Lin o contrato e acepto as condicións",
        error_messages={"required": "Tes que aceptar o contrato para completar a adopción."},
    )

    def clean_nif(self):
        nif = self.cleaned_data["nif"].upper().replace("-", "").replace(" ", "")
        if not nif_valido(nif):
            raise forms.ValidationError("O NIF ou NIE non é válido (revisa a letra).")
        return nif

    def clean_telefono(self):
        telefono = self.cleaned_data["telefono"].replace(" ", "")
        if not telefono.lstrip("+").isdigit() or len(telefono) < 9:
            raise forms.ValidationError("Escribe un teléfono válido.")
        return telefono
