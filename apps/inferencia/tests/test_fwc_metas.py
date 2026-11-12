import pytest
from uuid import uuid4
from apps.base_conocimiento.entities import Condicion, Conclusion, Hecho, Regla, Variable
from apps.inferencia.engine import MotorInferencia
from compartido.constantes.enums import OperadorCondicion, TipoDato


def crear_hecho(nombre: str, valor: str, tipo_dato: TipoDato = TipoDato.TEXTO) -> Hecho:
    return Hecho(
        id=uuid4(),
        base_conocimiento_id=uuid4(),
        nombre=nombre,
        valor=valor,
        tipo_dato=tipo_dato,
    )


def crear_regla(nombre: str, prioridad: int, variable_cond: Variable, valor_cond: str,
                variable_conc: Variable, valor_conc: str) -> Regla:
    regla_id = uuid4()
    cond = Condicion(
        id=uuid4(),
        regla_id=regla_id,
        variable_id=variable_cond.id,
        operador=OperadorCondicion.IGUAL,
        valor_esperado=valor_cond,
    )
    conc = Conclusion(
        id=uuid4(),
        regla_id=regla_id,
        variable_resultante_id=variable_conc.id,
        valor_resultante=valor_conc,
    )
    return Regla(
        id=regla_id,
        base_conocimiento_id=uuid4(),
        nombre=nombre,
        prioridad=prioridad,
        activa=True,
        condiciones=[cond],
        conclusiones=[conc],
    )


class TestFWCMetas:
    def test_todas_unificadas_evaluacion(self):
        memoria = {"X": "0", "P": "a", "vacante": ""}
        assert MotorInferencia.todas_unificadas(memoria, ["X"]) is True
        assert MotorInferencia.todas_unificadas(memoria, ["x"]) is True
        assert MotorInferencia.todas_unificadas(memoria, ["X", "P"]) is True
        assert MotorInferencia.todas_unificadas(memoria, ["X", "C"]) is False
        assert MotorInferencia.todas_unificadas(memoria, ["vacante"]) is False
        assert MotorInferencia.todas_unificadas(memoria, []) is False

    def test_clasificar_metas(self):
        memoria = {"X": "0", "P": "a"}
        res = MotorInferencia.clasificar_metas(memoria, ["X", "C"])
        assert res["unificadas"] == {"X": "0"}
        assert res["pendientes"] == ["C"]

    def test_fwc_parada_temprana_meta_unica(self):
        # R1: X=0 -> P=a
        # R2: P=a -> C=b (Meta deseada)
        # R3: C=b -> Z=99 (Innecesaria, NO debe ejecutarse)
        var_x = Variable(id=uuid4(), base_conocimiento_id=uuid4(), nombre="X")
        var_p = Variable(id=uuid4(), base_conocimiento_id=uuid4(), nombre="P")
        var_c = Variable(id=uuid4(), base_conocimiento_id=uuid4(), nombre="C")
        var_z = Variable(id=uuid4(), base_conocimiento_id=uuid4(), nombre="Z")

        r1 = crear_regla("R1", 10, var_x, "0", var_p, "a")
        r2 = crear_regla("R2", 10, var_p, "a", var_c, "b")
        r3 = crear_regla("R3", 10, var_c, "b", var_z, "99")

        motor = MotorInferencia()
        hechos_ini = [crear_hecho("X", "0")]

        # Con meta = ["C"]
        res = motor.ejecutar(
            hechos_iniciales=hechos_ini,
            reglas=[r1, r2, r3],
            variables=[var_x, var_p, var_c, var_z],
            metas=["C"],
        )

        assert res.motivo_parada == "METAS_ALCANZADAS"
        assert res.metas_unificadas == {"C": "b"}
        assert res.metas_pendientes == []
        # R1 y R2 dispararon; R3 NO debe haberse ejecutado porque C ya unificó
        nombres_disparadas = [p.regla_disparada.nombre for p in res.pasos if p.regla_disparada]
        assert nombres_disparadas == ["R1", "R2"]
        assert "Z" not in [h["nombre"] for h in res.hechos_generados]

    def test_fwc_vector_k_metas(self):
        # Vector con 2 metas: ["P", "C"]
        var_x = Variable(id=uuid4(), base_conocimiento_id=uuid4(), nombre="X")
        var_p = Variable(id=uuid4(), base_conocimiento_id=uuid4(), nombre="P")
        var_c = Variable(id=uuid4(), base_conocimiento_id=uuid4(), nombre="C")
        var_w = Variable(id=uuid4(), base_conocimiento_id=uuid4(), nombre="W")

        r1 = crear_regla("R1", 10, var_x, "0", var_p, "a")
        r2 = crear_regla("R2", 10, var_p, "a", var_c, "b")
        r3 = crear_regla("R3", 10, var_c, "b", var_w, "final")

        motor = MotorInferencia()
        hechos_ini = [crear_hecho("X", "0")]

        res = motor.ejecutar(
            hechos_iniciales=hechos_ini,
            reglas=[r1, r2, r3],
            variables=[var_x, var_p, var_c, var_w],
            metas=["P", "C"],
        )

        assert res.motivo_parada == "METAS_ALCANZADAS"
        assert res.metas_unificadas == {"P": "a", "C": "b"}
        assert res.metas_pendientes == []
        nombres_disparadas = [p.regla_disparada.nombre for p in res.pasos if p.regla_disparada]
        assert nombres_disparadas == ["R1", "R2"]
        assert "W" not in [h["nombre"] for h in res.hechos_generados]

    def test_fwc_metas_no_alcanzables_termina_por_saturacion(self):
        # Solicitamos meta "Imposible" que ninguna regla genera
        var_x = Variable(id=uuid4(), base_conocimiento_id=uuid4(), nombre="X")
        var_p = Variable(id=uuid4(), base_conocimiento_id=uuid4(), nombre="P")

        r1 = crear_regla("R1", 10, var_x, "0", var_p, "a")

        motor = MotorInferencia()
        hechos_ini = [crear_hecho("X", "0")]

        res = motor.ejecutar(
            hechos_iniciales=hechos_ini,
            reglas=[r1],
            variables=[var_x, var_p],
            metas=["Imposible"],
        )

        assert res.motivo_parada == "SATURACION"
        assert res.metas_unificadas == {}
        assert res.metas_pendientes == ["Imposible"]

