import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from apps.permisos.services import PermisoService

Usuario = get_user_model()


class Command(BaseCommand):
    help = "Crea un usuario administrador para Admin Central y le asigna el rol 'Administrador central'."

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, default="admin.central", help="Nombre de usuario del administrador.")
        parser.add_argument("--email", type=str, default="admin.central@sistema.edu.bo", help="Correo electrónico.")
        parser.add_argument("--password", type=str, default=None, help="Contraseña (opcional, si se omite se solicitará de forma segura).")

    def handle(self, *args, **options):
        # Asegurar catálogo y grupos sincronizados
        PermisoService.escanear_y_generar_permisos(verbose=False)

        username = options["username"]
        email = options["email"]
        password = options["password"]

        if not password:
            password = getpass.getpass(f"Ingrese la contraseña para '{username}': ")

        usuario, created = Usuario.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "nombre_completo": "Administrador Central",
                "is_staff": True,
                "is_superuser": True,
            },
        )

        usuario.set_password(password)
        usuario.is_active = True
        usuario.save()

        grupo_admin, _ = Group.objects.get_or_create(name="Administrador central")
        usuario.groups.add(grupo_admin)

        accion = "creado" if created else "actualizado"
        self.stdout.write(self.style.SUCCESS(f"✓ Administrador central '{username}' {accion} exitosamente."))
