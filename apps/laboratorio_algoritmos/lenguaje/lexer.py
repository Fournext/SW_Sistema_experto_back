from typing import List, Optional
from ..exceptions import SourceSpan, SintaxisError
from .tokens import Token, TokenType, PALABRAS_CLAVE


class Lexer:
    def __init__(self, fuente: str, max_tokens: int = 20000):
        # Normalizar a LF
        self.fuente = fuente.replace("\r\n", "\n").replace("\r", "\n")
        self.longitud = len(self.fuente)
        self.inicio = 0
        self.actual = 0
        self.linea = 1
        self.columna = 1
        self.inicio_columna = 1
        self.tokens: List[Token] = []
        self.max_tokens = max_tokens

    def tokenizar(self) -> List[Token]:
        while not self._es_fin():
            if len(self.tokens) >= self.max_tokens:
                span = SourceSpan(self.linea, self.columna, self.actual, self.actual)
                raise SintaxisError(
                    f"Se superó el límite máximo de tokens permitido ({self.max_tokens}).",
                    span=span,
                    codigo="LIMITE_TOKENS_EXCEDIDO"
                )

            self.inicio = self.actual
            self.inicio_columna = self.columna
            self._escanear_token()

        # Añadir EOF
        span_eof = SourceSpan(self.linea, self.columna, self.actual, self.actual)
        self.tokens.append(Token(TokenType.EOF, "", None, span_eof))
        return self.tokens

    def _es_fin(self) -> bool:
        return self.actual >= self.longitud

    def _avanzar(self) -> str:
        caracter = self.fuente[self.actual]
        self.actual += 1
        self.columna += 1
        return caracter

    def _mirar(self) -> str:
        if self._es_fin():
            return "\0"
        return self.fuente[self.actual]

    def _mirar_siguiente(self) -> str:
        if self.actual + 1 >= self.longitud:
            return "\0"
        return self.fuente[self.actual + 1]

    def _coincide(self, esperado: str) -> bool:
        if self._es_fin() or self.fuente[self.actual] != esperado:
            return False
        self.actual += 1
        self.columna += 1
        return True

    def _crear_span(self) -> SourceSpan:
        return SourceSpan(
            line=self.linea,
            column=self.inicio_columna,
            offset_start=self.inicio,
            offset_end=self.actual,
        )

    def _agregar_token(self, tipo: TokenType, valor: Optional[object] = None):
        texto = self.fuente[self.inicio:self.actual]
        self.tokens.append(Token(tipo, texto, valor, self._crear_span()))

    def _escanear_token(self):
        c = self._avanzar()

        # Espacios en blanco
        if c in (" ", "\t"):
            return
        elif c == "\n":
            self.linea += 1
            self.columna = 1
            return

        # Delimitadores simples
        if c == "(":
            self._agregar_token(TokenType.LPAREN)
        elif c == ")":
            self._agregar_token(TokenType.RPAREN)
        elif c == "{":
            self._agregar_token(TokenType.LBRACE)
        elif c == "}":
            self._agregar_token(TokenType.RBRACE)
        elif c == "[":
            self._agregar_token(TokenType.LBRACKET)
        elif c == "]":
            self._agregar_token(TokenType.RBRACKET)
        elif c == ";":
            self._agregar_token(TokenType.SEMICOLON)
        elif c == ",":
            self._agregar_token(TokenType.COMMA)
        elif c == ".":
            self._agregar_token(TokenType.DOT)

        # Operadores
        elif c == "+":
            if self._coincide("+"):
                self._agregar_token(TokenType.INCREMENT)
            else:
                self._agregar_token(TokenType.PLUS)
        elif c == "-":
            if self._coincide("-"):
                self._agregar_token(TokenType.DECREMENT)
            else:
                self._agregar_token(TokenType.MINUS)
        elif c == "*":
            self._agregar_token(TokenType.STAR)
        elif c == "%":
            self._agregar_token(TokenType.PERCENT)
        elif c == "/":
            if self._coincide("/"):
                # Comentario de una línea
                while self._mirar() != "\n" and not self._es_fin():
                    self._avanzar()
            elif self._coincide("*"):
                # Comentario multilínea
                self._comentario_bloque()
            else:
                self._agregar_token(TokenType.SLASH)
        elif c == "!":
            if self._coincide("="):
                self._agregar_token(TokenType.BANG_EQUAL)
            else:
                self._agregar_token(TokenType.BANG)
        elif c == "=":
            if self._coincide("="):
                self._agregar_token(TokenType.EQUAL_EQUAL)
            else:
                self._agregar_token(TokenType.ASSIGN)
        elif c == "<":
            if self._coincide("="):
                self._agregar_token(TokenType.LESS_EQUAL)
            else:
                self._agregar_token(TokenType.LESS)
        elif c == ">":
            if self._coincide("="):
                self._agregar_token(TokenType.GREATER_EQUAL)
            else:
                self._agregar_token(TokenType.GREATER)
        elif c == "&":
            if self._coincide("&"):
                self._agregar_token(TokenType.AND_AND)
            else:
                span = self._crear_span()
                raise SintaxisError("Operador no soportado '&'. ¿Quisiste escribir '&&'?", span=span)
        elif c == "|":
            if self._coincide("|"):
                self._agregar_token(TokenType.OR_OR)
            else:
                span = self._crear_span()
                raise SintaxisError("Operador no soportado '|'. ¿Quisiste escribir '||'?", span=span)

        # Cadenas de texto
        elif c == '"':
            self._cadena()

        # Números
        elif c.isdigit():
            self._numero()

        # Identificadores y palabras clave
        elif c.isalpha() or c == "_":
            self._identificador()

        else:
            span = self._crear_span()
            raise SintaxisError(f"Carácter inesperado: '{c}'", span=span)

    def _comentario_bloque(self):
        linea_inicio = self.linea
        col_inicio = self.inicio_columna
        offset_inicio = self.inicio

        while not self._es_fin():
            if self._mirar() == "*" and self._mirar_siguiente() == "/":
                self._avanzar()  # Consume *
                self._avanzar()  # Consume /
                return
            if self._mirar() == "\n":
                self.linea += 1
                self.columna = 0
            self._avanzar()

        span = SourceSpan(linea_inicio, col_inicio, offset_inicio, self.actual)
        raise SintaxisError("Comentario de bloque '/*' no cerrado.", span=span)

    def _cadena(self):
        caracteres = []
        while self._mirar() != '"' and not self._es_fin():
            if self._mirar() == "\n":
                self.linea += 1
                self.columna = 0

            c = self._avanzar()
            if c == "\\":
                if self._es_fin():
                    break
                escape = self._avanzar()
                if escape == "n":
                    caracteres.append("\n")
                elif escape == "t":
                    caracteres.append("\t")
                elif escape == '"':
                    caracteres.append('"')
                elif escape == "\\":
                    caracteres.append("\\")
                else:
                    caracteres.append(escape)
            else:
                caracteres.append(c)

        if self._es_fin():
            span = self._crear_span()
            raise SintaxisError("Cadena de texto sin comilla de cierre '\"'.", span=span)

        # Consumir la comilla de cierre
        self._avanzar()
        valor = "".join(caracteres)
        self._agregar_token(TokenType.STRING_LITERAL, valor)

    def _numero(self):
        while self._mirar().isdigit():
            self._avanzar()

        # Punto decimal
        es_double = False
        if self._mirar() == "." and self._mirar_siguiente().isdigit():
            es_double = True
            self._avanzar()  # Consume el '.'
            while self._mirar().isdigit():
                self._avanzar()

        texto = self.fuente[self.inicio:self.actual]
        if es_double:
            try:
                valor = float(texto)
                self._agregar_token(TokenType.DOUBLE_LITERAL, valor)
            except ValueError:
                span = self._crear_span()
                raise SintaxisError(f"Número decimal inválido: {texto}", span=span)
        else:
            try:
                valor = int(texto)
                # Validar rango 32 bits con signo
                if valor > 2147483647 or valor < -2147483648:
                    span = self._crear_span()
                    raise SintaxisError(f"Número entero excede el rango de 32 bits: {texto}", span=span, codigo="OVERFLOW")
                self._agregar_token(TokenType.INT_LITERAL, valor)
            except ValueError:
                span = self._crear_span()
                raise SintaxisError(f"Número entero inválido: {texto}", span=span)

    def _identificador(self):
        while self._mirar().isalnum() or self._mirar() == "_":
            self._avanzar()

        texto = self.fuente[self.inicio:self.actual]
        tipo = PALABRAS_CLAVE.get(texto, TokenType.IDENTIFIER)
        valor = None

        if tipo == TokenType.KW_TRUE:
            valor = True
            tipo = TokenType.BOOLEAN_LITERAL
        elif tipo == TokenType.KW_FALSE:
            valor = False
            tipo = TokenType.BOOLEAN_LITERAL
        elif tipo == TokenType.KW_NULL:
            valor = None
            tipo = TokenType.KW_NULL

        self._agregar_token(tipo, valor)

