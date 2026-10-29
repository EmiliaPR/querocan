"""
Distancia entre dous puntos da Terra (fórmula de Haversine).

Python puro, sen Django. Úsase para filtrar os cans por proximidade e para amosar
«A 12 km» nas tarxetas. A precisión (uns metros) sobra para este uso.
"""

from math import asin, cos, radians, sin, sqrt

RAIO_TERRA_KM = 6371.0


def distancia_km(lat1, lon1, lat2, lon2):
    """Distancia en liña recta, en quilómetros, entre dous puntos (graos decimais)."""
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * RAIO_TERRA_KM * asin(sqrt(a))


def texto_distancia(km):
    """Texto curto para a interface: «A menos de 1 km», «A 12 km»."""
    if km is None:
        return ""
    if km < 1:
        return "menos de 1 km"
    return f"{round(km)} km"
