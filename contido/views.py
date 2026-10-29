"""
Vistas das páxinas públicas de contido.

Non requiren conta: calquera visitante pode ver a landing, o manual, os enlaces e
os testemuños de Finais felices.
"""

from django.shortcuts import render


def landing(request):
    """Páxina de inicio: explica QueroCan «coma un Tinder» para adoptar cans."""
    return render(request, "contido/landing.html")
