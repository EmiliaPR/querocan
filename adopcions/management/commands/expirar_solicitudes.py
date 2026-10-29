"""
Caduca as solicitudes aceptadas que levan máis de 7 días sen completarse.

Execútao cada hora o servizo «tarefas» de compose.yaml, e tamén se pode lanzar a man:
    docker compose exec web python manage.py expirar_solicitudes
Pódese executar tantas veces como se queira: unha solicitude xa caducada non se toca.
"""

from django.core.management.base import BaseCommand

from adopcions.estados import caducar_vencidas


class Command(BaseCommand):
    help = "Caduca as solicitudes aceptadas que superaron o prazo para completar a adopción."

    def handle(self, *args, **options):
        total = caducar_vencidas()
        self.stdout.write(f"Solicitudes caducadas: {total}")
