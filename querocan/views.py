"""Vistas xerais do proxecto que non pertencen a ningunha app concreta."""

from django.db import connection
from django.http import JsonResponse


def saude(request):
    """Comproba que a aplicación responde e que a base de datos está accesible.

    Útil para saber dun vistazo se o contorno de Docker arrancou ben.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"estado": "ok", "base_de_datos": connection.vendor})
