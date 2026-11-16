import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from ..exceptions import RuntimeLaboratorioError, SourceSpan
from .instructions import Instruction, OpCode
from .values import (
    VariableRef, HechoValor, ReglaRef, ListaValue, PilaValue, ColaValue,
    BaseHechosValue, valores_son_iguales
)
from .state import VMState, StackFrame, EventoTraza, PreguntaPendiente
from ..lenguaje.compiler import CompiledProgram, CompiledFunction


class EvaluadorReglasSnapshot:
    """Evaluador de reglas en memoria basado en el snapshot de la Base de Conocimiento."""
    def __init__(self, reglas_datos: Optional[Dict[str, dict]] = None):
        # Mapea regla_id -> dict con condiciones y conclusiones
        self.reglas_datos = reglas_datos or {}

    def evaluar_disparo(self, regla_ref: ReglaRef, bh: BaseHechosValue) -> Optional[HechoValor]:
        datos = self.reglas_datos.get(regla_ref.id)
        if not datos:
            return None

        condiciones = datos.get("condiciones", [])
        # Todas las condiciones deben cumplirse (AND de clase)
        for cond in condiciones:
            var_nombre = cond.get("variable_nombre", "").strip().lower()
            operador = cond.get("operador", "=")
            val_esp = cond.get("valor_esperado")

            if var_nombre not in bh.hechos_por_var:
                return None  # Premisa no satisfecha por falta de dato

            hecho_actual = bh.hechos_por_var[var_nombre]
            val_actual = hecho_actual.valor

            if not self._comparar_valores(val_actual, operador, val_esp):
                return None

        # Si se cumplen las condiciones, construir la conclusión
        concl_datos = datos.get("conclusion")
        if not concl_datos:
            return None

        return HechoValor(
            id=str(uuid.uuid4())[:8],
            variable_id=concl_datos.get("variable_id", str(uuid.uuid4())[:8]),
            variable_nombre=concl_datos.get("variable_nombre", "conclusion"),
            valor=concl_datos.get("valor_resultante", "true"),
            tipo_dato=concl_datos.get("tipo_dato", "TEXTO")
        )

    def _comparar_valores(self, actual: Any, operador: str, esperado: Any) -> bool:
        # Conversión numérica si aplica
        try:
            act_num = float(actual)
            esp_num = float(esperado)
            if operador in ("=", "=="): return act_num == esp_num
            if operador == "!=": return act_num != esp_num
            if operador == ">": return act_num > esp_num
            if operador == ">=": return act_num >= esp_num
            if operador == "<": return act_num < esp_num
            if operador == "<=": return act_num <= esp_num
        except (ValueError, TypeError):
            pass

        # Comparación como cadenas/booleanos normalizados
        act_str = str(actual).strip().lower()
        esp_str = str(esperado).strip().lower()
        if operador in ("=", "=="): return act_str == esp_str
        if operador == "!=": return act_str != esp_str
        return False


class VirtualMachine:
    def __init__(
        self,
        programa: CompiledProgram,
        estado: Optional[VMState] = None,
        evaluador_reglas: Optional[EvaluadorReglasSnapshot] = None,
        max_instrucciones: int = 100000,
        max_frames: int = 64
    ):
        self.programa = programa
        self.estado = estado or VMState()
        self.evaluador_reglas = evaluador_reglas or EvaluadorReglasSnapshot()
        self.max_instrucciones = max_instrucciones
        self.max_frames = max_frames

    def inicializar(self, bindings: Dict[str, Any], entrada_principal: Optional[str] = None):
        nombre_func = entrada_principal or self.programa.entrada_principal
        if nombre_func not in self.programa.funciones:
            raise RuntimeLaboratorioError(f"Función de entrada '{nombre_func}' no encontrada en el programa.")

        func = self.programa.funciones[nombre_func]
        variables_iniciales = {}

        for param_nombre in func.parametros:
            if param_nombre in bindings:
                variables_iniciales[param_nombre] = bindings[param_nombre]
            else:
                variables_iniciales[param_nombre] = None

        frame_inicial = StackFrame(
            nombre_funcion=nombre_func,
            pc=0,
            variables=variables_iniciales,
            pila_operandos=[]
        )
        self.estado = VMState(frames=[frame_inicial], estado="EJECUTANDO")

    def ejecutar_hasta_pausa(self, max_pasos_visibles: int = 25, max_instrucciones_lote: int = 250) -> VMState:
        if self.estado.estado in ("FINALIZADA", "ERROR", "LIMITE_ALCANZADO", "ESPERANDO_ENTRADA"):
            return self.estado

        self.estado.estado = "EJECUTANDO"
        pasos_lote = 0
        instrucciones_lote = 0

        while self.estado.frames and self.estado.estado == "EJECUTANDO":
            # Control de cuota global
            if self.estado.instrucciones_totales >= self.max_instrucciones:
                self.estado.estado = "LIMITE_ALCANZADO"
                self.estado.error_detalle = {
                    "codigo": "LIMITE_INSTRUCCIONES",
                    "mensaje": f"Se superó el límite global de instrucciones ({self.max_instrucciones}). Posible bucle infinito."
                }
                break

            # Control de cuota de lote
            if instrucciones_lote >= max_instrucciones_lote:
                break

            frame = self.estado.frame_actual()
            func = self.programa.funciones.get(frame.nombre_funcion)
            if not func or frame.pc >= len(func.instrucciones):
                # Fin de la función
                self.estado.frames.pop()
                if not self.estado.frames:
                    self.estado.estado = "FINALIZADA"
                    break
                continue

            inst = func.instrucciones[frame.pc]
            frame.pc += 1
            self.estado.instrucciones_totales += 1
            instrucciones_lote += 1

            # Ejecutar instrucción
            hubo_paso_visible = self._ejecutar_instruccion(inst, frame)
            if hubo_paso_visible:
                pasos_lote += 1
                self.estado.pasos_visibles += 1
                if pasos_lote >= max_pasos_visibles:
                    break

        if not self.estado.frames and self.estado.estado != "ERROR":
            self.estado.estado = "FINALIZADA"

        return self.estado

    def resolver_pregunta(self, id_pregunta: str, valor: Any, es_cancelacion: bool = False):
        if self.estado.estado != "ESPERANDO_ENTRADA" or not self.estado.pregunta_pendiente:
            raise RuntimeLaboratorioError("La máquina virtual no está esperando una respuesta de consulta.")

        if self.estado.pregunta_pendiente.id_pregunta != id_pregunta:
            raise RuntimeLaboratorioError("El ID de la pregunta no coincide con la consulta pendiente.")

        var_nom = self.estado.pregunta_pendiente.variable_nombre
        var_id = self.estado.pregunta_pendiente.variable_id

        # Limpiar pregunta pendiente
        self.estado.pregunta_pendiente = None
        self.estado.estado = "EJECUTANDO"

        frame = self.estado.frame_actual()
        if es_cancelacion or valor is None:
            # Devuelve null
            frame.pila_operandos.append(None)
        else:
            hecho = HechoValor(
                id=str(uuid.uuid4())[:8],
                variable_id=var_id,
                variable_nombre=var_nom,
                valor=valor
            )
            frame.pila_operandos.append(hecho)

    def _ejecutar_instruccion(self, inst: Instruction, frame: StackFrame) -> bool:
        op = inst.op

        if op == OpCode.LINE_STEP:
            # Registra un evento de paso visible
            linea = inst.span.line if inst.span else 0
            columna = inst.span.column if inst.span else 0
            self.estado.eventos.append(EventoTraza(
                tipo="PASO",
                descripcion=f"Paso en línea {linea}",
                pc=frame.pc - 1,
                linea=linea,
                columna=columna
            ))
            return True

        if op == OpCode.CONST:
            frame.pila_operandos.append(inst.arg)
            return False

        if op == OpCode.POP:
            if frame.pila_operandos:
                frame.pila_operandos.pop()
            return False

        if op == OpCode.DUP:
            if frame.pila_operandos:
                frame.pila_operandos.append(frame.pila_operandos[-1])
            return False

        if op == OpCode.LOAD_VAR:
            nombre = inst.arg
            if nombre not in frame.variables:
                raise RuntimeLaboratorioError(f"Variable no inicializada: '{nombre}'", span=inst.span, codigo="VARIABLE_NO_INICIALIZADA")
            frame.pila_operandos.append(frame.variables[nombre])
            return False

        if op == OpCode.STORE_VAR:
            nombre = inst.arg
            val = frame.pila_operandos.pop() if frame.pila_operandos else None
            frame.variables[nombre] = val
            return False

        if op == OpCode.UPDATE_VAR:
            nombre, es_inc = inst.arg
            val = frame.variables.get(nombre, 0)
            if not isinstance(val, int):
                raise RuntimeLaboratorioError(f"Operador ++/-- requiere entero en '{nombre}'.", span=inst.span)
            frame.variables[nombre] = val + 1 if es_inc else val - 1
            return False

        if op == OpCode.BINARY_OP:
            b = frame.pila_operandos.pop()
            a = frame.pila_operandos.pop()
            res = self._aplicar_binario(a, inst.arg, b, inst.span)
            frame.pila_operandos.append(res)
            return False

        if op == OpCode.UNARY_OP:
            a = frame.pila_operandos.pop()
            if inst.arg == "!":
                frame.pila_operandos.append(not bool(a))
            elif inst.arg == "-":
                frame.pila_operandos.append(-a)
            return False

        if op == OpCode.JUMP:
            frame.pc = inst.arg
            return False

        if op == OpCode.JUMP_IF_FALSE:
            cond = frame.pila_operandos.pop()
            if not bool(cond):
                frame.pc = inst.arg
            return False

        if op == OpCode.JUMP_IF_TRUE:
            cond = frame.pila_operandos.pop()
            if bool(cond):
                frame.pc = inst.arg
            return False

        if op == OpCode.NEW_ARRAY:
            tamano = frame.pila_operandos.pop()
            if not isinstance(tamano, int) or tamano < 0:
                raise RuntimeLaboratorioError("Tamaño de arreglo inválido.", span=inst.span)
            frame.pila_operandos.append([None] * tamano)
            return False

        if op == OpCode.NEW_COLLECTION:
            col_tipo, _ = inst.arg
            if col_tipo == "Lista":
                frame.pila_operandos.append(ListaValue())
            elif col_tipo == "Pila":
                frame.pila_operandos.append(PilaValue())
            elif col_tipo == "Cola":
                frame.pila_operandos.append(ColaValue())
            return False

        if op == OpCode.LOAD_INDEX:
            idx = frame.pila_operandos.pop()
            col = frame.pila_operandos.pop()
            if isinstance(col, list):
                if idx < 0 or idx >= len(col):
                    raise RuntimeLaboratorioError(f"Índice fuera de rango: {idx} en arreglo de tamaño {len(col)}.", span=inst.span, codigo="INDICE_FUERA_RANGO")
                frame.pila_operandos.append(col[idx])
            else:
                raise RuntimeLaboratorioError("Acceso por corchetes solo soportado en arreglos.", span=inst.span)
            return False

        if op == OpCode.STORE_INDEX:
            val = frame.pila_operandos.pop()
            idx = frame.pila_operandos.pop()
            col = frame.pila_operandos.pop()
            if isinstance(col, list):
                if idx < 0 or idx >= len(col):
                    raise RuntimeLaboratorioError(f"Índice fuera de rango: {idx}.", span=inst.span, codigo="INDICE_FUERA_RANGO")
                col[idx] = val
            return False

        if op == OpCode.LOAD_MEMBER:
            obj = frame.pila_operandos.pop()
            miembro = inst.arg
            if obj is None:
                raise RuntimeLaboratorioError(f"Intento de acceder a la propiedad '{miembro}' en una referencia nula (null).", span=inst.span, codigo="ARGUMENTO_NULO")
            if isinstance(obj, (list, tuple)) and miembro == "length":
                frame.pila_operandos.append(len(obj))
            elif isinstance(obj, str) and miembro == "length":
                frame.pila_operandos.append(len(obj))
            elif isinstance(obj, (ListaValue, PilaValue, ColaValue, BaseHechosValue)) and miembro == "length":
                frame.pila_operandos.append(obj.length())
            elif isinstance(obj, ReglaRef):
                if miembro == "marcada":
                    frame.pila_operandos.append(obj.id in self.estado.marcas_reglas or getattr(obj, "marcada", False))
                elif miembro == "nombre":
                    frame.pila_operandos.append(obj.nombre)
                elif miembro == "orden":
                    frame.pila_operandos.append(obj.orden)
                else:
                    raise RuntimeLaboratorioError(f"Propiedad '{miembro}' no soportada en Regla.", span=inst.span)
            elif isinstance(obj, HechoValor):
                if miembro in ("variable", "variable_nombre"):
                    frame.pila_operandos.append(obj.variable_nombre)
                elif miembro == "valor":
                    frame.pila_operandos.append(obj.valor)
                elif miembro == "tipo_dato":
                    frame.pila_operandos.append(obj.tipo_dato)
                else:
                    raise RuntimeLaboratorioError(f"Propiedad '{miembro}' no soportada en Hecho.", span=inst.span)
            elif isinstance(obj, VariableRef):
                if miembro == "nombre":
                    frame.pila_operandos.append(obj.nombre)
                elif miembro == "tipo_dato":
                    frame.pila_operandos.append(obj.tipo_dato)
                elif miembro == "es_nativa":
                    frame.pila_operandos.append(obj.es_nativa)
                elif miembro == "marcada":
                    frame.pila_operandos.append(
                        obj.id in self.estado.variables_consultadas or
                        obj.nombre.strip().lower() in self.estado.variables_consultadas
                    )
                else:
                    raise RuntimeLaboratorioError(f"Propiedad '{miembro}' no soportada en Variable.", span=inst.span)
            elif hasattr(obj, miembro):
                frame.pila_operandos.append(getattr(obj, miembro))
            else:
                raise RuntimeLaboratorioError(f"Propiedad '{miembro}' no soportada.", span=inst.span)
            return False

        if op == OpCode.STORE_MEMBER:
            val = frame.pila_operandos.pop()
            obj = frame.pila_operandos.pop()
            miembro = inst.arg
            if isinstance(obj, ReglaRef) and miembro == "marcada":
                if val:
                    self.estado.marcas_reglas.add(obj.id)
                else:
                    self.estado.marcas_reglas.discard(obj.id)
                setattr(obj, "marcada", bool(val))
            elif isinstance(obj, VariableRef) and miembro == "marcada":
                if val:
                    self.estado.variables_consultadas.add(obj.id)
                    self.estado.variables_consultadas.add(obj.nombre.strip().lower())
                else:
                    self.estado.variables_consultadas.discard(obj.id)
                    self.estado.variables_consultadas.discard(obj.nombre.strip().lower())
                setattr(obj, "marcada", bool(val))
            elif hasattr(obj, miembro):
                setattr(obj, miembro, val)
            else:
                raise RuntimeLaboratorioError(f"No se puede asignar a la propiedad '{miembro}'.", span=inst.span)
            return False

        if op == OpCode.CALL:
            func_nombre, arg_count = inst.arg
            argumentos = [frame.pila_operandos.pop() for _ in range(arg_count)][::-1]

            # 1. Comprobar si es Built-in
            if self._es_builtin(func_nombre):
                res = self._ejecutar_builtin(func_nombre, argumentos, inst.span)
                if self.estado.estado == "ESPERANDO_ENTRADA":
                    # Al suspender para esperar respuesta de consulta interactiva, pausar la VM.
                    # No rebobinamos frame.pc porque los argumentos ya fueron consumidos de la pila;
                    # resolver_pregunta colocará el Hecho respuesta en la pila para la siguiente instrucción (ej. STORE_VAR).
                    return True
                if res is not None:
                    frame.pila_operandos.append(res)
                return False

            # 2. Llamada a función de usuario
            if func_nombre in self.programa.funciones:
                if len(self.estado.frames) >= self.max_frames:
                    raise RuntimeLaboratorioError("Desbordamiento de pila de llamadas (recursión máxima alcanzada).", span=inst.span, codigo="STACK_OVERFLOW")
                func_obj = self.programa.funciones[func_nombre]
                vars_llamada = {p: argumentos[i] for i, p in enumerate(func_obj.parametros)}
                nuevo_frame = StackFrame(
                    nombre_funcion=func_nombre,
                    pc=0,
                    variables=vars_llamada,
                    pila_operandos=[]
                )
                self.estado.frames.append(nuevo_frame)
                return False

            raise RuntimeLaboratorioError(f"Función no encontrada: '{func_nombre}'", span=inst.span)

        if op == OpCode.CALL_METHOD:
            metodo_nombre, arg_count = inst.arg
            args = [frame.pila_operandos.pop() for _ in range(arg_count)][::-1]
            obj = frame.pila_operandos.pop()
            res = self._ejecutar_metodo_objeto(obj, metodo_nombre, args, inst.span)
            if res is not None:
                frame.pila_operandos.append(res)
            return False

        if op == OpCode.RETURN:
            tiene_val = inst.arg
            ret_val = frame.pila_operandos.pop() if tiene_val and frame.pila_operandos else None
            self.estado.frames.pop()
            if self.estado.frames and tiene_val:
                self.estado.frame_actual().pila_operandos.append(ret_val)
            return False

        return False

    def _es_builtin(self, nombre: str) -> bool:
        return nombre in (
            "Disparar", "DispararTodos", "marcada", "Marcar", "marcar", "DesmarcarReglas",
            "DesmarcarVariables", "MarcarVariablesDeLaBH", "HechoNativo", "VariablesPremisa",
            "getVarPremisa", "ObtenerHechosNativos", "Consultada",
            "Preguntar", "Pregunta", "TodasUnificadas", "Mostrar", "println", "print",
            "MostrarLosHechosDisparados", "MostrarMeta", "RegistrarPasada"
        )

    def _ejecutar_builtin(self, nombre: str, args: List[Any], span: Optional[SourceSpan]) -> Any:
        if nombre == "Disparar":
            regla, bh = args[0], args[1]
            if not isinstance(regla, ReglaRef) or not isinstance(bh, BaseHechosValue):
                raise RuntimeLaboratorioError("Disparar(r, bh) espera Regla y BaseHechos.", span=span)
            hecho_res = self.evaluador_reglas.evaluar_disparo(regla, bh)
            self.estado.eventos.append(EventoTraza(
                tipo="EVALUACION_REGLA",
                descripcion=f"Evaluando regla {regla.nombre}: {'Disparó' if hecho_res else 'No disparó'}",
                datos={"regla": regla.nombre, "disparo": bool(hecho_res)}
            ))
            return hecho_res

        if nombre == "marcada":
            arg = args[0]
            if isinstance(arg, ReglaRef):
                return arg.id in self.estado.marcas_reglas or getattr(arg, "marcada", False)
            elif isinstance(arg, VariableRef):
                return (
                    arg.id in self.estado.variables_consultadas or
                    arg.nombre.strip().lower() in self.estado.variables_consultadas or
                    getattr(arg, "marcada", False)
                )
            elif isinstance(arg, str):
                return arg.strip().lower() in self.estado.variables_consultadas
            raise RuntimeLaboratorioError("marcada(x) espera una Regla o Variable.", span=span)

        if nombre in ("Marcar", "marcar"):
            arg = args[0]
            if isinstance(arg, ReglaRef):
                self.estado.marcas_reglas.add(arg.id)
                setattr(arg, "marcada", True)
                self.estado.eventos.append(EventoTraza(
                    tipo="REGLA_MARCADA",
                    descripcion=f"Regla {arg.nombre} marcada.",
                    datos={"regla_id": arg.id, "nombre": arg.nombre}
                ))
                return None
            elif isinstance(arg, (VariableRef, str)):
                var_id = arg.id if isinstance(arg, VariableRef) else arg
                var_nom = (arg.nombre if isinstance(arg, VariableRef) else arg).strip().lower()
                self.estado.variables_consultadas.add(var_id)
                self.estado.variables_consultadas.add(var_nom)
                if isinstance(arg, VariableRef):
                    setattr(arg, "marcada", True)
                for f in self.estado.frames:
                    for val in f.variables.values():
                        if isinstance(val, BaseHechosValue):
                            val.variables_consultadas.add(var_id)
                            val.variables_consultadas.add(var_nom)
                self.estado.eventos.append(EventoTraza(
                    tipo="VARIABLE_MARCADA",
                    descripcion=f"Variable '{var_nom}' marcada.",
                    datos={"variable": var_nom}
                ))
                return None
            raise RuntimeLaboratorioError("marcar(x) espera una Regla o Variable.", span=span)

        if nombre == "DesmarcarReglas":
            if not args or args[0] is None:
                self.estado.marcas_reglas.clear()
            else:
                reglas = args[0]
                elems = reglas.elementos if isinstance(reglas, ListaValue) else (reglas if isinstance(reglas, list) else [])
                for r in elems:
                    if isinstance(r, ReglaRef):
                        self.estado.marcas_reglas.discard(r.id)
                        setattr(r, "marcada", False)
            self.estado.eventos.append(EventoTraza(
                tipo="DESMARCAR_REGLAS",
                descripcion="Reglas desmarcadas."
            ))
            return None

        if nombre == "DesmarcarVariables":
            if not args or args[0] is None:
                self.estado.variables_consultadas.clear()
                for f in self.estado.frames:
                    for val in f.variables.values():
                        if isinstance(val, BaseHechosValue):
                            val.variables_consultadas.clear()
            else:
                vars_in = args[0]
                elems = vars_in.elementos if isinstance(vars_in, ListaValue) else (vars_in if isinstance(vars_in, list) else [vars_in])
                for v in elems:
                    var_id = v.id if isinstance(v, VariableRef) else str(v)
                    var_nom = (v.nombre if isinstance(v, VariableRef) else str(v)).strip().lower()
                    self.estado.variables_consultadas.discard(var_id)
                    self.estado.variables_consultadas.discard(var_nom)
                    if isinstance(v, VariableRef):
                        setattr(v, "marcada", False)
                    for f in self.estado.frames:
                        for val in f.variables.values():
                            if isinstance(val, BaseHechosValue):
                                val.variables_consultadas.discard(var_id)
                                val.variables_consultadas.discard(var_nom)
            self.estado.eventos.append(EventoTraza(
                tipo="DESMARCAR_VARIABLES",
                descripcion="Variables desmarcadas."
            ))
            return None

        if nombre == "MarcarVariablesDeLaBH":
            bhs: List[BaseHechosValue] = []
            if args and isinstance(args[0], BaseHechosValue):
                bhs.append(args[0])
            else:
                for f in self.estado.frames:
                    for val in f.variables.values():
                        if isinstance(val, BaseHechosValue) and val not in bhs:
                            bhs.append(val)
            for bh in bhs:
                for h in bh.hechos_por_var.values():
                    v_id = getattr(h, "variable_id", None) or f"var_{h.variable_nombre}"
                    v_nom = h.variable_nombre.strip().lower()
                    self.estado.variables_consultadas.add(v_id)
                    self.estado.variables_consultadas.add(v_nom)
                    bh.variables_consultadas.add(v_id)
                    bh.variables_consultadas.add(v_nom)
            self.estado.eventos.append(EventoTraza(
                tipo="MARCAR_VARIABLES_BH",
                descripcion="Variables presentes en BH marcadas."
            ))
            return None

        if nombre in ("Preguntar", "Pregunta"):
            texto, var = str(args[0]), args[1]
            if not isinstance(var, VariableRef):
                raise RuntimeLaboratorioError(f"{nombre}(texto, v) espera una Variable.", span=span)

            # Registrar como consultada en el estado de la VM y en BH para evitar ciclos
            self.estado.variables_consultadas.add(var.id)
            self.estado.variables_consultadas.add(var.nombre.strip().lower())
            setattr(var, "marcada", True)
            for f in self.estado.frames:
                for val in f.variables.values():
                    if isinstance(val, BaseHechosValue):
                        val.variables_consultadas.add(var.id)
                        val.variables_consultadas.add(var.nombre.strip().lower())

            # Suspender VM y esperar interacción del usuario
            id_preg = str(uuid.uuid4())[:8]
            self.estado.pregunta_pendiente = PreguntaPendiente(
                id_pregunta=id_preg,
                variable_id=var.id,
                variable_nombre=var.nombre,
                texto=texto
            )
            self.estado.estado = "ESPERANDO_ENTRADA"
            self.estado.eventos.append(EventoTraza(
                tipo="CONSULTA_SOLICITADA",
                descripcion=f"Consulta al usuario: {texto} ({var.nombre})",
                datos={"id_pregunta": id_preg, "variable": var.nombre}
            ))
            return None

        if nombre == "VariablesPremisa":
            regla = args[0]
            if not isinstance(regla, ReglaRef):
                raise RuntimeLaboratorioError("VariablesPremisa(r) espera una Regla.", span=span)

            vars_list: List[VariableRef] = []
            vistos = set()

            premisas = getattr(regla, "premisas", []) or []
            if not premisas and self.evaluador_reglas:
                datos = self.evaluador_reglas.reglas_datos.get(regla.id, {})
                premisas = datos.get("condiciones", [])

            for p in premisas:
                var_nom = p.get("variable") or p.get("variable_nombre") or ""
                if var_nom and var_nom not in vistos:
                    vistos.add(var_nom)
                    vars_list.append(VariableRef(
                        id=p.get("variable_id") or f"var_{var_nom}",
                        nombre=var_nom,
                        tipo_dato=p.get("tipo_dato", "TEXTO"),
                        es_nativa=p.get("es_nativa", False),
                    ))
            return vars_list

        if nombre == "getVarPremisa":
            regla = args[0]
            if not isinstance(regla, ReglaRef):
                raise RuntimeLaboratorioError("getVarPremisa(r) espera una Regla.", span=span)
            premisas = getattr(regla, "premisas", []) or []
            if not premisas and self.evaluador_reglas:
                datos = self.evaluador_reglas.reglas_datos.get(regla.id, {})
                premisas = datos.get("condiciones", [])
            if not premisas:
                return None
            p = premisas[0]
            var_nom = p.get("variable") or p.get("variable_nombre") or ""
            return VariableRef(
                id=p.get("variable_id") or f"var_{var_nom}",
                nombre=var_nom,
                tipo_dato=p.get("tipo_dato", "TEXTO"),
                es_nativa=p.get("es_nativa", False),
            )

        if nombre == "Consultada":
            var = args[0]
            if isinstance(var, VariableRef):
                var_nom = var.nombre.strip().lower()
                var_id = var.id
            elif isinstance(var, str):
                var_nom = var.strip().lower()
                var_id = var
            else:
                raise RuntimeLaboratorioError("Consultada(v) espera una Variable o String.", span=span)

            if var_id in self.estado.variables_consultadas or var_nom in self.estado.variables_consultadas:
                return True

            for f in self.estado.frames:
                for val in f.variables.values():
                    if isinstance(val, BaseHechosValue):
                        if var_nom in val.variables_consultadas or var_id in val.variables_consultadas:
                            return True
            return False

        if nombre == "HechoNativo":
            var = args[0]
            if not isinstance(var, VariableRef):
                raise RuntimeLaboratorioError("HechoNativo(v) espera una Variable.", span=span)
            return getattr(var, "es_nativa", False)

        if nombre == "ObtenerHechosNativos":
            reglas = args[0]
            elems = reglas.elementos if isinstance(reglas, ListaValue) else (reglas if isinstance(reglas, list) else [])
            vars_nativas: List[VariableRef] = []
            vistos = set()
            for r in elems:
                if isinstance(r, ReglaRef):
                    premisas = getattr(r, "premisas", []) or []
                    if not premisas and self.evaluador_reglas:
                        premisas = self.evaluador_reglas.reglas_datos.get(r.id, {}).get("condiciones", [])
                    for p in premisas:
                        var_nom = p.get("variable") or p.get("variable_nombre") or ""
                        if var_nom and var_nom not in vistos:
                            vistos.add(var_nom)
                            es_nat = p.get("es_nativa", True)
                            vars_nativas.append(VariableRef(
                                id=p.get("variable_id") or f"var_{var_nom}",
                                nombre=var_nom,
                                tipo_dato=p.get("tipo_dato", "TEXTO"),
                                es_nativa=es_nat,
                            ))
            return ListaValue(vars_nativas)

        if nombre == "DispararTodos":
            regla, bh = args[0], args[1]
            if not isinstance(regla, ReglaRef) or not isinstance(bh, BaseHechosValue):
                raise RuntimeLaboratorioError("DispararTodos(r, bh) espera Regla y BaseHechos.", span=span)
            hecho_res = self.evaluador_reglas.evaluar_disparo(regla, bh)
            self.estado.eventos.append(EventoTraza(
                tipo="EVALUACION_REGLA",
                descripcion=f"Evaluando regla {regla.nombre} (DispararTodos): {'Disparó' if hecho_res else 'No disparó'}",
                datos={"regla": regla.nombre, "disparo": bool(hecho_res)}
            ))
            return [hecho_res] if hecho_res else []

        if nombre == "MostrarMeta":
            meta, bh = args[0], args[1]
            if not isinstance(meta, VariableRef) or not isinstance(bh, BaseHechosValue):
                raise RuntimeLaboratorioError("MostrarMeta(meta, bh) espera Variable y BaseHechos.", span=span)
            h = bh.get(meta)
            if h:
                msg = f"Meta alcanzada: {meta.nombre} = {h.valor}"
            else:
                msg = f"Meta no alcanzada: {meta.nombre}"
            self.estado.salidas_texto.append(msg)
            self.estado.eventos.append(EventoTraza(tipo="SALIDA_TEXTO", descripcion=msg))
            return None

        if nombre in ("Mostrar", "println", "print"):
            msg = str(args[0])
            self.estado.salidas_texto.append(msg)
            self.estado.eventos.append(EventoTraza(tipo="SALIDA_TEXTO", descripcion=msg))
            return None

        if nombre == "MostrarLosHechosDisparados":
            bh = args[0]
            if isinstance(bh, BaseHechosValue):
                hechos_str = ", ".join([f"{h.variable_nombre}={h.valor}" for h in bh.hechos_por_var.values()])
                msg = f"Hechos derivados: [{hechos_str}]"
                self.estado.salidas_texto.append(msg)
                self.estado.eventos.append(EventoTraza(tipo="SALIDA_TEXTO", descripcion=msg))
            return None

        if nombre == "RegistrarPasada":
            n = int(args[0])
            self.estado.eventos.append(EventoTraza(tipo="PASADA", descripcion=f"Iniciando Pasada {n}", datos={"pasada": n}))
            return None

        if nombre == "TodasUnificadas":
            bh, metas = args[0], args[1]
            if isinstance(bh, BaseHechosValue) and isinstance(metas, ListaValue):
                for m in metas.elementos:
                    if isinstance(m, VariableRef) and not bh.contains(m):
                        return False
                return True
            return False

        return None

    def _ejecutar_metodo_objeto(self, obj: Any, metodo: str, args: List[Any], span: Optional[SourceSpan]) -> Any:
        if obj is None:
            raise RuntimeLaboratorioError(f"Intento de llamar al método '{metodo}' sobre una referencia nula (NullPointerException).", span=span, codigo="ARGUMENTO_NULO")

        if isinstance(obj, list):
            if metodo == "length": return len(obj)
            if metodo == "vacia": return len(obj) == 0
            if metodo == "add":
                obj.append(args[0])
                return True
            if metodo == "contains":
                return any(valores_son_iguales(elem, args[0]) for elem in obj)
            if metodo == "get":
                idx = args[0]
                if isinstance(idx, int) and 0 <= idx < len(obj):
                    return obj[idx]
                raise RuntimeLaboratorioError(f"Índice fuera de rango: {idx}.", span=span)

        if isinstance(obj, BaseHechosValue):
            if metodo == "length": return obj.length()
            if metodo == "contains": return obj.contains(args[0])
            if metodo == "add":
                res = obj.add(args[0])
                if res:
                    self.estado.eventos.append(EventoTraza(
                        tipo="HECHO_AGREGADO",
                        descripcion=f"Hecho incorporado a BH: {args[0].variable_nombre} = {args[0].valor}",
                        datos={"variable": args[0].variable_nombre, "valor": args[0].valor}
                    ))
                return res
            if metodo == "get": return obj.get(args[0])

        if isinstance(obj, ListaValue):
            if metodo == "length": return obj.length()
            if metodo == "vacia": return obj.vacia()
            if metodo == "add": return obj.add(args[0])
            if metodo == "contains": return obj.contains(args[0])
            if metodo == "del": return obj.delete(args[0])
            if metodo == "get": return obj.get(args[0])

        if isinstance(obj, PilaValue):
            if metodo == "length": return obj.length()
            if metodo == "vacia": return obj.vacia()
            if metodo == "push": return obj.push(args[0])
            if metodo == "pop": return obj.pop()

        if isinstance(obj, ColaValue):
            if metodo == "length": return obj.length()
            if metodo == "vacia": return obj.vacia()
            if metodo == "meter": return obj.meter(args[0])
            if metodo == "pop": return obj.pop()

        if isinstance(obj, ReglaRef):
            if metodo == "getVarPremisa":
                premisas = getattr(obj, "premisas", []) or []
                if not premisas and self.evaluador_reglas:
                    datos = self.evaluador_reglas.reglas_datos.get(obj.id, {})
                    premisas = datos.get("condiciones", [])
                if not premisas:
                    return None
                p = premisas[0]
                var_nom = p.get("variable") or p.get("variable_nombre") or ""
                return VariableRef(
                    id=p.get("variable_id") or f"var_{var_nom}",
                    nombre=var_nom,
                    tipo_dato=p.get("tipo_dato", "TEXTO"),
                    es_nativa=p.get("es_nativa", False),
                )
            if metodo == "getNombre":
                return obj.nombre

        if isinstance(obj, HechoValor):
            if metodo == "getVar":
                return VariableRef(
                    id=getattr(obj, "variable_id", None) or f"var_{obj.variable_nombre}",
                    nombre=obj.variable_nombre,
                    tipo_dato=obj.tipo_dato,
                    es_nativa=False,
                )
            if metodo == "getValorTexto":
                return str(obj.valor)

        if isinstance(obj, VariableRef):
            if metodo == "getNombre":
                return obj.nombre

        raise RuntimeLaboratorioError(f"Método '{metodo}' no existe en {type(obj).__name__}.", span=span)

    def _aplicar_binario(self, a: Any, op: str, b: Any, span: Optional[SourceSpan]) -> Any:
        if op == "==": return valores_son_iguales(a, b)
        if op == "!=": return not valores_son_iguales(a, b)
        if op == "<": return a < b
        if op == "<=": return a <= b
        if op == ">": return a > b
        if op == ">=": return a >= b
        if op == "+":
            if isinstance(a, str) or isinstance(b, str):
                return str(a) + str(b)
            return a + b
        if op == "-": return a - b
        if op == "*": return a * b
        if op == "/":
            if b == 0:
                raise RuntimeLaboratorioError("División por cero.", span=span, codigo="DIVISION_POR_CERO")
            return a // b if isinstance(a, int) and isinstance(b, int) else a / b
        if op == "%":
            if b == 0:
                raise RuntimeLaboratorioError("Resto de división por cero.", span=span, codigo="DIVISION_POR_CERO")
            return a % b
        if op == "&&": return bool(a) and bool(b)
        if op == "||": return bool(a) or bool(b)

        raise RuntimeLaboratorioError(f"Operador binario desconocido: {op}", span=span)
