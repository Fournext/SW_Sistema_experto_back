from django.core.management.base import BaseCommand
from apps.permisos.services import PermisoService


class Command(BaseCommand):
    help = "Sincroniza el catálogo de permisos en código con la base de datos de Django y actualiza los grupos por defecto."

    def add_arguments(self, parser):
        parser.add_argument(
            "--silent",
            action="store_true",
            help="Modo silencioso sin mensajes de salida en consola.",
        )
        parser.add_argument(
            "--conservar-obsoletos",
            action="store_true",
            help="Conserva los permisos en base de datos que ya no estén presentes en el catálogo.",
        )
        parser.add_argument(
            "--no-grupos",
            action="store_true",
            help="No sincroniza ni altera los permisos asociados a los grupos base.",
        )

    def handle(self, *args, **options):
        verbose = not options["silent"]
        conservar = options["conservar_obsoletos"]
        sin_grupos = options["no_grupos"]

        if verbose:
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(self.style.SUCCESS("  SINCRONIZACIÓN DE PERMISOS DEL SISTEMA EXPERTO"))
            self.stdout.write(self.style.SUCCESS("=" * 60))

        resultado = PermisoService.escanear_y_generar_permisos(
            verbose=verbose,
            eliminar_obsoletos=not conservar,
            sincronizar_grupos=not sin_grupos,
        )

        if verbose:
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(
                self.style.SUCCESS(
                    f"Listo: {resultado['creados']} creados, "
                    f"{resultado['actualizados']} actualizados, "
                    f"{resultado['eliminados']} eliminados."
                )
            )
