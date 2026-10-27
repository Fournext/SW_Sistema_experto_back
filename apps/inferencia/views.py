"""
Vistas de API REST para el módulo de Inferencia y Simulación (Sprint 1 + Sprint 2).
"""
from uuid import UUID
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.views import APIView
from apps.permisos.visibilidad import puede_ver_borradores

from apps.inferencia.serializers import (
    ConflictoInferenciaSalidaSerializer,
    DetalleInferenciaSalidaSerializer,
    EjecucionInferenciaSalidaSerializer,
    EjecutarInferenciaSalidaSerializer,
    ExplicacionConclusionSalidaSerializer,
    HechoInferidoSalidaSerializer,
    HistorialInferenciaSalidaSerializer,
    IniciarSimulacionEntradaSerializer,
    PasoInferenciaSalidaSerializer,
)
from apps.inferencia.services import (
    AvanzarPasoSimulacion,
    ConsultarConflictosEjecucion,
    ConsultarEjecucion,
    ConsultarExplicacionConclusion,
    ConsultarHechosInferidos,
    ConsultarHistorialInferencia,
    ConsultarTrazaInferencia,
    ControlarSimulacion,
    EjecutarInferencia,
    IniciarSimulacion,
)
from compartido.respuestas.respuesta_api import respuesta_creada, respuesta_error, respuesta_exitosa


class InferenciaEjecutarAPIView(APIView):
    """Ejecuta el motor de inferencia automáticamente para un sistema experto."""

    @extend_schema(
        summary="Ejecutar motor de inferencia",
        description=(
            "Ejecuta el ciclo de razonamiento por encadenamiento hacia adelante. "
            "Permite enviar hechos_iniciales opcionales para pruebas interactivas."
        ),
        request=IniciarSimulacionEntradaSerializer,
        responses={
            201: OpenApiResponse(
                response=EjecutarInferenciaSalidaSerializer,
                description="Inferencia completada",
            ),
            404: OpenApiResponse(description="Sistema experto no encontrado"),
            422: OpenApiResponse(description="Límite de iteraciones alcanzado"),
        },
        tags=["Inferencia"],
    )
    def post(self, request, id: UUID):
        ser = IniciarSimulacionEntradaSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        hechos_custom = ser.validated_data.get("hechos_iniciales") or None

        caso_uso = EjecutarInferencia()
        resultado = caso_uso.ejecutar(
            sistema_experto_id=id, hechos_personalizados=hechos_custom
        )
        datos = EjecutarInferenciaSalidaSerializer(resultado).data
        return respuesta_creada(datos=datos, mensaje="Inferencia ejecutada correctamente.")


class SimulacionIniciarAPIView(APIView):
    """Inicializa una sesión de simulación interactiva con hechos temporales (HU-14)."""

    @extend_schema(
        summary="Iniciar simulación interactiva",
        description="Inicializa la memoria de trabajo y el estado de simulación para ejecución paso a paso.",
        request=IniciarSimulacionEntradaSerializer,
        responses={
            201: EjecucionInferenciaSalidaSerializer,
            404: OpenApiResponse(description="Sistema no encontrado"),
        },
        tags=["Simulación"],
    )
    def post(self, request, id: UUID):
        ser = IniciarSimulacionEntradaSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        hechos_custom = ser.validated_data.get("hechos_iniciales") or None

        caso_uso = IniciarSimulacion()
        ejecucion = caso_uso.ejecutar(
            sistema_experto_id=id, hechos_iniciales_custom=hechos_custom
        )
        datos = EjecucionInferenciaSalidaSerializer(ejecucion).data
        return respuesta_creada(datos=datos, mensaje="Simulación iniciada correctamente.")


class SimulacionAvanzarPasoAPIView(APIView):
    """Avanza exactamente un paso discreto en una simulación (HU-09, HU-15)."""

    @extend_schema(
        summary="Avanzar un paso en la simulación",
        description="Evalúa reglas, resuelve conflictos y dispara la regla seleccionada.",
        request=None,
        responses={
            200: OpenApiResponse(description="Paso ejecutado con detalle"),
            404: OpenApiResponse(description="Ejecución no encontrada"),
        },
        tags=["Simulación"],
    )
    def post(self, request, id: UUID):
        hechos_nuevos = None
        regla_id = None
        modo_evaluacion = None
        if request.data:
            hechos_nuevos = (
                request.data.get("hechos_nuevos")
                or request.data.get("hechos")
                or request.data.get("hechos_iniciales")
            )
            regla_id = request.data.get("regla_id")
            modo_evaluacion = request.data.get("modo_evaluacion")
        caso_uso = AvanzarPasoSimulacion()
        res = caso_uso.ejecutar(
            id_ejecucion=id,
            hechos_nuevos=hechos_nuevos,
            regla_id=regla_id,
            modo_evaluacion=modo_evaluacion,
        )
        if "paso" in res and res["paso"]:
            res["paso"] = PasoInferenciaSalidaSerializer(res["paso"]).data
        caso_ejec = ConsultarEjecucion()
        ejecucion = caso_ejec.ejecutar(id_ejecucion=id)
        datos_ejecucion = EjecucionInferenciaSalidaSerializer(ejecucion).data
        datos_completos = {**datos_ejecucion, **res}
        return respuesta_exitosa(datos=datos_completos, mensaje="Paso de simulación procesado.")


class SimulacionControlAPIView(APIView):
    """Permite pausar, continuar, reiniciar o finalizar una simulación vía acción unificada (HU-15)."""

    @extend_schema(
        summary="Controlar ciclo de vida de la simulación",
        description="Acepta acciones: PAUSAR, CONTINUAR, REINICIAR, FINALIZAR.",
        tags=["Simulación"],
    )
    def post(self, request, id: UUID):
        accion = (request.data.get("accion") or "").upper()
        caso_uso = ControlarSimulacion()

        if accion == "PAUSAR":
            ejecucion = caso_uso.pausar(id_ejecucion=id)
            msg = "Simulación pausada."
        elif accion == "CONTINUAR":
            ejecucion = caso_uso.continuar(id_ejecucion=id)
            estado = getattr(ejecucion.estado, "value", ejecucion.estado)
            msg = "Simulación completada." if estado == "FINALIZADA" else "Simulación reanudada."
        elif accion == "REINICIAR":
            ejecucion = caso_uso.reiniciar(id_ejecucion=id)
            msg = "Simulación reiniciada a valores iniciales."
        elif accion == "FINALIZAR":
            ejecucion = caso_uso.finalizar(id_ejecucion=id)
            msg = "Simulación finalizada."
        else:
            return respuesta_error(
                mensaje=f"Acción '{accion}' no válida. Use PAUSAR, CONTINUAR, REINICIAR o FINALIZAR.",
                codigo_estado=status.HTTP_400_BAD_REQUEST,
            )

        datos = EjecucionInferenciaSalidaSerializer(ejecucion).data
        return respuesta_exitosa(datos=datos, mensaje=msg)


class SimulacionPausarAPIView(APIView):
    """Pausa una sesión de simulación en curso (HU-15)."""

    @extend_schema(
        summary="Pausar simulación",
        request=None,
        responses={200: EjecucionInferenciaSalidaSerializer},
        tags=["Simulación"],
    )
    def post(self, request, id: UUID):
        caso_uso = ControlarSimulacion()
        ejecucion = caso_uso.pausar(id_ejecucion=id)
        datos = EjecucionInferenciaSalidaSerializer(ejecucion).data
        return respuesta_exitosa(datos=datos, mensaje="Simulación pausada.")


class SimulacionContinuarAPIView(APIView):
    """Reanuda la ejecución continua de una simulación pausada (HU-15)."""

    @extend_schema(
        summary="Continuar simulación",
        request=None,
        responses={200: EjecucionInferenciaSalidaSerializer},
        tags=["Simulación"],
    )
    def post(self, request, id: UUID):
        caso_uso = ControlarSimulacion()
        ejecucion = caso_uso.continuar(id_ejecucion=id)
        datos = EjecucionInferenciaSalidaSerializer(ejecucion).data
        estado = getattr(ejecucion.estado, "value", ejecucion.estado)
        mensaje = "Simulación completada." if estado == "FINALIZADA" else "Simulación reanudada."
        return respuesta_exitosa(datos=datos, mensaje=mensaje)


class SimulacionReiniciarAPIView(APIView):
    """Restablece la memoria de trabajo a los hechos iniciales (HU-15)."""

    @extend_schema(
        summary="Reiniciar simulación",
        request=None,
        responses={200: EjecucionInferenciaSalidaSerializer},
        tags=["Simulación"],
    )
    def post(self, request, id: UUID):
        caso_uso = ControlarSimulacion()
        ejecucion = caso_uso.reiniciar(id_ejecucion=id)
        datos = EjecucionInferenciaSalidaSerializer(ejecucion).data
        return respuesta_exitosa(datos=datos, mensaje="Simulación reiniciada a valores iniciales.")


class SimulacionFinalizarAPIView(APIView):
    """Finaliza voluntariamente una simulación activa (HU-15)."""

    @extend_schema(
        summary="Finalizar simulación",
        request=None,
        responses={200: EjecucionInferenciaSalidaSerializer},
        tags=["Simulación"],
    )
    def post(self, request, id: UUID):
        caso_uso = ControlarSimulacion()
        ejecucion = caso_uso.finalizar(id_ejecucion=id)
        datos = EjecucionInferenciaSalidaSerializer(ejecucion).data
        return respuesta_exitosa(datos=datos, mensaje="Simulación finalizada.")


class InferenciaHistorialAPIView(APIView):
    """Consulta el historial de ejecuciones con filtros (HU-16)."""

    @extend_schema(
        summary="Consultar historial de inferencia",
        parameters=[
            OpenApiParameter("sistema_id", type=UUID, description="Filtrar por sistema experto"),
            OpenApiParameter("estado", type=str, description="Filtrar por estado"),
            OpenApiParameter("modo", type=str, description="Filtrar por modo"),
        ],
        responses={200: HistorialInferenciaSalidaSerializer(many=True)},
        tags=["Inferencia"],
    )
    def get(self, request):
        sistema_id = request.query_params.get("sistema_id") or request.query_params.get("sistema_experto_id")
        estado = request.query_params.get("estado")
        modo = request.query_params.get("modo")

        sistema_uuid = UUID(sistema_id) if sistema_id else None
        caso_uso = ConsultarHistorialInferencia()
        contexto = getattr(request, "_actividad_context", {})
        historial = caso_uso.ejecutar(
            sistema_experto_id=sistema_uuid, estado=estado, modo=modo,
            excluir_borradores=not puede_ver_borradores(request),
            asignacion_id=contexto.get("asignacion_id"), estudiante_id=contexto.get("estudiante_id"),
        )
        if not contexto and puede_ver_borradores(request) and not request.user.is_superuser:
            from apps.sistemas_expertos.models import SistemaExpertoModel
            from django.db.models import Q
            ids = set(SistemaExpertoModel.objects.filter(Q(created_by=request.user) | Q(created_by__isnull=True)).values_list("id", flat=True))
            historial = [e for e in historial if e.sistema_experto_id in ids]
        datos = HistorialInferenciaSalidaSerializer(historial, many=True, context={"es_historial": True}).data
        return respuesta_exitosa(datos=datos, mensaje="Historial de inferencia obtenido.")


class EjecucionInferenciaDetailAPIView(APIView):
    """Consulta el estado general de una ejecución de inferencia."""

    @extend_schema(
        summary="Consultar ejecución de inferencia",
        responses={
            200: EjecucionInferenciaSalidaSerializer,
            404: OpenApiResponse(description="No encontrada"),
        },
        tags=["Inferencia"],
    )
    def get(self, request, id: UUID):
        caso_uso = ConsultarEjecucion()
        ejecucion = caso_uso.ejecutar(id_ejecucion=id)
        datos = EjecucionInferenciaSalidaSerializer(ejecucion).data
        return respuesta_exitosa(
            datos=datos, mensaje="Ejecución de inferencia obtenida correctamente."
        )


class DetalleInferenciaListAPIView(APIView):
    """Consulta la traza detallada de reglas de una ejecución de inferencia (Sprint 1)."""

    @extend_schema(
        summary="Consultar traza de reglas evaluadas",
        responses={200: DetalleInferenciaSalidaSerializer(many=True)},
        tags=["Inferencia"],
    )
    def get(self, request, id: UUID):
        caso_uso = ConsultarTrazaInferencia()
        detalles = caso_uso.ejecutar(id_ejecucion=id)
        datos = DetalleInferenciaSalidaSerializer(detalles, many=True).data
        return respuesta_exitosa(
            datos=datos, mensaje="Traza de inferencia obtenida correctamente."
        )


class PasoInferenciaListAPIView(APIView):
    """Lista todos los pasos ejecutados en una inferencia (HU-09)."""

    @extend_schema(
        summary="Listar pasos de la inferencia",
        responses={200: PasoInferenciaSalidaSerializer(many=True)},
        tags=["Inferencia"],
    )
    def get(self, request, id: UUID):
        from apps.inferencia.repositories import DjangoPasoInferenciaRepositorio
        repo = DjangoPasoInferenciaRepositorio()
        pasos = repo.listar_por_ejecucion(id)
        datos = PasoInferenciaSalidaSerializer(pasos, many=True).data
        return respuesta_exitosa(datos=datos, mensaje="Pasos obtenidos correctamente.")


class InferenciaHechosInferidosListAPIView(APIView):
    """Consulta los hechos generados y derivados (HU-12)."""

    @extend_schema(
        summary="Consultar hechos inferidos",
        parameters=[
            OpenApiParameter("procedencia", type=str, description="Filtrar por INICIAL o DERIVADO"),
        ],
        responses={200: HechoInferidoSalidaSerializer(many=True)},
        tags=["Inferencia"],
    )
    def get(self, request, id: UUID):
        procedencia = request.query_params.get("procedencia")
        caso_uso = ConsultarHechosInferidos()
        hechos = caso_uso.ejecutar(id_ejecucion=id, procedencia=procedencia)
        datos = HechoInferidoSalidaSerializer(hechos, many=True).data
        return respuesta_exitosa(
            datos=datos, mensaje="Hechos inferidos obtenidos correctamente."
        )


class InferenciaConflictosListAPIView(APIView):
    """Consulta los conjuntos de conflicto y reglas candidatas (HU-13)."""

    @extend_schema(
        summary="Consultar conflictos de inferencia",
        responses={200: ConflictoInferenciaSalidaSerializer(many=True)},
        tags=["Inferencia"],
    )
    def get(self, request, id: UUID):
        caso_uso = ConsultarConflictosEjecucion()
        conflictos = caso_uso.ejecutar(id_ejecucion=id)
        datos = ConflictoInferenciaSalidaSerializer(conflictos, many=True).data
        return respuesta_exitosa(
            datos=datos, mensaje="Conflictos de inferencia obtenidos correctamente."
        )


class InferenciaExplicacionDetailAPIView(APIView):
    """Consulta la explicación y árbol causal determinista de la conclusión (HU-17)."""

    @extend_schema(
        summary="Explicar conclusión de inferencia",
        responses={200: ExplicacionConclusionSalidaSerializer},
        tags=["Inferencia"],
    )
    def get(self, request, id: UUID):
        caso_uso = ConsultarExplicacionConclusion()
        explicacion = caso_uso.ejecutar(id_ejecucion=id)
        datos = ExplicacionConclusionSalidaSerializer(explicacion).data
        return respuesta_exitosa(
            datos=datos, mensaje="Explicación determinista de la conclusión obtenida."
        )
