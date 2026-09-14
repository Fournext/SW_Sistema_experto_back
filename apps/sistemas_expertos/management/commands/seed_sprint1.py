"""
Comando de Django para poblar la base de datos con los datos de ejemplo del Sprint 1.
Sistema experto: 'Recomendador de metodología de desarrollo'.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.sistemas_expertos.models import SistemaExpertoModel
from apps.base_conocimiento.models import (
    BaseConocimientoModel,
    HechoModel,
    ReglaModel,
    CondicionModel,
    ConclusionModel,
)
from apps.editor_visual.models import NodoVisualModel, ConexionVisualModel
from compartido.constantes.enums import EstadoSistema, TipoDato, OperadorCondicion, TipoNodoVisual


class Command(BaseCommand):
    help = "Puebla la base de datos con el ejemplo oficial del Sprint 1: Recomendador de metodología de desarrollo"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando sembrado de datos para Sprint 1..."))

        nombre_sistema = "Recomendador de metodología de desarrollo"
        # Limpiar si ya existe para asegurar idempotencia
        SistemaExpertoModel.objects.filter(nombre=nombre_sistema).delete()

        # 1. Crear Sistema Experto
        sistema = SistemaExpertoModel.objects.create(
            nombre=nombre_sistema,
            descripcion=(
                "Sistema experto educativo que sugiere metodologías ágiles o tradicionales "
                "según las características del proyecto."
            ),
            estado=EstadoSistema.ACTIVO.value,
        )
        self.stdout.write(self.style.SUCCESS(f"Sistema Experto creado: {sistema.nombre} (ID: {sistema.id})"))

        # 2. Base de Conocimiento (1:1)
        base = BaseConocimientoModel.objects.create(
            sistema_experto=sistema,
            nombre="BC - Metodologías de Desarrollo",
            version=1,
        )
        self.stdout.write(self.style.SUCCESS(f"Base de Conocimiento creada: {base.nombre}"))

        # 3. Hechos
        h_equipo = HechoModel.objects.create(
            base_conocimiento=base,
            nombre="equipo_pequeno",
            valor="true",
            tipo_dato=TipoDato.BOOLEANO.value,
            es_inicial=True,
        )
        h_requisitos = HechoModel.objects.create(
            base_conocimiento=base,
            nombre="requisitos_cambiantes",
            valor="true",
            tipo_dato=TipoDato.BOOLEANO.value,
            es_inicial=True,
        )
        h_recomendacion = HechoModel.objects.create(
            base_conocimiento=base,
            nombre="recomendacion",
            valor=None,
            tipo_dato=TipoDato.TEXTO.value,
            es_inicial=False,
        )
        self.stdout.write(self.style.SUCCESS("Hechos creados: equipo_pequeno, requisitos_cambiantes, recomendacion"))

        # 4. Regla R1
        regla_r1 = ReglaModel.objects.create(
            base_conocimiento=base,
            nombre="R1 - Recomendar Scrum",
            descripcion="Si el equipo es pequeño y los requisitos son cambiantes, recomendar Scrum.",
            prioridad=10,
            factor_certeza=Decimal("0.90"),
            activa=True,
        )

        # 5. Condiciones para R1
        CondicionModel.objects.create(
            regla=regla_r1,
            hecho=h_equipo,
            operador=OperadorCondicion.IGUAL.value,
            valor_esperado="true",
            orden=1,
        )
        CondicionModel.objects.create(
            regla=regla_r1,
            hecho=h_requisitos,
            operador=OperadorCondicion.IGUAL.value,
            valor_esperado="true",
            orden=2,
        )

        # 6. Conclusión para R1
        conc1 = ConclusionModel.objects.create(
            regla=regla_r1,
            hecho_resultante=h_recomendacion,
            valor_resultante="Scrum",
        )
        self.stdout.write(self.style.SUCCESS("Regla R1 creada con sus 2 condiciones y conclusión."))

        # 7. Nodos Visuales en el lienzo
        nodo_h1 = NodoVisualModel.objects.create(
            sistema_experto=sistema,
            tipo=TipoNodoVisual.HECHO.value,
            referencia_id=h_equipo.id,
            posicion_x=Decimal("100.00"),
            posicion_y=Decimal("100.00"),
        )
        nodo_h2 = NodoVisualModel.objects.create(
            sistema_experto=sistema,
            tipo=TipoNodoVisual.HECHO.value,
            referencia_id=h_requisitos.id,
            posicion_x=Decimal("100.00"),
            posicion_y=Decimal("250.00"),
        )
        nodo_r1 = NodoVisualModel.objects.create(
            sistema_experto=sistema,
            tipo=TipoNodoVisual.REGLA.value,
            referencia_id=regla_r1.id,
            posicion_x=Decimal("400.00"),
            posicion_y=Decimal("175.00"),
        )
        nodo_conc = NodoVisualModel.objects.create(
            sistema_experto=sistema,
            tipo=TipoNodoVisual.CONCLUSION.value,
            referencia_id=conc1.id,
            posicion_x=Decimal("700.00"),
            posicion_y=Decimal("175.00"),
        )

        # 8. Conexiones visuales
        ConexionVisualModel.objects.create(
            sistema_experto=sistema,
            nodo_origen=nodo_h1,
            nodo_destino=nodo_r1,
            etiqueta="Premisa 1",
            tipo="CONDICIONAL",
        )
        ConexionVisualModel.objects.create(
            sistema_experto=sistema,
            nodo_origen=nodo_h2,
            nodo_destino=nodo_r1,
            etiqueta="Premisa 2",
            tipo="CONDICIONAL",
        )
        ConexionVisualModel.objects.create(
            sistema_experto=sistema,
            nodo_origen=nodo_r1,
            nodo_destino=nodo_conc,
            etiqueta="Dispara",
            tipo="CONSECUENTE",
        )
        self.stdout.write(self.style.SUCCESS("Nodos y conexiones visuales creados en el lienzo."))
        self.stdout.write(self.style.SUCCESS(f"\n¡Sembrado completado con éxito! UUID del Sistema: {sistema.id}"))
