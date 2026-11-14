from dataclasses import dataclass, field
from typing import Dict, List, Optional
from ..exceptions import SourceSpan
from ..runtime.instructions import Instruction, OpCode
from .ast_nodes import (
    ProgramNode, FunctionDefNode, StmtNode, BlockStmtNode, VarDeclStmtNode,
    AssignmentStmtNode, UpdateStmtNode, ExpressionStmtNode, IfStmtNode,
    WhileStmtNode, ForStmtNode, ReturnStmtNode, BreakStmtNode, ContinueStmtNode,
    ExprNode, LiteralExprNode, IdentifierExprNode, UnaryExprNode,
    BinaryExprNode, CallExprNode, MemberAccessExprNode, IndexExprNode,
    NewArrayExprNode, NewCollectionExprNode
)


@dataclass
class CompiledFunction:
    nombre: str
    parametros: List[str]
    instrucciones: List[Instruction] = field(default_factory=list)


@dataclass
class CompiledProgram:
    funciones: Dict[str, CompiledFunction] = field(default_factory=dict)
    entrada_principal: str = "FWC"

    def to_dict(self) -> dict:
        return {
            "entrada_principal": self.entrada_principal,
            "funciones": {
                k: {
                    "nombre": f.nombre,
                    "parametros": f.parametros,
                    "instrucciones": [inst.to_dict() for inst in f.instrucciones],
                }
                for k, f in self.funciones.items()
            }
        }


class Compiler:
    def __init__(self, programa: ProgramNode):
        self.programa = programa
        self.instrucciones: List[Instruction] = []
        self.pila_bucles: List[dict] = []  # para resolver break y continue: list of {'breaks': [], 'continues': [], 'start_pc': int}

    def compilar(self, entrada_principal: str = "FWC") -> CompiledProgram:
        resultado = CompiledProgram(entrada_principal=entrada_principal)

        for func in self.programa.funciones:
            self.instrucciones = []
            self.pila_bucles = []

            # Compilar cuerpo de la función
            self._compilar_bloque(func.cuerpo)

            # Si la última instrucción no es RETURN, agregar RETURN void implícito
            if not self.instrucciones or self.instrucciones[-1].op != OpCode.RETURN:
                self._emitir(OpCode.RETURN, False, func.span)

            parametros = [p.nombre for p in func.parametros]
            resultado.funciones[func.nombre] = CompiledFunction(
                nombre=func.nombre,
                parametros=parametros,
                instrucciones=self.instrucciones
            )

        return resultado

    def _emitir(self, op: OpCode, arg=None, span: Optional[SourceSpan] = None) -> int:
        idx = len(self.instrucciones)
        self.instrucciones.append(Instruction(op=op, arg=arg, span=span))
        return idx

    def _parchar_salto(self, idx: int, destino: int):
        self.instrucciones[idx].arg = destino

    def _compilar_bloque(self, bloque: BlockStmtNode):
        for stmt in bloque.sentencias:
            self._compilar_sentencia(stmt)

    def _compilar_sentencia(self, stmt: StmtNode):
        # Marcar paso visible de sentencia para el depurador
        self._emitir(OpCode.LINE_STEP, span=stmt.span)

        if isinstance(stmt, BlockStmtNode):
            self._compilar_bloque(stmt)

        elif isinstance(stmt, VarDeclStmtNode):
            if stmt.inicializador:
                self._compilar_expresion(stmt.inicializador)
            else:
                self._emitir(OpCode.CONST, None, stmt.span)
            self._emitir(OpCode.STORE_VAR, stmt.nombre, stmt.span)

        elif isinstance(stmt, AssignmentStmtNode):
            # Caso 1: Destino es variable simple
            if isinstance(stmt.destino, IdentifierExprNode):
                self._compilar_expresion(stmt.valor)
                self._emitir(OpCode.STORE_VAR, stmt.destino.nombre, stmt.span)
            # Caso 2: Destino es acceso por corchetes arr[i] = val
            elif isinstance(stmt.destino, IndexExprNode):
                self._compilar_expresion(stmt.destino.coleccion)
                self._compilar_expresion(stmt.destino.indice)
                self._compilar_expresion(stmt.valor)
                self._emitir(OpCode.STORE_INDEX, None, stmt.span)
            # Caso 3: Destino es acceso a miembro obj.prop = val
            elif isinstance(stmt.destino, MemberAccessExprNode):
                self._compilar_expresion(stmt.destino.objeto)
                self._compilar_expresion(stmt.valor)
                self._emitir(OpCode.STORE_MEMBER, stmt.destino.miembro, stmt.span)

        elif isinstance(stmt, UpdateStmtNode):
            if isinstance(stmt.destino, IdentifierExprNode):
                self._emitir(OpCode.UPDATE_VAR, (stmt.destino.nombre, stmt.es_incremento), stmt.span)

        elif isinstance(stmt, ExpressionStmtNode):
            self._compilar_expresion(stmt.expresion)
            self._emitir(OpCode.POP, None, stmt.span)

        elif isinstance(stmt, IfStmtNode):
            self._compilar_expresion(stmt.condicion)
            jump_false_idx = self._emitir(OpCode.JUMP_IF_FALSE, 0, stmt.condicion.span)

            self._compilar_sentencia(stmt.rama_then)

            if stmt.rama_else:
                jump_fin_idx = self._emitir(OpCode.JUMP, 0, stmt.span)
                destino_else = len(self.instrucciones)
                self._parchar_salto(jump_false_idx, destino_else)

                self._compilar_sentencia(stmt.rama_else)
                destino_fin = len(self.instrucciones)
                self._parchar_salto(jump_fin_idx, destino_fin)
            else:
                destino_fin = len(self.instrucciones)
                self._parchar_salto(jump_false_idx, destino_fin)

        elif isinstance(stmt, WhileStmtNode):
            inicio_bucle = len(self.instrucciones)
            bucle_info = {"breaks": [], "continues": [], "start_pc": inicio_bucle}
            self.pila_bucles.append(bucle_info)

            self._compilar_expresion(stmt.condicion)
            jump_false_idx = self._emitir(OpCode.JUMP_IF_FALSE, 0, stmt.condicion.span)

            self._compilar_sentencia(stmt.cuerpo)
            self._emitir(OpCode.JUMP, inicio_bucle, stmt.span)

            fin_bucle = len(self.instrucciones)
            self._parchar_salto(jump_false_idx, fin_bucle)

            # Parchar breaks y continues
            for b_idx in bucle_info["breaks"]:
                self._parchar_salto(b_idx, fin_bucle)
            for c_idx in bucle_info["continues"]:
                self._parchar_salto(c_idx, inicio_bucle)

            self.pila_bucles.pop()

        elif isinstance(stmt, ForStmtNode):
            # Inicialización
            if stmt.inicializacion:
                self._compilar_sentencia(stmt.inicializacion)

            inicio_cond = len(self.instrucciones)
            jump_false_idx = None
            if stmt.condicion:
                self._compilar_expresion(stmt.condicion)
                jump_false_idx = self._emitir(OpCode.JUMP_IF_FALSE, 0, stmt.condicion.span)

            # Para continue en for, se debe saltar a la cláusula de actualización
            bucle_info = {"breaks": [], "continues": [], "start_pc": inicio_cond}
            self.pila_bucles.append(bucle_info)

            # Cuerpo
            self._compilar_sentencia(stmt.cuerpo)

            # Punto de actualización (destino de continue)
            punto_actualizacion = len(self.instrucciones)
            for c_idx in bucle_info["continues"]:
                self._parchar_salto(c_idx, punto_actualizacion)

            if stmt.actualizacion:
                self._compilar_sentencia(stmt.actualizacion)

            self._emitir(OpCode.JUMP, inicio_cond, stmt.span)

            fin_for = len(self.instrucciones)
            if jump_false_idx is not None:
                self._parchar_salto(jump_false_idx, fin_for)
            for b_idx in bucle_info["breaks"]:
                self._parchar_salto(b_idx, fin_for)

            self.pila_bucles.pop()

        elif isinstance(stmt, BreakStmtNode):
            idx = self._emitir(OpCode.JUMP, 0, stmt.span)
            self.pila_bucles[-1]["breaks"].append(idx)

        elif isinstance(stmt, ContinueStmtNode):
            idx = self._emitir(OpCode.JUMP, 0, stmt.span)
            self.pila_bucles[-1]["continues"].append(idx)

        elif isinstance(stmt, ReturnStmtNode):
            if stmt.valor:
                self._compilar_expresion(stmt.valor)
                self._emitir(OpCode.RETURN, True, stmt.span)
            else:
                self._emitir(OpCode.RETURN, False, stmt.span)

    def _compilar_expresion(self, expr: ExprNode):
        if isinstance(expr, LiteralExprNode):
            self._emitir(OpCode.CONST, expr.valor, expr.span)

        elif isinstance(expr, IdentifierExprNode):
            self._emitir(OpCode.LOAD_VAR, expr.nombre, expr.span)

        elif isinstance(expr, UnaryExprNode):
            self._compilar_expresion(expr.operando)
            self._emitir(OpCode.UNARY_OP, expr.operador, expr.span)

        elif isinstance(expr, BinaryExprNode):
            # Cortocircuito para && y ||
            if expr.operador == "&&":
                self._compilar_expresion(expr.izquierda)
                self._emitir(OpCode.DUP, span=expr.span)
                jump_false = self._emitir(OpCode.JUMP_IF_FALSE, 0, expr.span)
                self._emitir(OpCode.POP, span=expr.span)
                self._compilar_expresion(expr.derecha)
                self._parchar_salto(jump_false, len(self.instrucciones))
            elif expr.operador == "||":
                self._compilar_expresion(expr.izquierda)
                self._emitir(OpCode.DUP, span=expr.span)
                jump_true = self._emitir(OpCode.JUMP_IF_TRUE, 0, expr.span)
                self._emitir(OpCode.POP, span=expr.span)
                self._compilar_expresion(expr.derecha)
                self._parchar_salto(jump_true, len(self.instrucciones))
            else:
                self._compilar_expresion(expr.izquierda)
                self._compilar_expresion(expr.derecha)
                self._emitir(OpCode.BINARY_OP, expr.operador, expr.span)

        elif isinstance(expr, MemberAccessExprNode):
            self._compilar_expresion(expr.objeto)
            self._emitir(OpCode.LOAD_MEMBER, expr.miembro, expr.span)

        elif isinstance(expr, IndexExprNode):
            self._compilar_expresion(expr.coleccion)
            self._compilar_expresion(expr.indice)
            self._emitir(OpCode.LOAD_INDEX, None, expr.span)

        elif isinstance(expr, CallExprNode):
            if isinstance(expr.callee, MemberAccessExprNode):
                # Llamada a método: obj.metodo(args)
                self._compilar_expresion(expr.callee.objeto)
                for arg in expr.argumentos:
                    self._compilar_expresion(arg)
                self._emitir(OpCode.CALL_METHOD, (expr.callee.miembro, len(expr.argumentos)), expr.span)
            elif isinstance(expr.callee, IdentifierExprNode):
                # Llamada a función: func(args)
                for arg in expr.argumentos:
                    self._compilar_expresion(arg)
                self._emitir(OpCode.CALL, (expr.callee.nombre, len(expr.argumentos)), expr.span)

        elif isinstance(expr, NewArrayExprNode):
            self._compilar_expresion(expr.tamano)
            self._emitir(OpCode.NEW_ARRAY, expr.tipo_elemento.nombre_base, expr.span)

        elif isinstance(expr, NewCollectionExprNode):
            self._emitir(OpCode.NEW_COLLECTION, (expr.tipo_coleccion, expr.parametro_tipo.nombre_base), expr.span)

