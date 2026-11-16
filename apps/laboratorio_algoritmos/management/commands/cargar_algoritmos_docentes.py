import hashlib
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.laboratorio_algoritmos.models import ProgramaAlgoritmoModel, RevisionProgramaModel
from apps.laboratorio_algoritmos.plantillas import EJERCICIOS_ALGORITMOS


class Command(BaseCommand):
    help = "Carga los algoritmos de los Ejercicios 7, 8 y 13 como programas propios para los docentes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            default=None,
            help="Usuario específico al cual asignar los algoritmos (opcional).",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options.get("username")

        if username:
            docentes = User.objects.filter(username=username)
            if not docentes.exists():
                self.stderr.write(self.style.ERROR(f"Usuario '{username}' no encontrado."))
                return
        else:
            docentes = User.objects.filter(groups__name="Docente").distinct()
            if not docentes.exists():
                docentes = User.objects.filter(is_staff=True)

        self.stdout.write(f"Iniciando carga de algoritmos para {docentes.count()} docente(s)...")

        total_creados = 0
        for docente in docentes:
            self.stdout.write(f"-> Procesando docente: {docente.username} ({docente.get_full_name() or docente.email})")
            for ej in EJERCICIOS_ALGORITMOS:
                titulo = ej["titulo"]
                descripcion = ej["descripcion"]
                codigo = ej["codigo"].strip()

                programa, creado = ProgramaAlgoritmoModel.objects.update_or_create(
                    owner=docente,
                    titulo=titulo,
                    defaults={
                        "descripcion": descripcion,
                        "codigo_fuente": codigo,
                        "version_entero": 1,
                        "sistema_experto": None,
                    }
                )

                h = hashlib.sha256(codigo.encode("utf-8")).hexdigest()
                RevisionProgramaModel.objects.get_or_create(
                    programa=programa,
                    numero_revision=1,
                    defaults={
                        "codigo_fuente": codigo,
                        "hash_fuente": h,
                    }
                )

                accion = "Creado" if creado else "Actualizado"
                self.stdout.write(self.style.SUCCESS(f"   [{accion}] {programa.titulo} (ID: {programa.id})"))
                if creado:
                    total_creados += 1

        self.stdout.write(self.style.SUCCESS(f"\n¡Proceso finalizado! Total programas creados: {total_creados}"))

