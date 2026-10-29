"""Variables dispoñibles en todas as plantillas."""

from django.conf import settings


def globais(request):
    return {"CONTACTO_EMAIL": settings.CONTACTO_EMAIL}
