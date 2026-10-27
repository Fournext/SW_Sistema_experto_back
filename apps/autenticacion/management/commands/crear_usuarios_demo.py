import os
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from apps.permisos.services import PermisoService

Usuario = get_user_model()


class Command(BaseCommand):
    help = "Crea los usuarios de demostración base: admin.central, docente1 y estudiante1."

    def handle(self, *args, **options):
        PermisoService.escanear_y_generar_permisos(verbose=False)

        clave_demo = os.environ.get("DEMO_PASSWORD", "Admin1234*")

        usuarios_data = [
            {
                "username": "admin.central",
                "email": "admin@sistema.edu.bo",
                "nombre_completo": "Administrador General",
                "grupo": "Administrador central",
                "is_staff": True,
                "is_superuser": True,
            },
            {
                "username": "docente1",
                "email": "docente1@sistema.edu.bo",
                "nombre_completo": "Prof. Carlos Ramos",
                "grupo": "Docente",
                "is_staff": False,
                "is_superuser": False,
            },
            {
                "username": "estudiante1",
                "email": "estudiante1@sistema.edu.bo",
                "nombre_completo": "María Flores",
                "grupo": "Estudiante",
                "is_staff": False,
                "is_superuser": False,
            },
        ]

        self.stdout.write(self.style.NOTICE("Creando usuarios de demostración..."))

        for d in usuarios_data:
            usuario, created = Usuario.objects.get_or_create(
                username=d["username"],
                defaults={
                    "email": d["email"],
                    "nombre_completo": d["nombre_completo"],
                    "is_staff": d["is_staff"],
                    "is_superuser": d["is_superuser"],
                    "is_active": True,
                },
            )
            usuario.set_password(clave_demo)
            usuario.save()

            if d["grupo"]:
                grupo = Group.objects.filter(name=d["grupo"]).first()
                if grupo:
                    usuario.groups.add(grupo)

            estado = "Creado" if created else "Actualizado"
            self.stdout.write(self.style.SUCCESS(f"  [+] {estado}: {d['username']} (Rol: {d['grupo']}, Clave: {clave_demo})"))

        self.stdout.write(self.style.SUCCESS("\nUsuarios de demostracion listos."))
