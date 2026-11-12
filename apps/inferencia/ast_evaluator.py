"""
AST Evaluator para expresiones lógicas complejas de premisas de reglas (IF).
Soporta:
- Operadores booleanos: AND (Y, &&), OR (O, ||), NOT (NO, !)
- Agrupación por paréntesis: ( ... )
- Comparaciones atómicas: =, ==, !=, <>, >, <, >=, <=, CONTIENE
- Variables booleanas implícitas (ej: "activo" -> activo = true)
"""
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, Union


class Token:
    def __init__(self, tipo: str, valor: str, posicion: int = 0):
        self.tipo = tipo      # 'AND', 'OR', 'NOT', 'LPAREN', 'RPAREN', 'ATOM'
        self.valor = valor
        self.posicion = posicion

    def __repr__(self):
        return f"Token({self.tipo}, {self.valor!r})"


class ASTNode:
    """Clase base para nodos del árbol sintáctico."""
    def evaluar(self, memoria_trabajo: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        raise NotImplementedError


class AtomNode(ASTNode):
    def __init__(self, variable: str, operador: str, valor_esperado: str):
        self.variable = variable.strip()
        self.operador = operador.strip()
        self.valor_esperado = valor_esperado.strip().strip("'\"")

    def __repr__(self):
        return f"AtomNode({self.variable} {self.operador} {self.valor_esperado})"

    def _buscar_valor_actual(self, memoria_trabajo: Dict[str, Any]) -> Tuple[bool, Any]:
        """Busca la variable en memoria_trabajo de forma insensible a mayúsculas/minúsculas."""
        if self.variable in memoria_trabajo:
            return True, memoria_trabajo[self.variable]
        
        var_lower = self.variable.lower()
        for k, v in memoria_trabajo.items():
            if str(k).lower() == var_lower:
                return True, v
        return False, None

    @staticmethod
    def _normalizar_booleano(valor: Any) -> bool:
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, str):
            return valor.strip().lower() in ("true", "1", "si", "sí", "verdadero")
        if isinstance(valor, (int, float)):
            return bool(valor)
        return False

    def evaluar(self, memoria_trabajo: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        existe, valor_actual = self._buscar_valor_actual(memoria_trabajo)
        
        detalle = {
            "tipo": "ATOM",
            "variable": self.variable,
            "operador": self.operador,
            "valor_esperado": self.valor_esperado,
            "valor_actual": valor_actual if existe else None,
            "definido": existe,
            "resultado": False,
        }

        if not existe or valor_actual is None:
            return False, detalle

        if isinstance(valor_actual, str) and not valor_actual.strip():
            return False, detalle

        op = self.operador
        if op == "==":
            op = "="
        elif op == "<>":
            op = "!="

        # 1. Comparación booleana
        if isinstance(valor_actual, bool) or self.valor_esperado.lower() in (
            "true", "false", "verdadero", "falso", "si", "no"
        ):
            actual_bool = self._normalizar_booleano(valor_actual)
            esperado_bool = self._normalizar_booleano(self.valor_esperado)
            if op == "=":
                res = actual_bool == esperado_bool
            elif op == "!=":
                res = actual_bool != esperado_bool
            else:
                res = False
            detalle["resultado"] = res
            return res, detalle

        # 2. Comparación numérica
        es_numerico = False
        try:
            val_actual_num = Decimal(str(valor_actual))
            val_esperado_num = Decimal(str(self.valor_esperado))
            es_numerico = True
        except (InvalidOperation, ValueError, TypeError):
            es_numerico = False

        if es_numerico:
            if op == "=":
                res = val_actual_num == val_esperado_num
            elif op == "!=":
                res = val_actual_num != val_esperado_num
            elif op == ">":
                res = val_actual_num > val_esperado_num
            elif op == "<":
                res = val_actual_num < val_esperado_num
            elif op == ">=":
                res = val_actual_num >= val_esperado_num
            elif op == "<=":
                res = val_actual_num <= val_esperado_num
            else:
                res = False
            detalle["resultado"] = res
            return res, detalle

        # 3. Comparación textual
        str_actual = str(valor_actual).strip().lower()
        str_esperado = self.valor_esperado.lower()

        if op == "=":
            res = str_actual == str_esperado
        elif op == "!=":
            res = str_actual != str_esperado
        elif op.upper() == "CONTIENE":
            res = str_esperado in str_actual
        else:
            res = False

        detalle["resultado"] = res
        return res, detalle


class NotNode(ASTNode):
    def __init__(self, hijo: ASTNode):
        self.hijo = hijo

    def __repr__(self):
        return f"NotNode({self.hijo})"

    def evaluar(self, memoria_trabajo: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        hijo_res, hijo_det = self.hijo.evaluar(memoria_trabajo)
        res = not hijo_res
        return res, {
            "tipo": "NOT",
            "resultado": res,
            "hijo": hijo_det,
        }


class BinaryOpNode(ASTNode):
    def __init__(self, op: str, izquierda: ASTNode, derecha: ASTNode):
        self.op = op  # 'AND' u 'OR'
        self.izquierda = izquierda
        self.derecha = derecha

    def __repr__(self):
        return f"BinaryOpNode({self.izquierda} {self.op} {self.derecha})"

    def evaluar(self, memoria_trabajo: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        izq_res, izq_det = self.izquierda.evaluar(memoria_trabajo)
        
        # Cortocircuito lógico
        if self.op == "OR":
            if izq_res:
                # Opcionalmente evaluamos derecha para detalle completo
                der_res, der_det = self.derecha.evaluar(memoria_trabajo)
                return True, {
                    "tipo": "OR",
                    "resultado": True,
                    "izquierda": izq_det,
                    "derecha": der_det,
                }
            der_res, der_det = self.derecha.evaluar(memoria_trabajo)
            return der_res, {
                "tipo": "OR",
                "resultado": der_res,
                "izquierda": izq_det,
                "derecha": der_det,
            }
        elif self.op == "AND":
            if not izq_res:
                der_res, der_det = self.derecha.evaluar(memoria_trabajo)
                return False, {
                    "tipo": "AND",
                    "resultado": False,
                    "izquierda": izq_det,
                    "derecha": der_det,
                }
            der_res, der_det = self.derecha.evaluar(memoria_trabajo)
            return der_res, {
                "tipo": "AND",
                "resultado": der_res,
                "izquierda": izq_det,
                "derecha": der_det,
            }
        raise ValueError(f"Operador binario no soportado: {self.op}")


class LogicaPremisasLexer:
    """Tokeniza la expresión lógica de premisas."""
    
    OPERADORES_RELACIONALES = (">=", "<=", "!=", "<>", "==", "=", ">", "<", "CONTIENE")

    @classmethod
    def tokenizar(cls, expresion: str) -> List[Token]:
        tokens: List[Token] = []
        i = 0
        n = len(expresion)

        while i < n:
            ch = expresion[i]

            # Espacios
            if ch.isspace():
                i += 1
                continue

            # Paréntesis
            if ch == "(":
                tokens.append(Token("LPAREN", "(", i))
                i += 1
                continue
            if ch == ")":
                tokens.append(Token("RPAREN", ")", i))
                i += 1
                continue

            # Conectores lógicos por símbolo
            if expresion[i:i+2] == "&&":
                tokens.append(Token("AND", "AND", i))
                i += 2
                continue
            if expresion[i:i+2] == "||":
                tokens.append(Token("OR", "OR", i))
                i += 2
                continue
            if ch == "!":
                # Asegurarse de que no sea !=
                if i + 1 < n and expresion[i+1] == "=":
                    # Es parte de una comparación relacional
                    pass
                else:
                    tokens.append(Token("NOT", "NOT", i))
                    i += 1
                    continue

            # Palabras clave o átomos
            # Busquemos el siguiente segmento hasta un delimitador lógico o paréntesis
            match_word = re.match(r"[A-Za-z_áéíóúÁÉÍÓÚñÑ][\wáéíóúÁÉÍÓÚñÑ]*", expresion[i:])
            if match_word:
                palabra = match_word.group(0)
                palabra_upper = palabra.upper()
                pos_inicio = i
                longitud = len(palabra)

                # Verificar si es un conector lógico reservado
                if palabra_upper in ("AND", "Y"):
                    tokens.append(Token("AND", "AND", pos_inicio))
                    i += longitud
                    continue
                elif palabra_upper in ("OR", "O"):
                    tokens.append(Token("OR", "OR", pos_inicio))
                    i += longitud
                    continue
                elif palabra_upper in ("NOT", "NO"):
                    tokens.append(Token("NOT", "NOT", pos_inicio))
                    i += longitud
                    continue

            # Si no es un operador booleano ni paréntesis, es parte de una condición ATOM.
            # Leemos hasta encontrar el fin del átomo: '(', ')', o un conector booleano ('AND', 'OR', 'Y', 'O', '&&', '||')
            atom_str = ""
            start_i = i
            while i < n:
                # Comprobar delimitadores
                if expresion[i] in ("(", ")"):
                    break
                if expresion[i:i+2] in ("&&", "||"):
                    break

                # Comprobar si la siguiente palabra es AND, OR, Y, O, NOT, NO
                resto = expresion[i:]
                m_op = re.match(r"^\s+(AND|OR|Y|O|NOT|NO)\b", resto, re.IGNORECASE)
                if m_op and len(atom_str.strip()) > 0:
                    break

                atom_str += expresion[i]
                i += 1

            atom_clean = atom_str.strip()
            if atom_clean:
                tokens.append(Token("ATOM", atom_clean, start_i))

        return tokens


class LogicaPremisasParser:
    """
    Parser descendente recursivo:
    Expr   -> OrTerm ('OR' OrTerm)*
    OrTerm -> AndTerm ('AND' AndTerm)*
    AndTerm-> 'NOT' AndTerm | Factor
    Factor -> '(' Expr ')' | ATOM
    """

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def actual(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consumir(self, tipo_esperado: Optional[str] = None) -> Token:
        tok = self.actual()
        if not tok:
            raise ValueError(f"Fin inesperado de expresión al esperar '{tipo_esperado}'")
        if tipo_esperado and tok.tipo != tipo_esperado:
            raise ValueError(
                f"Se esperaba '{tipo_esperado}' en posición {tok.posicion}, pero se encontró '{tok.tipo}' ({tok.valor})"
            )
        self.pos += 1
        return tok

    def parse(self) -> ASTNode:
        nodo = self.parse_expr()
        if self.actual() is not None:
            tok = self.actual()
            raise ValueError(f"Token inesperado '{tok.valor}' en posición {tok.posicion}")
        return nodo

    def parse_expr(self) -> ASTNode:
        nodo = self.parse_or()
        return nodo

    def parse_or(self) -> ASTNode:
        nodo = self.parse_and()
        while self.actual() and self.actual().tipo == "OR":
            self.consumir("OR")
            derecha = self.parse_and()
            nodo = BinaryOpNode("OR", nodo, derecha)
        return nodo

    def parse_and(self) -> ASTNode:
        nodo = self.parse_not()
        while self.actual() and self.actual().tipo == "AND":
            self.consumir("AND")
            derecha = self.parse_not()
            nodo = BinaryOpNode("AND", nodo, derecha)
        return nodo

    def parse_not(self) -> ASTNode:
        if self.actual() and self.actual().tipo == "NOT":
            self.consumir("NOT")
            hijo = self.parse_not()
            return NotNode(hijo)
        return self.parse_factor()

    def parse_factor(self) -> ASTNode:
        tok = self.actual()
        if not tok:
            raise ValueError("Expresión incompleta.")

        if tok.tipo == "LPAREN":
            self.consumir("LPAREN")
            nodo = self.parse_expr()
            self.consumir("RPAREN")
            return nodo

        if tok.tipo == "ATOM":
            self.consumir("ATOM")
            return self._parsear_atom(tok.valor)

        raise ValueError(f"Token inesperado en factor: {tok.tipo} ({tok.valor})")

    @classmethod
    def _parsear_atom(cls, texto: str) -> AtomNode:
        # Buscar operadores relacionales en orden de longitud descendente
        ops = [">=", "<=", "!=", "<>", "==", "=", ">", "<", "CONTIENE", "contiene"]
        for op in ops:
            pattern = rf"(?i)^(.+?)\s*({re.escape(op)})\s*(.+)$"
            m = re.match(pattern, texto)
            if m:
                var = m.group(1).strip()
                operador = m.group(2).strip().upper()
                valor = m.group(3).strip()
                return AtomNode(var, operador, valor)

        # Si no hay operador explícito, asumimos variable booleana = true
        return AtomNode(texto.strip(), "=", "true")


def compilar_expresion(expresion: str) -> ASTNode:
    """Tokeniza y genera el AST de la expresión lógica."""
    tokens = LogicaPremisasLexer.tokenizar(expresion)
    if not tokens:
        raise ValueError("La expresión lógica está vacía.")
    parser = LogicaPremisasParser(tokens)
    return parser.parse()


def evaluar_expresion_logica(
    expresion: Union[str, ASTNode],
    memoria_trabajo: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    """
    Evalúa una expresión lógica de premisas (AND, OR, NOT, paréntesis, operadores relacionales)
    frente a la memoria de trabajo dada.
    Retorna: (cumple: bool, detalle: Dict)
    """
    if isinstance(expresion, str):
        ast = compilar_expresion(expresion)
    else:
        ast = expresion
    return ast.evaluar(memoria_trabajo)

