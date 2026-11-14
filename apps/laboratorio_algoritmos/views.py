"""
Vistas de API REST para el Laboratorio de Algoritmos de Inferencia.
"""
import hashlib
from typing import Any, Dict
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from compartido.respuestas.respuesta_api import respuesta_creada, respuesta_error, respuesta_exitosa
from .exceptions import RuntimeLaboratorioError, SintaxisError, TipoError
from .lenguaje.compiler import Compiler
from .lenguaje.lexer import Lexer
from .lenguaje.parser import Parser
from .lenguaje.type_checker import TypeChecker
from .models import (
    CorridaLaboratorioModel,
    PasoEjecucionModel,
    ProgramaAlgoritmoModel,
    RevisionProgramaModel,
)
from .plantillas import PLANTILLAS_ALGORITMOS
from .runtime.state import VMState
from .runtime.values import (
    BaseHechosValue,
    ColaValue,
    HechoValor,
    ListaValue,
    PilaValue,
    ReglaRef,
    VariableRef,
)
from .runtime.vm import EvaluadorReglasSnapshot, VirtualMachine
from .adapters.knowledge import extraer_snapshot_base_conocimiento, instanciar_entorno_runtime
from .serializers import (
    AvanzarEjecucionEntradaSerializer,
    CompilarCodigoEntradaSerializer,
    CompilarCodigoSalidaSerializer,
    CorridaLaboratorioSalidaSerializer,
    IniciarEjecucionEntradaSerializer,
    ProgramaAlgoritmoSerializer,
    ResponderPreguntaEntradaSerializer,
    RevisionProgramaSerializer,
)


def _compilar_codigo(codigo: str, entrada_principal: str = "main"):
    """Auxiliar que ejecuta el pipeline completo del compilador."""
    lexer = Lexer(codigo)
    tokens = lexer.tokenizar()
    parser = Parser(tokens)
    ast = parser.parsear()
    tc = TypeChecker(ast)
    tc.verificar()
    entrada = entrada_principal
    nombres_funcs = [f.nombre for f in ast.funciones]
    if entrada not in nombres_funcs:
        if "FWC" in nombres_funcs:
            entrada = "FWC"
        elif "main" in nombres_funcs:
            entrada = "main"
        elif "BWC" in nombres_funcs:
            entrada = "BWC"
        else:
            candidatos = [n for n in nombres_funcs if not n.endswith("Pasada")]
            entrada = candidatos[-1] if candidatos else (nombres_funcs[-1] if nombres_funcs else entrada)
    compiler = Compiler(ast)
    prog = compiler.compilar(entrada_principal=entrada)
    return prog, ast


def _construir_evaluador(snapshot_bc: Dict[str, Any]) -> EvaluadorReglasSnapshot:
    """Construye un EvaluadorReglasSnapshot a partir del diccionario de snapshot."""
    reglas_datos = {}
    for r in snapshot_bc.get("reglas", []):
        rid = r.get("id")
        condiciones = []
        for p in r.get("premisas", []):
            condiciones.append({
                "variable_nombre": p.get("variable", ""),
                "operador": p.get("operador", "="),
                "valor_esperado": p.get("valor"),
            })
        conclusiones = r.get("conclusiones", [])
        concl_dict = {}
        if conclusiones:
            primera_concl = conclusiones[0]
            concl_dict = {
                "variable_nombre": primera_concl.get("variable", ""),
                "valor_resultante": primera_concl.get("valor", "true"),
                "tipo_dato": "TEXTO",
            }
        reglas_datos[rid] = {
            "condiciones": condiciones,
            "conclusion": concl_dict,
        }
    return EvaluadorReglasSnapshot(reglas_datos)


class CompilarCodigoAPIView(APIView):
    """Valida sintaxis y tipos de un código fuente pedagógico sin ejecutarlo."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = CompilarCodigoEntradaSerializer(data=request.data)
        if not ser.is_valid():
            return respuesta_error(errores=ser.errors)

        codigo = ser.validated_data["codigo_fuente"]
        try:
            prog, ast = _compilar_codigo(codigo)
            return respuesta_exitosa(
                datos={
                    "valido": True,
                    "errores": [],
                    "warnings": [],
                    "funciones": list(prog.funciones.keys()),
                },
                mensaje="El código compiló correctamente sin errores sintácticos ni de tipos."
            )
        except (SintaxisError, TipoError) as e:
            fase = "sintaxis" if isinstance(e, SintaxisError) else "tipos"
            return respuesta_exitosa(
                datos={
                    "valido": False,
                    "errores": [{
                        "mensaje": e.mensaje,
                        "linea": e.span.line if e.span else 1,
                        "columna": e.span.column if e.span else 1,
                        "offset": e.span.offset if e.span else 0,
                        "fase": fase,
                    }],
                    "warnings": [],
                },
                mensaje="Se detectaron errores en el código."
            )
        except Exception as ex:
            return respuesta_exitosa(
                datos={
                    "valido": False,
                    "errores": [{
                        "mensaje": str(ex),
                        "linea": 1,
                        "columna": 1,
                        "offset": 0,
                        "fase": "desconocida",
                    }],
                    "warnings": [],
                },
                mensaje=f"Error durante la compilación: {str(ex)}"
            )


class IniciarEjecucionAPIView(APIView):
    """Inicializa una nueva corrida de simulación interactiva con snapshot de la BC."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = IniciarEjecucionEntradaSerializer(data=request.data)
        if not ser.is_valid():
            return respuesta_error(errores=ser.errors)

        data = ser.validated_data
        sistema_experto_id = data.get("sistema_experto_id")
        programa_id = data.get("programa_id")
        codigo_fuente = data.get("codigo_fuente") or ""
        orden_reglas_ids = data.get("orden_reglas_ids") or []
        hechos_override = data.get("hechos_iniciales_override") or {}
        params_iniciales = data.get("parametros_iniciales") or {}

        # Si viene programa_id, obtener código si no se envió explícito
        programa_obj = None
        if programa_id:
            programa_obj = get_object_or_404(ProgramaAlgoritmoModel, id=programa_id)
            if not codigo_fuente.strip():
                codigo_fuente = programa_obj.codigo_fuente

        if not codigo_fuente.strip():
            return respuesta_error(mensaje="Debe proporcionar el código fuente para iniciar la corrida.")

        # Compilar código
        try:
            prog, ast_arbol = _compilar_codigo(codigo_fuente)
        except (SintaxisError, TipoError) as err:
            return respuesta_error(
                mensaje=f"Error al compilar código: {err.mensaje}",
                errores=[{
                    "mensaje": err.mensaje,
                    "linea": err.span.line if err.span else 1,
                    "columna": err.span.column if err.span else 1,
                }]
            )

        # Snapshot de Base de Conocimiento
        snapshot_bc = {}
        if sistema_experto_id:
            try:
                snapshot_bc = extraer_snapshot_base_conocimiento(
                    sistema_experto_id=sistema_experto_id,
                    orden_reglas_ids=orden_reglas_ids,
                    hechos_override=hechos_override,
                )
            except Exception as e:
                return respuesta_error(mensaje=f"No se pudo cargar la Base de Conocimiento: {str(e)}")

        evaluador = _construir_evaluador(snapshot_bc)
        reglas_refs, bh = instanciar_entorno_runtime(snapshot_bc)

        # Preparar bindings de parámetros para la función de entrada principal (FWC, main, etc.)
        entrada_nom = prog.entrada_principal
        func_main = prog.funciones.get(entrada_nom)
        if not func_main:
            func_main = prog.funciones.get("FWC") or prog.funciones.get("main") or (list(prog.funciones.values())[-1] if prog.funciones else None)
            if func_main:
                entrada_nom = func_main.nombre

        if not func_main:
            return respuesta_error(mensaje="El programa no define una función ejecutable de entrada (ej: FWC o main).")

        ast_func = next((f for f in ast_arbol.funciones if f.nombre == entrada_nom), None)
        param_tipos = {p.nombre: p.tipo for p in ast_func.parametros} if ast_func else {}

        bindings: Dict[str, Any] = {}
        for param in func_main.parametros:
            tipo_param = param_tipos.get(param)
            es_arr = tipo_param.es_arreglo if tipo_param else False

            if param == "R":
                bindings["R"] = list(reglas_refs) if es_arr else ListaValue(reglas_refs)
            elif param == "Q":
                bindings["Q"] = ColaValue(list(reglas_refs))
            elif param == "BH":
                bindings["BH"] = bh
            elif param == "HN":
                # Pila HN de variables nativas
                vars_nativas = [
                    VariableRef(id=v["id"], nombre=v["nombre"], tipo_dato=v.get("tipo_dato", "TEXTO"), es_nativa=True)
                    for v in snapshot_bc.get("variables", [])
                    if v.get("es_inicial", False) or v.get("pregunta")
                ]
                bindings["HN"] = PilaValue(vars_nativas)
            elif param in params_iniciales:
                val = params_iniciales[param]
                if isinstance(val, str) and param.lower() == "meta":
                    bindings[param] = VariableRef(id=val, nombre=val)
                else:
                    bindings[param] = val
            elif param.lower() == "meta":
                primer_var = snapshot_bc.get("variables", [{}])[0].get("nombre", "Meta")
                bindings[param] = VariableRef(id=primer_var, nombre=primer_var)
            elif param.lower() == "metas":
                vars_metas = [
                    VariableRef(id=v["id"], nombre=v["nombre"], tipo_dato=v.get("tipo_dato", "TEXTO"))
                    for v in snapshot_bc.get("variables", [])
                    if not v.get("es_inicial", False)
                ]
                bindings[param] = ListaValue(vars_metas)
            else:
                bindings[param] = None

        # Instanciar VM y ejecutar primer paso
        vm = VirtualMachine(prog, evaluador_reglas=evaluador)
        try:
            vm.inicializar(bindings, entrada_principal=entrada_nom)
            # Avanzar hasta la primera línea visible
            vm.ejecutar_hasta_pausa(max_pasos_visibles=1)
        except Exception as e:
            return respuesta_error(mensaje=f"Error en tiempo de ejecución: {str(e)}")

        # Crear registro en BD
        corrida = CorridaLaboratorioModel.objects.create(
            usuario=request.user,
            programa=programa_obj,
            sistema_experto_id=sistema_experto_id if sistema_experto_id else None,
            codigo_fuente=codigo_fuente,
            estado=vm.estado.estado,
            estado_vm_json=vm.estado.to_dict(),
            snapshot_bc_json=snapshot_bc,
            total_pasos=vm.estado.pasos_visibles,
        )

        # Registrar primer paso si existe
        if vm.estado.eventos:
            prim_ev = vm.estado.eventos[-1]
            PasoEjecucionModel.objects.create(
                corrida=corrida,
                numero_paso=1,
                pc=prim_ev.pc,
                linea=prim_ev.linea,
                columna=prim_ev.columna,
                evento_json=prim_ev.to_dict(),
                delta_json={"estado": vm.estado.estado},
            )

        return respuesta_creada(
            datos=CorridaLaboratorioSalidaSerializer(corrida).data,
            mensaje="Corrida de simulación iniciada con éxito."
        )


class AvanzarEjecucionAPIView(APIView):
    """Avanza la ejecución de una corrida existente (paso a paso o hasta el final)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, corrida_id):
        corrida = get_object_or_404(CorridaLaboratorioModel, id=corrida_id)
        if corrida.usuario_id != request.user.id and not request.user.is_staff:
            return respuesta_error(mensaje="No tiene permisos para controlar esta corrida.", codigo_estado=status.HTTP_403_FORBIDDEN)

        if corrida.estado in ("FINALIZADA", "ERROR", "CANCELADA"):
            return respuesta_error(mensaje=f"La corrida ya está en estado {corrida.estado} y no puede avanzar.")

        if corrida.estado == "ESPERANDO_ENTRADA":
            return respuesta_error(mensaje="La máquina virtual está esperando una respuesta a una consulta. Responda antes de avanzar.")

        ser = AvanzarEjecucionEntradaSerializer(data=request.data)
        if not ser.is_valid():
            return respuesta_error(errores=ser.errors)

        modo = ser.validated_data["modo"]
        max_pasos = ser.validated_data["max_pasos"]

        codigo = corrida.codigo_fuente or (corrida.programa.codigo_fuente if corrida.programa else "")
        if not codigo:
            codigo = request.data.get("codigo_fuente", "")

        try:
            prog, _ = _compilar_codigo(codigo)
        except Exception as e:
            return respuesta_error(mensaje=f"Error al recompilar el programa para reanudar: {str(e)}")

        evaluador = _construir_evaluador(corrida.snapshot_bc_json)
        estado_vm = VMState.from_dict(corrida.estado_vm_json)
        vm = VirtualMachine(prog, estado=estado_vm, evaluador_reglas=evaluador)

        pasos_a_ejecutar = 1 if modo == "LINE_STEP" else max_pasos
        try:
            vm.ejecutar_hasta_pausa(max_pasos_visibles=pasos_a_ejecutar)
        except Exception as ex:
            corrida.estado = "ERROR"
            corrida.mensaje_salida = str(ex)
            corrida.save()
            return respuesta_error(mensaje=f"Error durante la ejecución: {str(ex)}")

        corrida.estado = vm.estado.estado
        corrida.estado_vm_json = vm.estado.to_dict()
        corrida.total_pasos = vm.estado.pasos_visibles
        if vm.estado.error_detalle:
            corrida.mensaje_salida = vm.estado.error_detalle.get("mensaje", "")
        corrida.save()

        # Guardar paso en BD
        if vm.estado.eventos:
            ev = vm.estado.eventos[-1]
            PasoEjecucionModel.objects.create(
                corrida=corrida,
                numero_paso=corrida.total_pasos,
                pc=ev.pc,
                linea=ev.linea,
                columna=ev.columna,
                evento_json=ev.to_dict(),
                delta_json={"estado": vm.estado.estado},
            )

        return respuesta_exitosa(
            datos=CorridaLaboratorioSalidaSerializer(corrida).data,
            mensaje="Paso ejecutado correctamente."
        )


class ResponderPreguntaAPIView(APIView):
    """Entrega la respuesta ingresada por el usuario para una consulta pendiente."""
    permission_classes = [IsAuthenticated]

    def post(self, request, corrida_id):
        corrida = get_object_or_404(CorridaLaboratorioModel, id=corrida_id)
        if corrida.usuario_id != request.user.id and not request.user.is_staff:
            return respuesta_error(mensaje="No tiene permisos para modificar esta corrida.", codigo_estado=status.HTTP_403_FORBIDDEN)

        if corrida.estado != "ESPERANDO_ENTRADA":
            return respuesta_error(mensaje="La máquina virtual no está esperando ninguna respuesta en este momento.")

        ser = ResponderPreguntaEntradaSerializer(data=request.data)
        if not ser.is_valid():
            return respuesta_error(errores=ser.errors)

        valor = ser.validated_data["valor"]
        cancelada = ser.validated_data["cancelada"]

        estado_vm = VMState.from_dict(corrida.estado_vm_json)
        if not estado_vm.pregunta_pendiente:
            return respuesta_error(mensaje="No se encontró el objeto de consulta pendiente en el estado.")

        id_preg = estado_vm.pregunta_pendiente.id_pregunta

        codigo = corrida.codigo_fuente or (corrida.programa.codigo_fuente if corrida.programa else "")
        if not codigo:
            codigo = request.data.get("codigo_fuente", "")
        try:
            prog, _ = _compilar_codigo(codigo)
        except Exception as e:
            return respuesta_error(mensaje=f"Error al recompilar el programa: {str(e)}")

        evaluador = _construir_evaluador(corrida.snapshot_bc_json)
        vm = VirtualMachine(prog, estado=estado_vm, evaluador_reglas=evaluador)

        try:
            vm.resolver_pregunta(id_pregunta=id_preg, valor=valor, es_cancelacion=cancelada)
            # Avanzar hasta la siguiente línea visible
            vm.ejecutar_hasta_pausa(max_pasos_visibles=1)
        except Exception as ex:
            return respuesta_error(mensaje=f"Error al reanudar la simulación: {str(ex)}")

        corrida.estado = vm.estado.estado
        corrida.estado_vm_json = vm.estado.to_dict()
        corrida.total_pasos = vm.estado.pasos_visibles
        corrida.save()

        return respuesta_exitosa(
            datos=CorridaLaboratorioSalidaSerializer(corrida).data,
            mensaje="Respuesta registrada y simulación reanudada."
        )


class PlantillasAlgoritmoAPIView(APIView):
    """Devuelve las plantillas oficiales canónicas de algoritmos de clase."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return respuesta_exitosa(
            datos=PLANTILLAS_ALGORITMOS,
            mensaje="Plantillas oficiales del laboratorio obtenidas con éxito."
        )


class ProgramasAlgoritmoViewSet(viewsets.ModelViewSet):
    """CRUD de algoritmos guardados por el usuario y gestión de revisiones inmutables."""
    serializer_class = ProgramaAlgoritmoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ProgramaAlgoritmoModel.objects.filter(owner=user)
        se_id = self.request.query_params.get("sistema_experto")
        if se_id:
            qs = qs.filter(sistema_experto_id=se_id)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return respuesta_exitosa(datos=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return respuesta_exitosa(datos=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        codigo = serializer.validated_data.get("codigo_fuente", "")
        instancia = serializer.save(owner=self.request.user, version_entero=1)
        h = hashlib.sha256(codigo.encode("utf-8")).hexdigest()
        RevisionProgramaModel.objects.create(
            programa=instancia,
            numero_revision=1,
            codigo_fuente=codigo,
            hash_fuente=h,
        )
        return respuesta_creada(datos=serializer.data, mensaje="Programa guardado con éxito.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        codigo_nuevo = serializer.validated_data.get("codigo_fuente", "")
        if codigo_nuevo and codigo_nuevo != instance.codigo_fuente:
            nueva_version = instance.version_entero + 1
            h = hashlib.sha256(codigo_nuevo.encode("utf-8")).hexdigest()
            instancia = serializer.save(version_entero=nueva_version)
            RevisionProgramaModel.objects.create(
                programa=instancia,
                numero_revision=nueva_version,
                codigo_fuente=codigo_nuevo,
                hash_fuente=h,
            )
        else:
            instancia = serializer.save()
        return respuesta_exitosa(datos=serializer.data, mensaje="Programa actualizado con éxito.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return respuesta_exitosa(mensaje="Programa eliminado con éxito.")

    @action(detail=True, methods=["get"], url_path="revisiones")
    def listar_revisiones(self, request, pk=None):
        programa = self.get_object()
        revisiones = programa.revisiones.all()
        ser = RevisionProgramaSerializer(revisiones, many=True)
        return respuesta_exitosa(datos=ser.data)
