"""
Vistas de API REST para el mdulo de Base de Conocimiento.
Controladores limpios que delegan en los casos de uso.
"""
from uuid import UUID
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from compartido.respuestas.respuesta_api import respuesta_exitosa, respuesta_creada
from apps.base_conocimiento.serializers import (
    BaseConocimientoSalidaSerializer,
    HechoEntradaSerializer,
    HechoParcialEntradaSerializer,
    HechoSalidaSerializer,
    VariableEntradaSerializer,
    VariableParcialEntradaSerializer,
    VariableSalidaSerializer,
    ReglaEntradaSerializer,
    ReglaParcialEntradaSerializer,
    ReglaSalidaSerializer,
    CondicionEntradaSerializer,
    CondicionSalidaSerializer,
    ConclusionEntradaSerializer,
    ConclusionSalidaSerializer,
)
from apps.base_conocimiento.services import (
    ObtenerBaseConocimiento,
    CrearHecho,
    ActualizarHecho,
    ObtenerHecho,
    ListarHechos,
    EliminarHecho,
    CrearVariable,
    ActualizarVariable,
    ObtenerVariable,
    ListarVariables,
    EliminarVariable,
    CrearRegla,
    ActualizarRegla,
    ObtenerRegla,
    ListarReglas,
    EliminarRegla,
    AgregarCondicionARegla,
    ActualizarCondicion,
    EliminarCondicion,
    AgregarConclusionARegla,
    ActualizarConclusion,
    EliminarConclusion,
)


# =====================================================================
# VISTAS: BASE DE CONOCIMIENTO
# =====================================================================

class BaseConocimientoPorSistemaAPIView(APIView):
    """Consulta la base de conocimiento de un sistema experto específico."""

    @extend_schema(
        summary="Obtener base de conocimiento de un sistema experto",
        description="Retorna la información general de la base de conocimiento asociada al sistema experto.",
        responses={200: BaseConocimientoSalidaSerializer, 404: OpenApiResponse(description="No encontrada")},
        tags=["Base de Conocimiento"],
    )
    def get(self, request, id: UUID):
        caso_uso = ObtenerBaseConocimiento()
        bc = caso_uso.ejecutar_por_sistema(id_sistema=id)
        datos = BaseConocimientoSalidaSerializer(bc).data
        return respuesta_exitosa(datos=datos, mensaje="Base de conocimiento obtenida correctamente.")


# =====================================================================
# VISTAS: HECHOS
# =====================================================================

class HechoListCreateAPIView(APIView):
    """Listar o crear hechos en una base de conocimiento."""

    @extend_schema(
        summary="Listar hechos de una base de conocimiento",
        responses={200: HechoSalidaSerializer(many=True)},
        tags=["Hechos"],
    )
    def get(self, request, id: UUID):
        caso_uso = ListarHechos()
        hechos = caso_uso.ejecutar(base_conocimiento_id=id)
        datos = HechoSalidaSerializer(hechos, many=True).data
        return respuesta_exitosa(datos=datos, mensaje="Hechos listados correctamente.")

    @extend_schema(
        summary="Crear hecho",
        request=HechoEntradaSerializer,
        responses={201: HechoSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Hechos"],
    )
    def post(self, request, id: UUID):
        serializer = HechoEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = CrearHecho()
        hecho = caso_uso.ejecutar(
            base_conocimiento_id=id,
            nombre=serializer.validated_data["nombre"],
            valor=serializer.validated_data.get("valor"),
            tipo_dato=serializer.validated_data.get("tipo_dato"),
            opciones=serializer.validated_data.get("opciones"),
            pregunta=serializer.validated_data.get("pregunta"),
            es_inicial=serializer.validated_data.get("es_inicial", True),
        )
        datos = HechoSalidaSerializer(hecho).data
        return respuesta_creada(datos=datos, mensaje="Hecho creado correctamente.")


class HechoDetailAPIView(APIView):
    """Consultar, actualizar o eliminar un hecho por su ID."""

    @extend_schema(
        summary="Obtener hecho",
        responses={200: HechoSalidaSerializer, 404: OpenApiResponse(description="No encontrado")},
        tags=["Hechos"],
    )
    def get(self, request, id: UUID):
        caso_uso = ObtenerHecho()
        hecho = caso_uso.ejecutar(id_hecho=id)
        datos = HechoSalidaSerializer(hecho).data
        return respuesta_exitosa(datos=datos, mensaje="Hecho obtenido correctamente.")

    @extend_schema(
        summary="Actualizar hecho completamente",
        request=HechoEntradaSerializer,
        responses={200: HechoSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Hechos"],
    )
    def put(self, request, id: UUID):
        serializer = HechoEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = ActualizarHecho()
        hecho = caso_uso.ejecutar(
            id_hecho=id,
            **serializer.validated_data,
        )
        datos = HechoSalidaSerializer(hecho).data
        return respuesta_exitosa(datos=datos, mensaje="Hecho actualizado correctamente.")

    @extend_schema(
        summary="Actualizar hecho parcialmente",
        request=HechoParcialEntradaSerializer,
        responses={200: HechoSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Hechos"],
    )
    def patch(self, request, id: UUID):
        serializer = HechoParcialEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = ActualizarHecho()
        hecho = caso_uso.ejecutar(
            id_hecho=id,
            **serializer.validated_data,
        )
        datos = HechoSalidaSerializer(hecho).data
        return respuesta_exitosa(datos=datos, mensaje="Hecho actualizado parcialmente.")

    @extend_schema(
        summary="Eliminar hecho",
        responses={
            204: OpenApiResponse(description="Eliminado exitosamente"),
            404: OpenApiResponse(description="No encontrado"),
        },
        tags=["Hechos"],
    )
    def delete(self, request, id: UUID):
        caso_uso = EliminarHecho()
        caso_uso.ejecutar(id_hecho=id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# =====================================================================
# VISTAS: VARIABLES
# =====================================================================

class VariableListCreateAPIView(APIView):
    """Listar o crear variables en una base de conocimiento."""

    @extend_schema(
        summary="Listar variables de una base de conocimiento",
        responses={200: VariableSalidaSerializer(many=True)},
        tags=["Variables"],
    )
    def get(self, request, id: UUID):
        caso_uso = ListarVariables()
        variables = caso_uso.ejecutar(base_conocimiento_id=id)
        datos = VariableSalidaSerializer(variables, many=True).data
        return respuesta_exitosa(datos=datos, mensaje="Variables listadas correctamente.")

    @extend_schema(
        summary="Crear variable",
        request=VariableEntradaSerializer,
        responses={201: VariableSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Variables"],
    )
    def post(self, request, id: UUID):
        serializer = VariableEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = CrearVariable()
        variable = caso_uso.ejecutar(
            base_conocimiento_id=id,
            nombre=serializer.validated_data["nombre"],
            tipo_dato=serializer.validated_data.get("tipo_dato"),
            valor_defecto=serializer.validated_data.get("valor_defecto"),
            pregunta=serializer.validated_data.get("pregunta"),
            es_inicial=serializer.validated_data.get("es_inicial", False),
            descripcion=serializer.validated_data.get("descripcion"),
        )
        datos = VariableSalidaSerializer(variable).data
        return respuesta_creada(datos=datos, mensaje="Variable creada correctamente.")


class VariableDetailAPIView(APIView):
    """Consultar, actualizar o eliminar una variable por su ID."""

    @extend_schema(
        summary="Obtener variable",
        responses={200: VariableSalidaSerializer, 404: OpenApiResponse(description="No encontrada")},
        tags=["Variables"],
    )
    def get(self, request, id: UUID):
        caso_uso = ObtenerVariable()
        variable = caso_uso.ejecutar(id_variable=id)
        datos = VariableSalidaSerializer(variable).data
        return respuesta_exitosa(datos=datos, mensaje="Variable obtenida correctamente.")

    @extend_schema(
        summary="Actualizar variable completamente",
        request=VariableEntradaSerializer,
        responses={200: VariableSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Variables"],
    )
    def put(self, request, id: UUID):
        serializer = VariableEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = ActualizarVariable()
        variable = caso_uso.ejecutar(
            id_variable=id,
            **serializer.validated_data,
        )
        datos = VariableSalidaSerializer(variable).data
        return respuesta_exitosa(datos=datos, mensaje="Variable actualizada correctamente.")

    @extend_schema(
        summary="Actualizar variable parcialmente",
        request=VariableParcialEntradaSerializer,
        responses={200: VariableSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Variables"],
    )
    def patch(self, request, id: UUID):
        serializer = VariableParcialEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = ActualizarVariable()
        variable = caso_uso.ejecutar(
            id_variable=id,
            **serializer.validated_data,
        )
        datos = VariableSalidaSerializer(variable).data
        return respuesta_exitosa(datos=datos, mensaje="Variable actualizada parcialmente.")

    @extend_schema(
        summary="Eliminar variable",
        responses={
            204: OpenApiResponse(description="Eliminada exitosamente"),
            404: OpenApiResponse(description="No encontrada"),
        },
        tags=["Variables"],
    )
    def delete(self, request, id: UUID):
        caso_uso = EliminarVariable()
        caso_uso.ejecutar(id_variable=id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# =====================================================================
# VISTAS: REGLAS
# =====================================================================

class ReglaListCreateAPIView(APIView):
    """Listar o crear reglas en una base de conocimiento."""

    @extend_schema(
        summary="Listar reglas de una base de conocimiento",
        responses={200: ReglaSalidaSerializer(many=True)},
        tags=["Reglas"],
    )
    def get(self, request, id: UUID):
        caso_uso = ListarReglas()
        reglas = caso_uso.ejecutar(base_conocimiento_id=id)
        datos = ReglaSalidaSerializer(reglas, many=True).data
        return respuesta_exitosa(datos=datos, mensaje="Reglas listadas correctamente.")

    @extend_schema(
        summary="Crear regla",
        request=ReglaEntradaSerializer,
        responses={201: ReglaSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Reglas"],
    )
    def post(self, request, id: UUID):
        serializer = ReglaEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = CrearRegla()
        regla = caso_uso.ejecutar(
            base_conocimiento_id=id,
            nombre=serializer.validated_data["nombre"],
            descripcion=serializer.validated_data.get("descripcion"),
            prioridad=serializer.validated_data.get("prioridad", 0),
            factor_certeza=serializer.validated_data.get("factor_certeza"),
            activa=serializer.validated_data.get("activa", True),
        )
        datos = ReglaSalidaSerializer(regla).data
        return respuesta_creada(datos=datos, mensaje="Regla creada correctamente.")


class ReglaDetailAPIView(APIView):
    """Consultar, actualizar o eliminar una regla por su ID."""

    @extend_schema(
        summary="Obtener regla con condiciones y conclusiones",
        responses={200: ReglaSalidaSerializer, 404: OpenApiResponse(description="No encontrada")},
        tags=["Reglas"],
    )
    def get(self, request, id: UUID):
        caso_uso = ObtenerRegla()
        regla = caso_uso.ejecutar(id_regla=id)
        datos = ReglaSalidaSerializer(regla).data
        return respuesta_exitosa(datos=datos, mensaje="Regla obtenida correctamente.")

    @extend_schema(
        summary="Actualizar regla completamente",
        request=ReglaEntradaSerializer,
        responses={200: ReglaSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Reglas"],
    )
    def put(self, request, id: UUID):
        serializer = ReglaEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = ActualizarRegla()
        regla = caso_uso.ejecutar(
            id_regla=id,
            nombre=serializer.validated_data["nombre"],
            descripcion=serializer.validated_data.get("descripcion"),
            prioridad=serializer.validated_data.get("prioridad"),
            factor_certeza=serializer.validated_data.get("factor_certeza"),
            activa=serializer.validated_data.get("activa"),
        )
        datos = ReglaSalidaSerializer(regla).data
        return respuesta_exitosa(datos=datos, mensaje="Regla actualizada correctamente.")

    @extend_schema(
        summary="Actualizar regla parcialmente",
        request=ReglaParcialEntradaSerializer,
        responses={200: ReglaSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Reglas"],
    )
    def patch(self, request, id: UUID):
        serializer = ReglaParcialEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = ActualizarRegla()
        regla = caso_uso.ejecutar(
            id_regla=id,
            nombre=serializer.validated_data.get("nombre"),
            descripcion=serializer.validated_data.get("descripcion"),
            prioridad=serializer.validated_data.get("prioridad"),
            factor_certeza=serializer.validated_data.get("factor_certeza"),
            activa=serializer.validated_data.get("activa"),
        )
        datos = ReglaSalidaSerializer(regla).data
        return respuesta_exitosa(datos=datos, mensaje="Regla actualizada parcialmente.")

    @extend_schema(
        summary="Eliminar regla",
        responses={
            204: OpenApiResponse(description="Eliminada exitosamente"),
            404: OpenApiResponse(description="No encontrada"),
        },
        tags=["Reglas"],
    )
    def delete(self, request, id: UUID):
        caso_uso = EliminarRegla()
        caso_uso.ejecutar(id_regla=id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# =====================================================================
# VISTAS: CONDICIONES
# =====================================================================

class CondicionCreateAPIView(APIView):
    """Agregar una condición a una regla existente."""

    @extend_schema(
        summary="Agregar condición a regla",
        request=CondicionEntradaSerializer,
        responses={201: CondicionSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Condiciones"],
    )
    def post(self, request, id: UUID):
        serializer = CondicionEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = AgregarCondicionARegla()
        condicion = caso_uso.ejecutar(
            regla_id=id,
            operador=serializer.validated_data["operador"],
            valor_esperado=serializer.validated_data["valor_esperado"],
            variable_id=serializer.validated_data.get("variable_id"),
            hecho_id=serializer.validated_data.get("hecho_id"),
            orden=serializer.validated_data.get("orden", 1),
        )
        datos = CondicionSalidaSerializer(condicion).data
        return respuesta_creada(datos=datos, mensaje="Condición agregada correctamente.")


class CondicionDetailAPIView(APIView):
    """Actualizar o eliminar una condición por su ID."""

    @extend_schema(
        summary="Actualizar condición",
        request=CondicionEntradaSerializer,
        responses={200: CondicionSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Condiciones"],
    )
    def put(self, request, id: UUID):
        serializer = CondicionEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = ActualizarCondicion()
        condicion = caso_uso.ejecutar(
            id_condicion=id,
            operador=serializer.validated_data.get("operador"),
            valor_esperado=serializer.validated_data.get("valor_esperado"),
            variable_id=serializer.validated_data.get("variable_id"),
            hecho_id=serializer.validated_data.get("hecho_id"),
            orden=serializer.validated_data.get("orden"),
        )
        datos = CondicionSalidaSerializer(condicion).data
        return respuesta_exitosa(datos=datos, mensaje="Condición actualizada correctamente.")

    @extend_schema(
        summary="Eliminar condición",
        responses={
            204: OpenApiResponse(description="Eliminada exitosamente"),
            404: OpenApiResponse(description="No encontrada"),
        },
        tags=["Condiciones"],
    )
    def delete(self, request, id: UUID):
        caso_uso = EliminarCondicion()
        caso_uso.ejecutar(id_condicion=id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# =====================================================================
# VISTAS: CONCLUSIONES
# =====================================================================

class ConclusionCreateAPIView(APIView):
    """Agregar una conclusión a una regla existente."""

    @extend_schema(
        summary="Agregar conclusión a regla",
        request=ConclusionEntradaSerializer,
        responses={201: ConclusionSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Conclusiones"],
    )
    def post(self, request, id: UUID):
        serializer = ConclusionEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = AgregarConclusionARegla()
        conclusion = caso_uso.ejecutar(
            regla_id=id,
            valor_resultante=serializer.validated_data["valor_resultante"],
            hecho_resultante_id=serializer.validated_data.get("hecho_resultante_id"),
            variable_resultante_id=serializer.validated_data.get("variable_resultante_id"),
        )
        datos = ConclusionSalidaSerializer(conclusion).data
        return respuesta_creada(datos=datos, mensaje="Conclusión agregada correctamente.")


class ConclusionDetailAPIView(APIView):
    """Actualizar o eliminar una conclusión por su ID."""

    @extend_schema(
        summary="Actualizar conclusión",
        request=ConclusionEntradaSerializer,
        responses={200: ConclusionSalidaSerializer, 400: OpenApiResponse(description="Datos inválidos")},
        tags=["Conclusiones"],
    )
    def put(self, request, id: UUID):
        serializer = ConclusionEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = ActualizarConclusion()
        conclusion = caso_uso.ejecutar(
            id_conclusion=id,
            valor_resultante=serializer.validated_data.get("valor_resultante"),
            hecho_resultante_id=serializer.validated_data.get("hecho_resultante_id"),
            variable_resultante_id=serializer.validated_data.get("variable_resultante_id"),
        )
        datos = ConclusionSalidaSerializer(conclusion).data
        return respuesta_exitosa(datos=datos, mensaje="Conclusión actualizada correctamente.")

    @extend_schema(
        summary="Eliminar conclusión",
        responses={
            204: OpenApiResponse(description="Eliminada exitosamente"),
            404: OpenApiResponse(description="No encontrada"),
        },
        tags=["Conclusiones"],
    )
    def delete(self, request, id: UUID):
        caso_uso = EliminarConclusion()
        caso_uso.ejecutar(id_conclusion=id)
        return Response(status=status.HTTP_204_NO_CONTENT)
