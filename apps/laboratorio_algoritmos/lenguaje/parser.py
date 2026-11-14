from typing import List, Optional, Set
from ..exceptions import SourceSpan, SintaxisError
from .tokens import Token, TokenType
from .ast_nodes import (
    ProgramNode, FunctionDefNode, ParamNode, TypeNode,
    StmtNode, BlockStmtNode, VarDeclStmtNode, AssignmentStmtNode, UpdateStmtNode,
    ExpressionStmtNode, IfStmtNode, WhileStmtNode, ForStmtNode,
    ReturnStmtNode, BreakStmtNode, ContinueStmtNode,
    ExprNode, LiteralExprNode, IdentifierExprNode, UnaryExprNode,
    BinaryExprNode, CallExprNode, MemberAccessExprNode, IndexExprNode,
    NewArrayExprNode, NewCollectionExprNode
)

# Precedencias para Pratt Parser
PREC_NONE = 0
PREC_OR = 1           # ||
PREC_AND = 2          # &&
PREC_EQUALITY = 3     # ==, !=
PREC_COMPARISON = 4   # <, <=, >, >=
PREC_TERM = 5         # +, -
PREC_FACTOR = 6       # *, /, %
PREC_UNARY = 7        # !, -
PREC_CALL = 8         # ., (), []


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.actual = 0
        self.nombres_funciones: Set[str] = set()

    def parsear(self) -> ProgramNode:
        span_inicio = self._token_actual().span
        funciones: List[FunctionDefNode] = []

        while not self._es_fin():
            func = self._parsear_declaracion_funcion()
            funciones.append(func)

        span_fin = self._token_anterior().span if self.actual > 0 else span_inicio
        span_programa = SourceSpan(
            span_inicio.line,
            span_inicio.column,
            span_inicio.offset_start,
            span_fin.offset_end
        )
        return ProgramNode(span=span_programa, funciones=funciones)

    # ----------------------------------------------------
    # Funciones y Tipos
    # ----------------------------------------------------
    def _parsear_declaracion_funcion(self) -> FunctionDefNode:
        span_inicio = self._token_actual().span
        tipo_retorno = self._parsear_tipo()

        token_nombre = self._consumir(TokenType.IDENTIFIER, "Se esperaba el nombre de la función.")
        nombre_func = token_nombre.lexema

        if nombre_func in self.nombres_funciones:
            raise SintaxisError(
                f"Función duplicada: '{nombre_func}'. No se admiten sobrecargas.",
                span=token_nombre.span,
                codigo="SOBRECARGA_NO_PERMITIDA"
            )
        self.nombres_funciones.add(nombre_func)

        self._consumir(TokenType.LPAREN, "Se esperaba '(' después del nombre de la función.")
        parametros: List[ParamNode] = []

        if not self._comprobar(TokenType.RPAREN):
            while True:
                param = self._parsear_parametro()
                parametros.append(param)
                if not self._coincide(TokenType.COMMA):
                    break

        self._consumir(TokenType.RPAREN, "Se esperaba ')' después de los parámetros.")
        cuerpo = self._parsear_bloque()

        span_total = SourceSpan(
            span_inicio.line,
            span_inicio.column,
            span_inicio.offset_start,
            cuerpo.span.offset_end
        )
        return FunctionDefNode(
            span=span_total,
            tipo_retorno=tipo_retorno,
            nombre=nombre_func,
            parametros=parametros,
            cuerpo=cuerpo
        )

    def _parsear_parametro(self) -> ParamNode:
        span_inicio = self._token_actual().span
        tipo = self._parsear_tipo()
        token_nombre = self._consumir(TokenType.IDENTIFIER, "Se esperaba el nombre del parámetro.")
        span_total = SourceSpan(
            span_inicio.line,
            span_inicio.column,
            span_inicio.offset_start,
            token_nombre.span.offset_end
        )
        return ParamNode(span=span_total, tipo=tipo, nombre=token_nombre.lexema)

    def _parsear_tipo(self) -> TypeNode:
        token = self._avanzar()
        span_inicio = token.span
        nombre_base = token.lexema
        parametro_tipo: Optional[TypeNode] = None

        if token.tipo not in (
            TokenType.KW_INT, TokenType.KW_DOUBLE, TokenType.KW_BOOLEAN,
            TokenType.KW_STRING, TokenType.KW_VOID, TokenType.KW_REGLA,
            TokenType.KW_VARIABLE, TokenType.KW_HECHO, TokenType.KW_BASE_HECHOS,
            TokenType.KW_LISTA, TokenType.KW_PILA, TokenType.KW_COLA
        ):
            raise SintaxisError(
                f"Tipo de dato desconocido: '{token.lexema}'",
                span=token.span,
                codigo="TIPO_DESCONOCIDO"
            )

        # Genéricos: Lista<T>, Pila<T>, Cola<T>
        if token.tipo in (TokenType.KW_LISTA, TokenType.KW_PILA, TokenType.KW_COLA):
            if self._coincide(TokenType.LESS):
                parametro_tipo = self._parsear_tipo()
                self._consumir(TokenType.GREATER, "Se esperaba '>' al cerrar tipo genérico.")

        # Arreglos: T[]
        es_arreglo = False
        span_fin = token.span
        if self._coincide(TokenType.LBRACKET):
            self._consumir(TokenType.RBRACKET, "Se esperaba ']' en declaración de arreglo.")
            es_arreglo = True
            span_fin = self._token_anterior().span

        span_total = SourceSpan(
            span_inicio.line,
            span_inicio.column,
            span_inicio.offset_start,
            span_fin.offset_end
        )
        return TypeNode(
            span=span_total,
            nombre_base=nombre_base,
            es_arreglo=es_arreglo,
            parametro_tipo=parametro_tipo
        )

    # ----------------------------------------------------
    # Sentencias
    # ----------------------------------------------------
    def _parsear_sentencia(self) -> StmtNode:
        if self._coincide(TokenType.LBRACE):
            return self._parsear_bloque_con_llave_abierta()
        if self._coincide(TokenType.KW_IF):
            return self._parsear_if()
        if self._coincide(TokenType.KW_WHILE):
            return self._parsear_while()
        if self._coincide(TokenType.KW_FOR):
            return self._parsear_for()
        if self._coincide(TokenType.KW_RETURN):
            return self._parsear_return()
        if self._coincide(TokenType.KW_BREAK):
            return self._parsear_break()
        if self._coincide(TokenType.KW_CONTINUE):
            return self._parsear_continue()

        # Comprobar si es declaración de variable
        if self._es_inicio_de_tipo():
            return self._parsear_declaracion_variable()

        return self._parsear_sentencia_expresion_o_asignacion()

    def _parsear_bloque(self) -> BlockStmtNode:
        span_inicio = self._consumir(TokenType.LBRACE, "Se esperaba '{' para iniciar bloque.").span
        return self._parsear_bloque_con_llave_abierta(span_inicio)

    def _parsear_bloque_con_llave_abierta(self, span_inicio: Optional[SourceSpan] = None) -> BlockStmtNode:
        if not span_inicio:
            span_inicio = self._token_anterior().span
        sentencias: List[StmtNode] = []

        while not self._comprobar(TokenType.RBRACE) and not self._es_fin():
            sentencias.append(self._parsear_sentencia())

        token_cierre = self._consumir(TokenType.RBRACE, "Se esperaba '}' para cerrar bloque.")
        span_total = SourceSpan(
            span_inicio.line,
            span_inicio.column,
            span_inicio.offset_start,
            token_cierre.span.offset_end
        )
        return BlockStmtNode(span=span_total, sentencias=sentencias)

    def _es_inicio_de_tipo(self) -> bool:
        t = self._token_actual().tipo
        return t in (
            TokenType.KW_INT, TokenType.KW_DOUBLE, TokenType.KW_BOOLEAN,
            TokenType.KW_STRING, TokenType.KW_REGLA, TokenType.KW_VARIABLE,
            TokenType.KW_HECHO, TokenType.KW_BASE_HECHOS,
            TokenType.KW_LISTA, TokenType.KW_PILA, TokenType.KW_COLA
        )

    def _parsear_declaracion_variable(self) -> VarDeclStmtNode:
        span_inicio = self._token_actual().span
        tipo = self._parsear_tipo()
        token_nombre = self._consumir(TokenType.IDENTIFIER, "Se esperaba el nombre de la variable.")
        inicializador: Optional[ExprNode] = None

        if self._coincide(TokenType.ASSIGN):
            inicializador = self._parsear_expresion()

        token_semicolon = self._consumir(TokenType.SEMICOLON, "Se esperaba ';' al final de la declaración.")
        span_total = SourceSpan(
            span_inicio.line,
            span_inicio.column,
            span_inicio.offset_start,
            token_semicolon.span.offset_end
        )
        return VarDeclStmtNode(
            span=span_total,
            tipo=tipo,
            nombre=token_nombre.lexema,
            inicializador=inicializador
        )

    def _parsear_sentencia_expresion_o_asignacion(self) -> StmtNode:
        expr = self._parsear_expresion()

        # Asignación simple: destino = valor;
        if self._coincide(TokenType.ASSIGN):
            valor = self._parsear_expresion()
            token_semi = self._consumir(TokenType.SEMICOLON, "Se esperaba ';' después de la asignación.")
            span_total = SourceSpan(
                expr.span.line,
                expr.span.column,
                expr.span.offset_start,
                token_semi.span.offset_end
            )
            return AssignmentStmtNode(span=span_total, destino=expr, valor=valor)

        # Actualización i++ o i--
        if self._coincide(TokenType.INCREMENT):
            token_semi = self._consumir(TokenType.SEMICOLON, "Se esperaba ';' después de '++'.")
            span_total = SourceSpan(
                expr.span.line,
                expr.span.column,
                expr.span.offset_start,
                token_semi.span.offset_end
            )
            return UpdateStmtNode(span=span_total, destino=expr, es_incremento=True)

        if self._coincide(TokenType.DECREMENT):
            token_semi = self._consumir(TokenType.SEMICOLON, "Se esperaba ';' después de '--'.")
            span_total = SourceSpan(
                expr.span.line,
                expr.span.column,
                expr.span.offset_start,
                token_semi.span.offset_end
            )
            return UpdateStmtNode(span=span_total, destino=expr, es_incremento=False)

        token_semi = self._consumir(TokenType.SEMICOLON, "Se esperaba ';' al final de la instrucción.")
        span_total = SourceSpan(
            expr.span.line,
            expr.span.column,
            expr.span.offset_start,
            token_semi.span.offset_end
        )
        return ExpressionStmtNode(span=span_total, expresion=expr)

    def _parsear_if(self) -> IfStmtNode:
        span_inicio = self._token_anterior().span
        self._consumir(TokenType.LPAREN, "Se esperaba '(' después de 'if'.")
        condicion = self._parsear_expresion()
        self._consumir(TokenType.RPAREN, "Se esperaba ')' después de la condición del if.")

        rama_then = self._parsear_sentencia()
        rama_else: Optional[StmtNode] = None

        if self._coincide(TokenType.KW_ELSE):
            rama_else = self._parsear_sentencia()

        span_fin = rama_else.span if rama_else else rama_then.span
        span_total = SourceSpan(
            span_inicio.line,
            span_inicio.column,
            span_inicio.offset_start,
            span_fin.offset_end
        )
        return IfStmtNode(
            span=span_total,
            condicion=condicion,
            rama_then=rama_then,
            rama_else=rama_else
        )

    def _parsear_while(self) -> WhileStmtNode:
        span_inicio = self._token_anterior().span
        self._consumir(TokenType.LPAREN, "Se esperaba '(' después de 'while'.")
        condicion = self._parsear_expresion()
        self._consumir(TokenType.RPAREN, "Se esperaba ')' después de la condición del while.")

        cuerpo = self._parsear_sentencia()
        span_total = SourceSpan(
            span_inicio.line,
            span_inicio.column,
            span_inicio.offset_start,
            cuerpo.span.offset_end
        )
        return WhileStmtNode(span=span_total, condicion=condicion, cuerpo=cuerpo)

    def _parsear_for(self) -> ForStmtNode:
        span_inicio = self._token_anterior().span
        self._consumir(TokenType.LPAREN, "Se esperaba '(' después de 'for'.")

        # Cláusula 1: Inicialización
        inicializacion: Optional[StmtNode] = None
        if not self._comprobar(TokenType.SEMICOLON):
            if self._es_inicio_de_tipo():
                inicializacion = self._parsear_declaracion_variable()
            else:
                expr = self._parsear_expresion()
                if self._coincide(TokenType.ASSIGN):
                    val = self._parsear_expresion()
                    token_semi = self._consumir(TokenType.SEMICOLON, "Se esperaba ';' en for.")
                    span_asig = SourceSpan(expr.span.line, expr.span.column, expr.span.offset_start, token_semi.span.offset_end)
                    inicializacion = AssignmentStmtNode(span=span_asig, destino=expr, valor=val)
                else:
                    token_semi = self._consumir(TokenType.SEMICOLON, "Se esperaba ';' en for.")
                    span_exp = SourceSpan(expr.span.line, expr.span.column, expr.span.offset_start, token_semi.span.offset_end)
                    inicializacion = ExpressionStmtNode(span=span_exp, expresion=expr)
        else:
            self._consumir(TokenType.SEMICOLON, "Se esperaba ';'.")

        # Cláusula 2: Condición
        condicion: Optional[ExprNode] = None
        if not self._comprobar(TokenType.SEMICOLON):
            condicion = self._parsear_expresion()
        self._consumir(TokenType.SEMICOLON, "Se esperaba ';' después de condición de for.")

        # Cláusula 3: Actualización
        actualizacion: Optional[StmtNode] = None
        if not self._comprobar(TokenType.RPAREN):
            expr_act = self._parsear_expresion()
            if self._coincide(TokenType.INCREMENT):
                span_act = SourceSpan(expr_act.span.line, expr_act.span.column, expr_act.span.offset_start, self._token_anterior().span.offset_end)
                actualizacion = UpdateStmtNode(span=span_act, destino=expr_act, es_incremento=True)
            elif self._coincide(TokenType.DECREMENT):
                span_act = SourceSpan(expr_act.span.line, expr_act.span.column, expr_act.span.offset_start, self._token_anterior().span.offset_end)
                actualizacion = UpdateStmtNode(span=span_act, destino=expr_act, es_incremento=False)
            elif self._coincide(TokenType.ASSIGN):
                val_act = self._parsear_expresion()
                span_act = SourceSpan(expr_act.span.line, expr_act.span.column, expr_act.span.offset_start, val_act.span.offset_end)
                actualizacion = AssignmentStmtNode(span=span_act, destino=expr_act, valor=val_act)
            else:
                actualizacion = ExpressionStmtNode(span=expr_act.span, expresion=expr_act)

        self._consumir(TokenType.RPAREN, "Se esperaba ')' al cerrar encabezado de for.")
        cuerpo = self._parsear_sentencia()

        span_total = SourceSpan(
            span_inicio.line,
            span_inicio.column,
            span_inicio.offset_start,
            cuerpo.span.offset_end
        )
        return ForStmtNode(
            span=span_total,
            inicializacion=inicializacion,
            condicion=condicion,
            actualizacion=actualizacion,
            cuerpo=cuerpo
        )

    def _parsear_return(self) -> ReturnStmtNode:
        span_inicio = self._token_anterior().span
        valor: Optional[ExprNode] = None
        if not self._comprobar(TokenType.SEMICOLON):
            valor = self._parsear_expresion()
        token_semi = self._consumir(TokenType.SEMICOLON, "Se esperaba ';' después de 'return'.")
        span_total = SourceSpan(
            span_inicio.line,
            span_inicio.column,
            span_inicio.offset_start,
            token_semi.span.offset_end
        )
        return ReturnStmtNode(span=span_total, valor=valor)

    def _parsear_break(self) -> BreakStmtNode:
        span_inicio = self._token_anterior().span
        token_semi = self._consumir(TokenType.SEMICOLON, "Se esperaba ';' después de 'break'.")
        return BreakStmtNode(span=SourceSpan(span_inicio.line, span_inicio.column, span_inicio.offset_start, token_semi.span.offset_end))

    def _parsear_continue(self) -> ContinueStmtNode:
        span_inicio = self._token_anterior().span
        token_semi = self._consumir(TokenType.SEMICOLON, "Se esperaba ';' después de 'continue'.")
        return ContinueStmtNode(span=SourceSpan(span_inicio.line, span_inicio.column, span_inicio.offset_start, token_semi.span.offset_end))

    # ----------------------------------------------------
    # Expresiones (Pratt Parsing)
    # ----------------------------------------------------
    def _parsear_expresion(self) -> ExprNode:
        return self._parsear_expresion_con_precedencia(PREC_NONE)

    def _parsear_expresion_con_precedencia(self, precedencia: int) -> ExprNode:
        token = self._avanzar()
        izquierda = self._parsear_prefijo(token)

        while precedencia < self._obtener_precedencia(self._token_actual().tipo):
            token_op = self._avanzar()
            izquierda = self._parsear_infijo(izquierda, token_op)

        return izquierda

    def _parsear_prefijo(self, token: Token) -> ExprNode:
        if token.tipo in (TokenType.INT_LITERAL, TokenType.DOUBLE_LITERAL,
                          TokenType.STRING_LITERAL, TokenType.BOOLEAN_LITERAL):
            tipo_map = {
                TokenType.INT_LITERAL: "int",
                TokenType.DOUBLE_LITERAL: "double",
                TokenType.STRING_LITERAL: "String",
                TokenType.BOOLEAN_LITERAL: "boolean",
            }
            return LiteralExprNode(span=token.span, valor=token.valor, tipo_literal=tipo_map[token.tipo])

        if token.tipo == TokenType.KW_NULL:
            return LiteralExprNode(span=token.span, valor=None, tipo_literal="null")

        if token.tipo == TokenType.IDENTIFIER:
            return IdentifierExprNode(span=token.span, nombre=token.lexema)

        if token.tipo in (TokenType.BANG, TokenType.MINUS):
            operador = token.lexema
            operando = self._parsear_expresion_con_precedencia(PREC_UNARY)
            span_total = SourceSpan(
                token.span.line,
                token.span.column,
                token.span.offset_start,
                operando.span.offset_end
            )
            return UnaryExprNode(span=span_total, operador=operador, operando=operando)

        if token.tipo == TokenType.LPAREN:
            expr = self._parsear_expresion()
            token_cierre = self._consumir(TokenType.RPAREN, "Se esperaba ')' después de la expresión.")
            span_total = SourceSpan(
                token.span.line,
                token.span.column,
                token.span.offset_start,
                token_cierre.span.offset_end
            )
            expr.span = span_total
            return expr

        if token.tipo == TokenType.KW_NEW:
            return self._parsear_new(token.span)

        raise SintaxisError(
            f"Expresión inesperada: '{token.lexema}'",
            span=token.span,
            codigo="EXPRESION_INVALIDA"
        )

    def _parsear_new(self, span_inicio: SourceSpan) -> ExprNode:
        token_tipo = self._avanzar()

        # new T[tamano]
        if self._coincide(TokenType.LBRACKET):
            tamano_expr = self._parsear_expresion()
            token_cierre = self._consumir(TokenType.RBRACKET, "Se esperaba ']' en 'new T[...]'.")
            tipo_elem = TypeNode(
                span=token_tipo.span,
                nombre_base=token_tipo.lexema,
                es_arreglo=False
            )
            span_total = SourceSpan(span_inicio.line, span_inicio.column, span_inicio.offset_start, token_cierre.span.offset_end)
            return NewArrayExprNode(span=span_total, tipo_elemento=tipo_elem, tamano=tamano_expr)

        # new Lista<T>(), new Pila<T>(), new Cola<T>()
        if token_tipo.tipo in (TokenType.KW_LISTA, TokenType.KW_PILA, TokenType.KW_COLA):
            self._consumir(TokenType.LESS, "Se esperaba '<' en 'new Coleccion<T>()'.")
            param_tipo = self._parsear_tipo()
            self._consumir(TokenType.GREATER, "Se esperaba '>' en 'new Coleccion<T>()'.")
            self._consumir(TokenType.LPAREN, "Se esperaba '(' en llamada de constructor.")
            token_cierre = self._consumir(TokenType.RPAREN, "Se esperaba ')' en llamada de constructor.")
            span_total = SourceSpan(span_inicio.line, span_inicio.column, span_inicio.offset_start, token_cierre.span.offset_end)
            return NewCollectionExprNode(span=span_total, tipo_coleccion=token_tipo.lexema, parametro_tipo=param_tipo)

        raise SintaxisError(
            f"Instanciación con 'new' no soportada para: '{token_tipo.lexema}'",
            span=token_tipo.span,
            codigo="NEW_INVALIDO"
        )

    def _parsear_infijo(self, izquierda: ExprNode, token_op: Token) -> ExprNode:
        # Llamada a función: expr(args)
        if token_op.tipo == TokenType.LPAREN:
            argumentos: List[ExprNode] = []
            if not self._comprobar(TokenType.RPAREN):
                while True:
                    argumentos.append(self._parsear_expresion())
                    if not self._coincide(TokenType.COMMA):
                        break
            token_cierre = self._consumir(TokenType.RPAREN, "Se esperaba ')' después de los argumentos.")
            span_total = SourceSpan(
                izquierda.span.line,
                izquierda.span.column,
                izquierda.span.offset_start,
                token_cierre.span.offset_end
            )
            return CallExprNode(span=span_total, callee=izquierda, argumentos=argumentos)

        # Acceso a miembros: expr.miembro
        if token_op.tipo == TokenType.DOT:
            token_miembro = self._consumir(TokenType.IDENTIFIER, "Se esperaba nombre de miembro tras '.'.")
            span_total = SourceSpan(
                izquierda.span.line,
                izquierda.span.column,
                izquierda.span.offset_start,
                token_miembro.span.offset_end
            )
            return MemberAccessExprNode(span=span_total, objeto=izquierda, miembro=token_miembro.lexema)

        # Acceso a índice: expr[index]
        if token_op.tipo == TokenType.LBRACKET:
            indice_expr = self._parsear_expresion()
            token_cierre = self._consumir(TokenType.RBRACKET, "Se esperaba ']' tras índice.")
            span_total = SourceSpan(
                izquierda.span.line,
                izquierda.span.column,
                izquierda.span.offset_start,
                token_cierre.span.offset_end
            )
            return IndexExprNode(span=span_total, coleccion=izquierda, indice=indice_expr)

        # Operadores binarios
        prec = self._obtener_precedencia(token_op.tipo)
        derecha = self._parsear_expresion_con_precedencia(prec)
        span_total = SourceSpan(
            izquierda.span.line,
            izquierda.span.column,
            izquierda.span.offset_start,
            derecha.span.offset_end
        )
        return BinaryExprNode(span=span_total, izquierda=izquierda, operador=token_op.lexema, derecha=derecha)

    def _obtener_precedencia(self, tipo: TokenType) -> int:
        if tipo == TokenType.OR_OR:
            return PREC_OR
        if tipo == TokenType.AND_AND:
            return PREC_AND
        if tipo in (TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
            return PREC_EQUALITY
        if tipo in (TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL):
            return PREC_COMPARISON
        if tipo in (TokenType.PLUS, TokenType.MINUS):
            return PREC_TERM
        if tipo in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            return PREC_FACTOR
        if tipo in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.DOT):
            return PREC_CALL
        return PREC_NONE

    # ----------------------------------------------------
    # Utilidades
    # ----------------------------------------------------
    def _token_actual(self) -> Token:
        return self.tokens[self.actual]

    def _token_anterior(self) -> Token:
        return self.tokens[self.actual - 1]

    def _es_fin(self) -> bool:
        return self._token_actual().tipo == TokenType.EOF

    def _comprobar(self, tipo: TokenType) -> bool:
        if self._es_fin():
            return False
        return self._token_actual().tipo == tipo

    def _coincide(self, *tipos: TokenType) -> bool:
        for t in tipos:
            if self._comprobar(t):
                self._avanzar()
                return True
        return False

    def _avanzar(self) -> Token:
        if not self._es_fin():
            self.actual += 1
        return self._token_anterior()

    def _consumir(self, tipo: TokenType, mensaje: str) -> Token:
        if self._comprobar(tipo):
            return self._avanzar()
        actual = self._token_actual()
        raise SintaxisError(
            f"{mensaje} (se encontró '{actual.lexema}')",
            span=actual.span,
            codigo="TOKEN_INESPERADO"
        )

