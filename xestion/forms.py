"""Formularios do panel de xestión."""

from django import forms

from adopcions.models import ItemChecklist, ModeloContrato
from contido.models import Enlace, Testemuno


class FormularioPeriodo(forms.Form):
    """Filtro do funil por protectora e datas."""

    protectora = forms.ModelChoiceField(queryset=None, required=False, empty_label="Todas")
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    ata = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        from contas.models import Protectora

        super().__init__(*args, **kwargs)
        self.fields["protectora"].queryset = Protectora.objects.all()


class FormularioTestemuno(forms.ModelForm):
    class Meta:
        model = Testemuno
        fields = ["nome_persoa", "nome_can", "texto", "foto", "publicado", "orde"]
        widgets = {"texto": forms.Textarea(attrs={"rows": 4})}

    def clean_foto(self):
        from animais.imaxes import preparar_imaxe

        foto = self.cleaned_data.get("foto")
        # Só preparamos as fotos novas (as xa gardadas non teñen content_type)
        if foto and hasattr(foto, "content_type"):
            return preparar_imaxe(foto)
        return foto


class FormularioEnlace(forms.ModelForm):
    url = forms.URLField(label="Enderezo", assume_scheme="https", max_length=300)

    class Meta:
        model = Enlace
        fields = ["titulo", "url", "descricion", "orde"]


class FormularioItemChecklist(forms.ModelForm):
    class Meta:
        model = ItemChecklist
        fields = ["texto", "orde", "activo"]


class FormularioContrato(forms.ModelForm):
    """Ao gardar créase unha versión nova; as aceptacións anteriores non cambian."""

    class Meta:
        model = ModeloContrato
        fields = ["texto"]
        widgets = {"texto": forms.Textarea(attrs={"rows": 24})}
        help_texts = {
            "texto": "Marcadores dispoñibles: {nome}, {nif}, {enderezo}, {telefono}, {email}, "
            "{can}, {protectora}, {data}."
        }
