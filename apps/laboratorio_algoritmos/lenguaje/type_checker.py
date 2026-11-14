from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from ..exceptions import SourceSpan, TipoError
from .ast_nodes import (
    ProgramNode, FunctionDefNode, ParamNode, TypeNode,
    StmtNode, BlockStmtNode, VarDeclStmtNode, AssignmentStmtNode, UpdateStmtNode,
    ExpressionStmtNode, IfStmtNode, WhileStmtNode, ForStmtNode,
    ReturnStmtNode, BreakStmtNode, ContinueStmtNode,
    ExprNode, LiteralExprNode, IdentifierExprNode, UnaryExprNode,
    BinaryExprNode, CallExprNode, MemberAccessExprNode, IndexExprNode,
    NewArrayExprNode, NewCollectionExprNode
)


@dataclass
class TipoSimbolo:
    nombre: str                      # int, double, boolean, String, void, Regla, Variable, Hecho, BaseHechos, Lista, Pila, Cola, null
    es_arreglo: bool = False
    parametro_tipo: Optional['TipoSimbolo'] = None

    def __repr__(self) -> str:
        s = self.nombre
        if self.parametro_tipo:
            s += f"<{self.parametro_tipo}>"
        if self.es_arreglo:
            s += "[]"
        return s

    def es_compatible_con(self, otro: 'TipoSimbolo') -> bool:
        # null es compatible con cualquier referencia (no primitivas)
        if self.nombre == "null":
            return otro.es_referencia()
        if otro.nombre == "null":
            return self.es_referencia()

        # Tipos primitivos y promoción int -> double
        if self.nombre == "int" and otro.nombre == "double" and not self.es_arreglo and not otro.es_arreglo:
            return True

        # Compatibilidad entre Arreglo T[] y Lista<T> para interoperabilidad
        if self.es_arreglo and otro.nombre == "Lista" and otro.parametro_tipo:
            return TipoSimbolo(self.nombre).es_compatible_con(otro.parametro_tipo)
        if otro.es_arreglo and self.nombre == "Lista" and self.parametro_tipo:
            return self.parametro_tipo.es_compatible_con(TipoSimbolo(otro.nombre))

        if self.es_arreglo != otro.es_arreglo:
            return False

        if self.nombre != otro.nombre:
            return False

        if self.parametro_tipo and otro.parametro_tipo:
            return self.parametro_tipo.es_compatible_con(otro.parametro_tipo)

        return True

    def es_referencia(self) -> bool:
        if self.es_arreglo:
            return True
        return self.nombre in ("String", "Regla", "Variable", "Hecho", "BaseHechos", "Lista", "Pila", "Cola", "null")

    def es_numerico(self) -> bool:
        return not self.es_arreglo and self.nombre in ("int", "double")


# Tipos básicos predefinidos
TIPO_INT = TipoSimbolo("int")
TIPO_DOUBLE = TipoSimbolo("double")
TIPO_BOOLEAN = TipoSimbolo("boolean")
TIPO_STRING = TipoSimbolo("String")
TIPO_VOID = TipoSimbolo("void")
TIPO_NULL = TipoSimbolo("null")
TIPO_REGLA = TipoSimbolo("Regla")
TIPO_VARIABLE = TipoSimbolo("Variable")
TIPO_HECHO = TipoSimbolo("Hecho")
TIPO_BASE_HECHOS = TipoSimbolo("BaseHechos")


@dataclass
class FirmaFuncion:
    tipo_retorno: TipoSimbolo
    parametros: List[Tuple[str, TipoSimbolo]]


# Catálogo de Built-ins del Laboratorio
BUILTIN_FUNCTIONS: Dict[str, FirmaFuncion] = {
    "Disparar": FirmaFuncion(TIPO_HECHO, [("r", TIPO_REGLA), ("bh", TIPO_BASE_HECHOS)]),
    "DispararTodos": FirmaFuncion(TipoSimbolo("Hecho", es_arreglo=True), [("r", TIPO_REGLA), ("bh", TIPO_BASE_HECHOS)]),
    "marcada": FirmaFuncion(TIPO_BOOLEAN, [("r", TIPO_REGLA)]),
    "Marcar": FirmaFuncion(TIPO_VOID, [("r", TIPO_REGLA)]),
    "DesmarcarReglas": FirmaFuncion(TIPO_VOID, [("r", TipoSimbolo("Regla", es_arreglo=True))]),
    "HechoNativo": FirmaFuncion(TIPO_BOOLEAN, [("v", TIPO_VARIABLE)]),
    "VariablesPremisa": FirmaFuncion(TipoSimbolo("Variable", es_arreglo=True), [("r", TIPO_REGLA)]),
    "ObtenerHechosNativos": FirmaFuncion(TipoSimbolo("Lista", parametro_tipo=TIPO_VARIABLE), [("r", TipoSimbolo("Regla", es_arreglo=True))]),
    "Consultada": FirmaFuncion(TIPO_BOOLEAN, [("v", TIPO_VARIABLE)]),
    "Preguntar": FirmaFuncion(TIPO_HECHO, [("texto", TIPO_STRING), ("v", TIPO_VARIABLE)]),
    "TodasUnificadas": FirmaFuncion(TIPO_BOOLEAN, [("bh", TIPO_BASE_HECHOS), ("metas", TipoSimbolo("Lista", parametro_tipo=TIPO_VARIABLE))]),
    "Mostrar": FirmaFuncion(TIPO_VOID, [("texto", TIPO_STRING)]),
    "println": FirmaFuncion(TIPO_VOID, [("texto", TIPO_STRING)]),
    "print": FirmaFuncion(TIPO_VOID, [("texto", TIPO_STRING)]),
    "MostrarLosHechosDisparados": FirmaFuncion(TIPO_VOID, [("bh", TIPO_BASE_HECHOS)]),
    "MostrarMeta": FirmaFuncion(TIPO_VOID, [("meta", TIPO_VARIABLE), ("bh", TIPO_BASE_HECHOS)]),
    "RegistrarPasada": FirmaFuncion(TIPO_VOID, [("pasada", TIPO_INT)]),
}


class Scope:
    def __init__(self, padre: Optional['Scope'] = None):
        self.padre = padre
        self.variables: Dict[str, TipoSimbolo] = {}

    def definir(self, nombre: str, tipo: TipoSimbolo, span: SourceSpan):
        if nombre in self.variables:
            raise TipoError(f"Variable '{nombre}' ya declarada en este ámbito.", span=span, codigo="VARIABLE_REDECLARADA")
        self.variables[nombre] = tipo

    def resolver(self, nombre: str) -> Optional[TipoSimbolo]:
        if nombre in self.variables:
            return self.variables[nombre]
        if self.padre:
            return self.padre.resolver(nombre)
        return None


class TypeChecker:
    def __init__(self, programa: ProgramNode):
        self.programa = programa
        self.funciones: Dict[str, FirmaFuncion] = dict(BUILTIN_FUNCTIONS)
        self.funcion_actual: Optional[FunctionDefNode] = None
        self.profundidad_bucles = 0
        self.tipos_expresiones: Dict[int, TipoSimbolo] = {}

    def verificar(self):
        # 1. Registrar firmas de todas las funciones de usuario
        for func in self.programa.funciones:
            params = []
            for p in func.parametros:
                tipo_p = self._convertir_tipo_nodo(p.tipo)
                params.append((p.nombre, tipo_p))
            tipo_ret = self._convertir_tipo_nodo(func.tipo_retorno)
            if func.nombre in self.funciones:
                raise TipoError(
                    f"Función duplicada o colisión con built-in: '{func.nombre}'.",
                    span=func.span,
                    codigo="COLISION_NOMBRE_FUNCION"
                )
            self.funciones[func.nombre] = FirmaFuncion(tipo_ret, params)

        # 2. Verificar cuerpo de cada función
        for func in self.programa.funciones:
            self.funcion_actual = func
            scope_inicial = Scope()
            # Añadir parámetros al scope
            for p in func.parametros:
                tipo_param = self._convertir_tipo_nodo(p.tipo)
                scope_inicial.definir(p.nombre, tipo_param, p.span)

            retorno_garantizado = self._verificar_bloque(func.cuerpo, scope_inicial)

            tipo_ret = self._convertir_tipo_nodo(func.tipo_retorno)
            if tipo_ret.nombre != "void" and not retorno_garantizado:
                raise TipoError(
                    f"La función '{func.nombre}' no garantiza un retorno en todas sus ramas de ejecución.",
                    span=func.span,
                    codigo="FALTA_RETURN"
                )

    def _convertir_tipo_nodo(self, nodo: TypeNode) -> TipoSimbolo:
        param_tipo = None
        if nodo.parametro_tipo:
            param_tipo = self._convertir_tipo_nodo(nodo.parametro_tipo)
        return TipoSimbolo(
            nombre=nodo.nombre_base,
            es_arreglo=nodo.es_arreglo,
            parametro_tipo=param_tipo
        )

    def _verificar_bloque(self, bloque: BlockStmtNode, scope: Scope) -> bool:
        scope_bloque = Scope(scope)
        retorno_garantizado = False

        for stmt in bloque.sentencias:
            si_retorna = self._verificar_sentencia(stmt, scope_bloque)
            if si_retorna:
                retorno_garantizado = True

        return retorno_garantizado

    def _verificar_sentencia(self, stmt: StmtNode, scope: Scope) -> bool:
        if isinstance(stmt, BlockStmtNode):
            return self._verificar_bloque(stmt, scope)

        if isinstance(stmt, VarDeclStmtNode):
            tipo_declarado = self._convertir_tipo_nodo(stmt.tipo)
            if tipo_declarado.nombre == "void":
                raise TipoError("Una variable no puede tener tipo 'void'.", span=stmt.span, codigo="TIPO_VOID_INVALIDO")

            if stmt.inicializador:
                tipo_expr = self._verificar_expresion(stmt.inicializador, scope)
                if not tipo_expr.es_compatible_con(tipo_declarado):
                    raise TipoError(
                        f"Tipo incompatible en inicialización de '{stmt.nombre}'. Esperado {tipo_declarado}, recibido {tipo_expr}.",
                        span=stmt.inicializador.span,
                        codigo="TIPO_INCOMPATIBLE"
                    )
            scope.definir(stmt.nombre, tipo_declarado, stmt.span)
            return False

        if isinstance(stmt, AssignmentStmtNode):
            tipo_dest = self._verificar_expresion(stmt.destino, scope)
            tipo_val = self._verificar_expresion(stmt.valor, scope)
            if not tipo_val.es_compatible_con(tipo_dest):
                raise TipoError(
                    f"Tipo incompatible en asignación. Destino es {tipo_dest}, pero la expresión es {tipo_val}.",
                    span=stmt.span,
                    codigo="TIPO_INCOMPATIBLE"
                )
            return False

        if isinstance(stmt, UpdateStmtNode):
            tipo_dest = self._verificar_expresion(stmt.destino, scope)
            if tipo_dest.nombre != "int" or tipo_dest.es_arreglo:
                raise TipoError("El operador ++/-- solo se puede aplicar a variables enteras ('int').", span=stmt.span, codigo="OPERADOR_INVALIDO")
            return False

        if isinstance(stmt, ExpressionStmtNode):
            self._verificar_expresion(stmt.expresion, scope)
            return False

        if isinstance(stmt, IfStmtNode):
            tipo_cond = self._verificar_expresion(stmt.condicion, scope)
            if tipo_cond.nombre != "boolean" or tipo_cond.es_arreglo:
                raise TipoError("La condición de un 'if' debe ser de tipo boolean.", span=stmt.condicion.span, codigo="CONDICION_NO_BOOLEANA")

            ret_then = self._verificar_sentencia(stmt.rama_then, scope)
            ret_else = False
            if stmt.rama_else:
                ret_else = self._verificar_sentencia(stmt.rama_else, scope)

            return ret_then and ret_else

        if isinstance(stmt, WhileStmtNode):
            tipo_cond = self._verificar_expresion(stmt.condicion, scope)
            if tipo_cond.nombre != "boolean" or tipo_cond.es_arreglo:
                raise TipoError("La condición de un 'while' debe ser de tipo boolean.", span=stmt.condicion.span, codigo="CONDICION_NO_BOOLEANA")

            self.profundidad_bucles += 1
            self._verificar_sentencia(stmt.cuerpo, scope)
            self.profundidad_bucles -= 0
            return False

        if isinstance(stmt, ForStmtNode):
            scope_for = Scope(scope)
            if stmt.inicializacion:
                self._verificar_sentencia(stmt.inicializacion, scope_for)

            if stmt.condicion:
                tipo_cond = self._verificar_expresion(stmt.condicion, scope_for)
                if tipo_cond.nombre != "boolean" or tipo_cond.es_arreglo:
                    raise TipoError("La condición del bucle 'for' debe ser de tipo boolean.", span=stmt.condicion.span, codigo="CONDICION_NO_BOOLEANA")

            if stmt.actualizacion:
                self._verificar_sentencia(stmt.actualizacion, scope_for)

            self.profundidad_bucles += 1
            self._verificar_sentencia(stmt.cuerpo, scope_for)
            self.profundidad_bucles -= 1
            return False

        if isinstance(stmt, BreakStmtNode):
            if self.profundidad_bucles <= 0:
                raise TipoError("'break' solo está permitido dentro de un bucle.", span=stmt.span, codigo="BREAK_FUERA_DE_BUCLE")
            return False

        if isinstance(stmt, ContinueStmtNode):
            if self.profundidad_bucles <= 0:
                raise TipoError("'continue' solo está permitido dentro de un bucle.", span=stmt.span, codigo="CONTINUE_FUERA_DE_BUCLE")
            return False

        if isinstance(stmt, ReturnStmtNode):
            tipo_esperado = self._convertir_tipo_nodo(self.funcion_actual.tipo_retorno)
            if stmt.valor:
                tipo_devuelto = self._verificar_expresion(stmt.valor, scope)
                if not tipo_devuelto.es_compatible_con(tipo_esperado):
                    raise TipoError(
                        f"Retorno incompatible. La función espera {tipo_esperado}, pero devuelve {tipo_devuelto}.",
                        span=stmt.span,
                        codigo="RETORNO_INCOMPATIBLE"
                    )
            else:
                if tipo_esperado.nombre != "void":
                    raise TipoError(
                        f"La función espera retornar {tipo_esperado}, pero no devuelve ningún valor.",
                        span=stmt.span,
                        codigo="FALTA_VALOR_RETORNO"
                    )
            return True

        return False

    def _verificar_expresion(self, expr: ExprNode, scope: Scope) -> TipoSimbolo:
        tipo = self._calcular_tipo_expresion(expr, scope)
        self.tipos_expresiones[id(expr)] = tipo
        return tipo

    def _calcular_tipo_expresion(self, expr: ExprNode, scope: Scope) -> TipoSimbolo:
        if isinstance(expr, LiteralExprNode):
            if expr.tipo_literal == "int":
                return TIPO_INT
            if expr.tipo_literal == "double":
                return TIPO_DOUBLE
            if expr.tipo_literal == "boolean":
                return TIPO_BOOLEAN
            if expr.tipo_literal == "String":
                return TIPO_STRING
            if expr.tipo_literal == "null":
                return TIPO_NULL

        if isinstance(expr, IdentifierExprNode):
            tipo = scope.resolver(expr.nombre)
            if not tipo:
                raise TipoError(f"Variable '{expr.nombre}' no declarada.", span=expr.span, codigo="VARIABLE_NO_DECLARADA")
            return tipo

        if isinstance(expr, UnaryExprNode):
            tipo_op = self._verificar_expresion(expr.operando, scope)
            if expr.operador == "!":
                if tipo_op.nombre != "boolean" or tipo_op.es_arreglo:
                    raise TipoError("El operador '!' solo se aplica a booleanos.", span=expr.span, codigo="OPERADOR_INVALIDO")
                return TIPO_BOOLEAN
            if expr.operador == "-":
                if not tipo_op.es_numerico():
                    raise TipoError("El operador '-' solo se aplica a números (int, double).", span=expr.span, codigo="OPERADOR_INVALIDO")
                return tipo_op

        if isinstance(expr, BinaryExprNode):
            tipo_izq = self._verificar_expresion(expr.izquierda, scope)
            tipo_der = self._verificar_expresion(expr.derecha, scope)

            # Lógicos
            if expr.operador in ("&&", "||"):
                if tipo_izq.nombre != "boolean" or tipo_der.nombre != "boolean" or tipo_izq.es_arreglo or tipo_der.es_arreglo:
                    raise TipoError(f"Operador '{expr.operador}' requiere operandos booleanos.", span=expr.span, codigo="TIPO_INCOMPATIBLE")
                return TIPO_BOOLEAN

            # Comparación de igualdad
            if expr.operador in ("==", "!="):
                if not (tipo_izq.es_compatible_con(tipo_der) or tipo_der.es_compatible_con(tipo_izq)):
                    raise TipoError(f"No se pueden comparar tipos incompatibles: {tipo_izq} y {tipo_der}.", span=expr.span, codigo="COMPARACION_INCOMPATIBLE")
                return TIPO_BOOLEAN

            # Relacionales
            if expr.operador in ("<", "<=", ">", ">="):
                if not tipo_izq.es_numerico() or not tipo_der.es_numerico():
                    raise TipoError(f"Operador '{expr.operador}' solo se puede aplicar entre números.", span=expr.span, codigo="COMPARACION_NO_NUMERICA")
                return TIPO_BOOLEAN

            # Concatenación de Strings
            if expr.operador == "+":
                if tipo_izq.nombre == "String" or tipo_der.nombre == "String":
                    return TIPO_STRING

            # Aritméticos
            if expr.operador in ("+", "-", "*", "/", "%"):
                if not tipo_izq.es_numerico() or not tipo_der.es_numerico():
                    raise TipoError(f"Operador aritmético '{expr.operador}' solo se aplica a números.", span=expr.span, codigo="ARITMETICA_NO_NUMERICA")
                if tipo_izq.nombre == "double" or tipo_der.nombre == "double":
                    return TIPO_DOUBLE
                return TIPO_INT

        if isinstance(expr, MemberAccessExprNode):
            tipo_obj = self._verificar_expresion(expr.objeto, scope)
            # Arreglo .length
            if tipo_obj.es_arreglo and expr.miembro == "length":
                return TIPO_INT

            # Regla
            if tipo_obj.nombre == "Regla":
                if expr.miembro == "marcada":
                    return TIPO_BOOLEAN
                if expr.miembro == "nombre":
                    return TIPO_STRING
                if expr.miembro in ("orden", "prioridad"):
                    return TIPO_INT

            # Hecho
            if tipo_obj.nombre == "Hecho":
                if expr.miembro in ("variable", "variable_nombre"):
                    return TIPO_STRING
                if expr.miembro == "valor":
                    return TIPO_STRING
                if expr.miembro == "tipo_dato":
                    return TIPO_STRING

            # Variable
            if tipo_obj.nombre == "Variable":
                if expr.miembro == "nombre":
                    return TIPO_STRING
                if expr.miembro == "tipo_dato":
                    return TIPO_STRING
                if expr.miembro == "es_nativa":
                    return TIPO_BOOLEAN

            # Colecciones o BaseHechos con .length
            if tipo_obj.nombre in ("Lista", "Pila", "Cola", "BaseHechos") and expr.miembro == "length":
                return TIPO_INT

            raise TipoError(f"Miembro '{expr.miembro}' no encontrado en tipo {tipo_obj}.", span=expr.span, codigo="MIEMBRO_INEXISTENTE")

        if isinstance(expr, IndexExprNode):
            tipo_col = self._verificar_expresion(expr.coleccion, scope)
            tipo_idx = self._verificar_expresion(expr.indice, scope)
            if tipo_idx.nombre != "int" or tipo_idx.es_arreglo:
                raise TipoError("El índice debe ser de tipo int.", span=expr.indice.span, codigo="INDICE_NO_ENTERO")
            if not tipo_col.es_arreglo:
                raise TipoError(f"Tipo {tipo_col} no admite acceso por corchetes [].", span=expr.span, codigo="NO_ES_ARREGLO")
            return TipoSimbolo(nombre=tipo_col.nombre, es_arreglo=False, parametro_tipo=tipo_col.parametro_tipo)

        if isinstance(expr, CallExprNode):
            # Llamada a método: obj.metodo(args)
            if isinstance(expr.callee, MemberAccessExprNode):
                tipo_obj = self._verificar_expresion(expr.callee.objeto, scope)
                metodo = expr.callee.miembro
                args_tipos = [self._verificar_expresion(a, scope) for a in expr.argumentos]
                return self._verificar_llamada_metodo(tipo_obj, metodo, args_tipos, expr.span)

            # Llamada a función global o builtin: func(args)
            if isinstance(expr.callee, IdentifierExprNode):
                nombre_func = expr.callee.nombre
                args_tipos = [self._verificar_expresion(a, scope) for a in expr.argumentos]
                if nombre_func not in self.funciones:
                    raise TipoError(f"Función '{nombre_func}' no encontrada.", span=expr.span, codigo="FUNCION_NO_DECLARADA")
                firma = self.funciones[nombre_func]
                if len(args_tipos) != len(firma.parametros):
                    raise TipoError(
                        f"Función '{nombre_func}' espera {len(firma.parametros)} argumentos, pero recibió {len(args_tipos)}.",
                        span=expr.span,
                        codigo="CANTIDAD_ARGUMENTOS_INCORRECTA"
                    )
                for i, (arg_t, (p_nom, p_t)) in enumerate(zip(args_tipos, firma.parametros)):
                    if not arg_t.es_compatible_con(p_t):
                        raise TipoError(
                            f"Argumento {i+1} de '{nombre_func}' incompatible. Esperado {p_t}, recibido {arg_t}.",
                            span=expr.argumentos[i].span,
                            codigo="TIPO_ARGUMENTO_INCOMPATIBLE"
                        )
                return firma.tipo_retorno

            raise TipoError("Expresión no invocable como función.", span=expr.span, codigo="NO_INVOCABLE")

        if isinstance(expr, NewArrayExprNode):
            tipo_tam = self._verificar_expresion(expr.tamano, scope)
            if tipo_tam.nombre != "int" or tipo_tam.es_arreglo:
                raise TipoError("El tamaño del arreglo debe ser un entero.", span=expr.tamano.span, codigo="TAMANO_NO_ENTERO")
            tipo_elem = self._convertir_tipo_nodo(expr.tipo_elemento)
            return TipoSimbolo(nombre=tipo_elem.nombre, es_arreglo=True, parametro_tipo=tipo_elem.parametro_tipo)

        if isinstance(expr, NewCollectionExprNode):
            tipo_elem = self._convertir_tipo_nodo(expr.parametro_tipo)
            return TipoSimbolo(nombre=expr.tipo_coleccion, es_arreglo=False, parametro_tipo=tipo_elem)

        raise TipoError(f"Expresión no soportada para análisis de tipo: {type(expr).__name__}", span=expr.span)

    def _verificar_llamada_metodo(self, tipo_obj: TipoSimbolo, metodo: str, args: List[TipoSimbolo], span: SourceSpan) -> TipoSimbolo:
        # Métodos de BaseHechos
        if tipo_obj.nombre == "BaseHechos" and not tipo_obj.es_arreglo:
            if metodo == "length":
                if len(args) != 0: raise TipoError("BH.length() no recibe argumentos.", span=span)
                return TIPO_INT
            if metodo == "contains":
                if len(args) != 1 or args[0].nombre != "Variable": raise TipoError("BH.contains(v) espera 1 argumento de tipo Variable.", span=span)
                return TIPO_BOOLEAN
            if metodo == "add":
                if len(args) != 1 or args[0].nombre != "Hecho": raise TipoError("BH.add(h) espera 1 argumento de tipo Hecho.", span=span)
                return TIPO_BOOLEAN
            if metodo == "get":
                if len(args) != 1 or args[0].nombre != "Variable": raise TipoError("BH.get(v) espera 1 argumento de tipo Variable.", span=span)
                return TIPO_HECHO

        # Métodos de Lista<T>
        if tipo_obj.nombre == "Lista" and not tipo_obj.es_arreglo:
            tipo_t = tipo_obj.parametro_tipo or TIPO_VARIABLE
            if metodo in ("length", "vacia"):
                if len(args) != 0: raise TipoError(f"Lista.{metodo}() no recibe argumentos.", span=span)
                return TIPO_INT if metodo == "length" else TIPO_BOOLEAN
            if metodo in ("add", "contains", "del"):
                if len(args) != 1 or not args[0].es_compatible_con(tipo_t):
                    raise TipoError(f"Lista.{metodo}(elem) espera un argumento de tipo {tipo_t}.", span=span)
                return TIPO_BOOLEAN
            if metodo == "get":
                if len(args) != 1 or args[0].nombre != "int": raise TipoError("Lista.get(i) espera un índice int.", span=span)
                return tipo_t

        # Métodos de Pila<T>
        if tipo_obj.nombre == "Pila" and not tipo_obj.es_arreglo:
            tipo_t = tipo_obj.parametro_tipo or TIPO_VARIABLE
            if metodo in ("length", "vacia"):
                if len(args) != 0: raise TipoError(f"Pila.{metodo}() no recibe argumentos.", span=span)
                return TIPO_INT if metodo == "length" else TIPO_BOOLEAN
            if metodo == "pop":
                if len(args) != 0: raise TipoError("Pila.pop() no recibe argumentos.", span=span)
                return tipo_t
            if metodo == "push":
                if len(args) != 1 or not args[0].es_compatible_con(tipo_t): raise TipoError(f"Pila.push(elem) espera {tipo_t}.", span=span)
                return TIPO_VOID

        # Métodos de Cola<T>
        if tipo_obj.nombre == "Cola" and not tipo_obj.es_arreglo:
            tipo_t = tipo_obj.parametro_tipo or TIPO_REGLA
            if metodo in ("length", "vacia"):
                if len(args) != 0: raise TipoError(f"Cola.{metodo}() no recibe argumentos.", span=span)
                return TIPO_INT if metodo == "length" else TIPO_BOOLEAN
            if metodo == "pop":
                if len(args) != 0: raise TipoError("Cola.pop() no recibe argumentos.", span=span)
                return tipo_t
            if metodo == "meter":
                if len(args) != 1 or not args[0].es_compatible_con(tipo_t): raise TipoError(f"Cola.meter(elem) espera {tipo_t}.", span=span)
                return TIPO_VOID

        # Métodos de Dominio: Regla, Hecho, Variable
        if tipo_obj.nombre == "Regla" and not tipo_obj.es_arreglo:
            if metodo == "getVarPremisa":
                return TIPO_VARIABLE
            if metodo == "getNombre":
                return TIPO_STRING

        if tipo_obj.nombre == "Hecho" and not tipo_obj.es_arreglo:
            if metodo == "getVar":
                return TIPO_VARIABLE
            if metodo == "getValorTexto":
                return TIPO_STRING
            if metodo == "getValorNumero":
                return TIPO_DOUBLE
            if metodo == "getValorBooleano":
                return TIPO_BOOLEAN

        if tipo_obj.nombre == "Variable" and not tipo_obj.es_arreglo:
            if metodo == "getNombre":
                return TIPO_STRING

        raise TipoError(f"El método '{metodo}' no existe en el tipo {tipo_obj}.", span=span, codigo="METODO_NO_EXISTE")
