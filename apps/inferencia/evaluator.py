"""
Evaluador de condiciones para el motor de inferencia.
Evalúa precondiciones lógicas contra la memoria de trabajo actual.
"""
from decimal import Decimal, InvalidOperation
from typing import Any, Dict
from apps.base_conocimiento.entities import Condicion


class EvaluadorCondicion:
    """Evalúa si una condición se satisface con el estado actual de la memoria de trabajo."""

    @staticmethod
    def _normalizar_booleano(valor: Any) -> bool:
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, str):
            return valor.strip().lower() in ("true", "1", "si", "sí", "verdadero")
        if isinstance(valor, (int, float)):
            return bool(valor)
        return False

    @classmethod
    def evaluar(
        cls,
        condicion: Condicion,
        memoria_trabajo: Dict[str, Any],
        mapa_ids_a_nombres: Dict[str, str],
    ) -> bool:
        """
        Determina si una condición es verdadera dada la memoria de trabajo.
        memoria_trabajo: {nombre_hecho_o_variable: valor_actual}
        mapa_ids_a_nombres: {str(uuid): nombre}
        """
        clave = None
        if condicion.variable_id:
            clave = mapa_ids_a_nombres.get(str(condicion.variable_id))
        elif condicion.hecho_id:
            clave = mapa_ids_a_nombres.get(str(condicion.hecho_id))

        if not clave or clave not in memoria_trabajo:
            return False

        valor_actual = memoria_trabajo[clave]
        valor_esperado_str = str(condicion.valor_esperado).strip()
        operador = (
            condicion.operador.value
            if hasattr(condicion.operador, "value")
            else condicion.operador
        )

        # 1. Comparación booleana
        if isinstance(valor_actual, bool) or valor_esperado_str.lower() in (
            "true",
            "false",
            "verdadero",
            "falso",
        ):
            actual_bool = cls._normalizar_booleano(valor_actual)
            esperado_bool = cls._normalizar_booleano(valor_esperado_str)
            if operador == "=":
                return actual_bool == esperado_bool
            if operador == "!=":
                return actual_bool != esperado_bool
            return False

        # 2. Comparación numérica
        es_numerico = False
        val_actual_num = None
        val_esperado_num = None
        try:
            val_actual_num = Decimal(str(valor_actual))
            val_esperado_num = Decimal(valor_esperado_str)
            es_numerico = True
        except (InvalidOperation, ValueError, TypeError):
            es_numerico = False

        if es_numerico:
            if operador == "=":
                return val_actual_num == val_esperado_num
            if operador == "!=":
                return val_actual_num != val_esperado_num
            if operador == ">":
                return val_actual_num > val_esperado_num
            if operador == "<":
                return val_actual_num < val_esperado_num
            if operador == ">=":
                return val_actual_num >= val_esperado_num
            if operador == "<=":
                return val_actual_num <= val_esperado_num
            return False

        # 3. Comparación de texto
        str_actual = str(valor_actual).strip()
        if operador == "=":
            return str_actual.lower() == valor_esperado_str.lower()
        if operador == "!=":
            return str_actual.lower() != valor_esperado_str.lower()
        if operador == "CONTIENE":
            return valor_esperado_str.lower() in str_actual.lower()

        return False
