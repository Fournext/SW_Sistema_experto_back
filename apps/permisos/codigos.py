"""
Catálogo único y fuente de verdad de los permisos del sistema experto.
Sigue el patrón de Sistema-DEA: los códigos se construyen dinámicamente
a partir del slug del sistema (<slug>_<operacion>) y se sincronizan a
django.contrib.auth.models.Permission mediante 'manage.py generar_permisos'.
"""

from typing import NamedTuple
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

_SETTING_SLUG = "SISTEMA_SLUG"


def slug_sistema() -> str:
    """
    Slug de este sistema, leído de settings.
    Falla explícitamente si no está configurado para evitar prefijos vacíos o inconsistentes.
    """
    slug = str(getattr(settings, _SETTING_SLUG, "sistema-experto")).strip()
    if not slug:
        raise ImproperlyConfigured(
            f"{_SETTING_SLUG} no está configurado en settings. "
            "Definirlo en el .env con el identificador del sistema (ej. sistema-experto)."
        )
    return slug


def prefijo() -> str:
    """Prefijo de los códigos de permiso: el slug en guiones bajos con sufijo '_'."""
    return slug_sistema().strip("-_").replace("-", "_") + "_"


def _codigo(operacion: str) -> str:
    """Construye el código de permiso calificado con el prefijo."""
    return f"{prefijo()}{operacion}"


class DefinicionPermiso(NamedTuple):
    """Metadatos de cada permiso sincronizado en la base de datos."""
    codigo: str
    nombre: str
    descripcion: str
    recurso: str
    operacion: str


class Permisos:
    """Constantes de los códigos de permiso del sistema."""

    # 1. Sistemas Expertos (4)
    SISTEMAS_VER                = _codigo("sistemas_ver")
    SISTEMAS_CREAR              = _codigo("sistemas_crear")
    SISTEMAS_EDITAR             = _codigo("sistemas_editar")
    SISTEMAS_ELIMINAR           = _codigo("sistemas_eliminar")

    # 2. Base de Conocimiento (13)
    BASE_CONOCIMIENTO_VER       = _codigo("base_conocimiento_ver")
    HECHOS_VER                  = _codigo("hechos_ver")
    HECHOS_CREAR                = _codigo("hechos_crear")
    HECHOS_EDITAR               = _codigo("hechos_editar")
    HECHOS_ELIMINAR             = _codigo("hechos_eliminar")

    VARIABLES_VER               = _codigo("variables_ver")
    VARIABLES_CREAR             = _codigo("variables_crear")
    VARIABLES_EDITAR            = _codigo("variables_editar")
    VARIABLES_ELIMINAR          = _codigo("variables_eliminar")

    REGLAS_VER                  = _codigo("reglas_ver")
    REGLAS_CREAR                = _codigo("reglas_crear")
    REGLAS_EDITAR               = _codigo("reglas_editar")
    REGLAS_ELIMINAR             = _codigo("reglas_eliminar")

    # 3. Editor Visual (7)
    EDITOR_VER                  = _codigo("editor_ver")
    EDITOR_NODOS_CREAR          = _codigo("editor_nodos_crear")
    EDITOR_NODOS_EDITAR         = _codigo("editor_nodos_editar")
    EDITOR_NODOS_ELIMINAR       = _codigo("editor_nodos_eliminar")
    EDITOR_CONEXIONES_CREAR     = _codigo("editor_conexiones_crear")
    EDITOR_CONEXIONES_EDITAR    = _codigo("editor_conexiones_editar")
    EDITOR_CONEXIONES_ELIMINAR  = _codigo("editor_conexiones_eliminar")

    # 4. Inferencia y Simulación (6)
    INFERENCIA_EJECUTAR         = _codigo("inferencia_ejecutar")
    SIMULACION_INICIAR          = _codigo("simulacion_iniciar")
    SIMULACION_CONTROLAR        = _codigo("simulacion_controlar")
    INFERENCIA_HISTORIAL_VER    = _codigo("inferencia_historial_ver")
    INFERENCIA_TRAZABILIDAD_VER = _codigo("inferencia_trazabilidad_ver")
    INFERENCIA_EXPLICACION_VER  = _codigo("inferencia_explicacion_ver")

    # 5. Validación de Base de Conocimiento (2)
    VALIDACION_EJECUTAR         = _codigo("validacion_ejecutar")
    VALIDACION_VER              = _codigo("validacion_ver")

    # 6. Actividades Didácticas (11)
    CURSOS_VER                  = _codigo("cursos_ver")
    CURSOS_CREAR                = _codigo("cursos_crear")
    ACTIVIDADES_VER             = _codigo("actividades_ver")
    ACTIVIDADES_CREAR           = _codigo("actividades_crear")
    ACTIVIDADES_EDITAR          = _codigo("actividades_editar")
    ACTIVIDADES_ELIMINAR        = _codigo("actividades_eliminar")
    ASIGNACIONES_VER            = _codigo("asignaciones_ver")
    ASIGNACIONES_CREAR          = _codigo("asignaciones_crear")
    ENTREGAS_VER_TODAS          = _codigo("entregas_ver_todas")
    ACTIVIDADES_RESOLVER        = _codigo("actividades_resolver")
    ENTREGAS_ENVIAR             = _codigo("entregas_enviar")

    # 7. Admin Central (13)
    CENTRAL_ACCEDER             = _codigo("central_acceder")
    CENTRAL_USUARIOS_VER        = _codigo("central_usuarios_ver")
    CENTRAL_USUARIOS_CREAR      = _codigo("central_usuarios_crear")
    CENTRAL_USUARIOS_EDITAR     = _codigo("central_usuarios_editar")
    CENTRAL_USUARIOS_DESACTIVAR = _codigo("central_usuarios_desactivar")
    CENTRAL_ROLES_VER           = _codigo("central_roles_ver")
    CENTRAL_ROLES_CREAR         = _codigo("central_roles_crear")
    CENTRAL_ROLES_EDITAR        = _codigo("central_roles_editar")
    CENTRAL_ROLES_ELIMINAR      = _codigo("central_roles_eliminar")
    CENTRAL_PERMISOS_VER        = _codigo("central_permisos_ver")
    CENTRAL_SESIONES_VER        = _codigo("central_sesiones_ver")
    CENTRAL_SESIONES_REVOCAR    = _codigo("central_sesiones_revocar")
    CENTRAL_BITACORA_VER        = _codigo("central_bitacora_ver")

    TODOS: frozenset[str] = frozenset()


CATALOGO: tuple[DefinicionPermiso, ...] = (
    # Sistemas Expertos
    DefinicionPermiso(Permisos.SISTEMAS_VER, "Ver sistemas expertos", "Permite listar y ver detalles de sistemas expertos.", "sistemas_expertos", "ver"),
    DefinicionPermiso(Permisos.SISTEMAS_CREAR, "Crear sistemas expertos", "Permite registrar nuevos proyectos de sistemas expertos.", "sistemas_expertos", "crear"),
    DefinicionPermiso(Permisos.SISTEMAS_EDITAR, "Editar sistemas expertos", "Permite modificar datos generales de sistemas expertos.", "sistemas_expertos", "editar"),
    DefinicionPermiso(Permisos.SISTEMAS_ELIMINAR, "Eliminar sistemas expertos", "Permite dar de baja o eliminar sistemas expertos.", "sistemas_expertos", "eliminar"),

    # Base de Conocimiento
    DefinicionPermiso(Permisos.BASE_CONOCIMIENTO_VER, "Ver base de conocimiento", "Permite ver el resumen general de la base de conocimiento.", "base_conocimiento", "ver"),
    DefinicionPermiso(Permisos.HECHOS_VER, "Ver hechos", "Permite listar hechos de la base de conocimiento.", "base_conocimiento", "hechos_ver"),
    DefinicionPermiso(Permisos.HECHOS_CREAR, "Crear hechos", "Permite agregar nuevos hechos a la base de conocimiento.", "base_conocimiento", "hechos_crear"),
    DefinicionPermiso(Permisos.HECHOS_EDITAR, "Editar hechos", "Permite modificar hechos existentes.", "base_conocimiento", "hechos_editar"),
    DefinicionPermiso(Permisos.HECHOS_ELIMINAR, "Eliminar hechos", "Permite eliminar hechos de la base de conocimiento.", "base_conocimiento", "hechos_eliminar"),

    DefinicionPermiso(Permisos.VARIABLES_VER, "Ver variables", "Permite consultar variables y sus dominios.", "base_conocimiento", "variables_ver"),
    DefinicionPermiso(Permisos.VARIABLES_CREAR, "Crear variables", "Permite registrar nuevas variables.", "base_conocimiento", "variables_crear"),
    DefinicionPermiso(Permisos.VARIABLES_EDITAR, "Editar variables", "Permite modificar variables y dominios.", "base_conocimiento", "variables_editar"),
    DefinicionPermiso(Permisos.VARIABLES_ELIMINAR, "Eliminar variables", "Permite eliminar variables.", "base_conocimiento", "variables_eliminar"),

    DefinicionPermiso(Permisos.REGLAS_VER, "Ver reglas", "Permite listar y ver detalles de reglas de producción.", "base_conocimiento", "reglas_ver"),
    DefinicionPermiso(Permisos.REGLAS_CREAR, "Crear reglas", "Permite definir nuevas reglas, condiciones y conclusiones.", "base_conocimiento", "reglas_crear"),
    DefinicionPermiso(Permisos.REGLAS_EDITAR, "Editar reglas", "Permite modificar reglas, condiciones y conclusiones.", "base_conocimiento", "reglas_editar"),
    DefinicionPermiso(Permisos.REGLAS_ELIMINAR, "Eliminar reglas", "Permite eliminar reglas de producción.", "base_conocimiento", "reglas_eliminar"),

    # Editor Visual
    DefinicionPermiso(Permisos.EDITOR_VER, "Ver editor visual", "Permite visualizar el grafo y diagrama de la base de conocimiento.", "editor_visual", "ver"),
    DefinicionPermiso(Permisos.EDITOR_NODOS_CREAR, "Crear nodos visuales", "Permite agregar nodos al lienzo interactivo.", "editor_visual", "nodos_crear"),
    DefinicionPermiso(Permisos.EDITOR_NODOS_EDITAR, "Editar nodos visuales", "Permite mover y actualizar propiedades de nodos en el lienzo.", "editor_visual", "nodos_editar"),
    DefinicionPermiso(Permisos.EDITOR_NODOS_ELIMINAR, "Eliminar nodos visuales", "Permite remover nodos del lienzo.", "editor_visual", "nodos_eliminar"),
    DefinicionPermiso(Permisos.EDITOR_CONEXIONES_CREAR, "Crear conexiones visuales", "Permite trazar aristas entre nodos.", "editor_visual", "conexiones_crear"),
    DefinicionPermiso(Permisos.EDITOR_CONEXIONES_EDITAR, "Editar conexiones visuales", "Permite modificar aristas en el lienzo.", "editor_visual", "conexiones_editar"),
    DefinicionPermiso(Permisos.EDITOR_CONEXIONES_ELIMINAR, "Eliminar conexiones visuales", "Permite desconectar nodos en el lienzo.", "editor_visual", "conexiones_eliminar"),

    # Inferencia
    DefinicionPermiso(Permisos.INFERENCIA_EJECUTAR, "Ejecutar inferencia", "Permite correr el motor de encadenamiento hacia adelante.", "inferencia", "ejecutar"),
    DefinicionPermiso(Permisos.SIMULACION_INICIAR, "Iniciar simulación", "Permite iniciar una sesión de simulación interactiva.", "inferencia", "simulacion_iniciar"),
    DefinicionPermiso(Permisos.SIMULACION_CONTROLAR, "Controlar simulación", "Permite pausar, continuar, avanzar paso a paso y reiniciar la simulación.", "inferencia", "simulacion_controlar"),
    DefinicionPermiso(Permisos.INFERENCIA_HISTORIAL_VER, "Ver historial de inferencias", "Permite consultar ejecuciones anteriores.", "inferencia", "historial_ver"),
    DefinicionPermiso(Permisos.INFERENCIA_TRAZABILIDAD_VER, "Ver trazabilidad de inferencia", "Permite inspeccionar pasos, conflictos y hechos inferidos.", "inferencia", "trazabilidad_ver"),
    DefinicionPermiso(Permisos.INFERENCIA_EXPLICACION_VER, "Ver explicación de conclusiones", "Permite consultar el árbol de justificación y por qué de una conclusión.", "inferencia", "explicacion_ver"),

    # Validación
    DefinicionPermiso(Permisos.VALIDACION_EJECUTAR, "Ejecutar validación", "Permite correr el motor de validación lógica de la base de conocimiento.", "validacion", "ejecutar"),
    DefinicionPermiso(Permisos.VALIDACION_VER, "Ver resultados de validación", "Permite consultar incidencias lógicas detectadas.", "validacion", "ver"),

    # Actividades
    DefinicionPermiso(Permisos.CURSOS_VER, "Ver cursos", "Permite consultar cursos académicos.", "actividades", "cursos_ver"),
    DefinicionPermiso(Permisos.CURSOS_CREAR, "Crear cursos", "Permite registrar nuevos cursos académicos.", "actividades", "cursos_crear"),
    DefinicionPermiso(Permisos.ACTIVIDADES_VER, "Ver actividades docentes", "Permite ver catálogo de actividades creadas.", "actividades", "ver"),
    DefinicionPermiso(Permisos.ACTIVIDADES_CREAR, "Crear actividades", "Permite diseñar actividades didácticas.", "actividades", "crear"),
    DefinicionPermiso(Permisos.ACTIVIDADES_EDITAR, "Editar actividades", "Permite modificar parámetros de actividades didácticas.", "actividades", "editar"),
    DefinicionPermiso(Permisos.ACTIVIDADES_ELIMINAR, "Eliminar actividades", "Permite dar de baja actividades didácticas.", "actividades", "eliminar"),
    DefinicionPermiso(Permisos.ASIGNACIONES_VER, "Ver asignaciones", "Permite consultar asignaciones a cursos.", "actividades", "asignaciones_ver"),
    DefinicionPermiso(Permisos.ASIGNACIONES_CREAR, "Crear asignaciones", "Permite asignar actividades a cursos de estudiantes.", "actividades", "asignaciones_crear"),
    DefinicionPermiso(Permisos.ENTREGAS_VER_TODAS, "Ver entregas de estudiantes", "Permite a los docentes revisar las entregas de todos los estudiantes.", "actividades", "entregas_ver_todas"),
    DefinicionPermiso(Permisos.ACTIVIDADES_RESOLVER, "Resolver actividades", "Permite a los estudiantes ver sus actividades asignadas y guardar borradores.", "actividades", "resolver"),
    DefinicionPermiso(Permisos.ENTREGAS_ENVIAR, "Enviar entregas", "Permite formalizar y enviar definitivamente una entrega de actividad.", "actividades", "entregas_enviar"),

    # Admin Central
    DefinicionPermiso(Permisos.CENTRAL_ACCEDER, "Acceder a Admin Central", "Permite acceder a la vista del administrador central del sistema.", "central", "acceder"),
    DefinicionPermiso(Permisos.CENTRAL_USUARIOS_VER, "Ver usuarios en Admin Central", "Permite listar y ver detalles de usuarios en el panel administrativo.", "central", "usuarios_ver"),
    DefinicionPermiso(Permisos.CENTRAL_USUARIOS_CREAR, "Crear usuarios en Admin Central", "Permite registrar nuevos usuarios desde el panel administrativo.", "central", "usuarios_crear"),
    DefinicionPermiso(Permisos.CENTRAL_USUARIOS_EDITAR, "Editar usuarios en Admin Central", "Permite actualizar datos, roles y claves de usuarios.", "central", "usuarios_editar"),
    DefinicionPermiso(Permisos.CENTRAL_USUARIOS_DESACTIVAR, "Activar/Desactivar usuarios", "Permite suspender o reactivar cuentas de usuario.", "central", "usuarios_desactivar"),
    DefinicionPermiso(Permisos.CENTRAL_ROLES_VER, "Ver roles en Admin Central", "Permite consultar los roles (grupos) del sistema.", "central", "roles_ver"),
    DefinicionPermiso(Permisos.CENTRAL_ROLES_CREAR, "Crear roles en Admin Central", "Permite crear nuevos roles de usuario.", "central", "roles_crear"),
    DefinicionPermiso(Permisos.CENTRAL_ROLES_EDITAR, "Editar roles en Admin Central", "Permite asociar o remover permisos a roles.", "central", "roles_editar"),
    DefinicionPermiso(Permisos.CENTRAL_ROLES_ELIMINAR, "Eliminar roles en Admin Central", "Permite remover roles sin usuarios asignados.", "central", "roles_eliminar"),
    DefinicionPermiso(Permisos.CENTRAL_PERMISOS_VER, "Ver catálogo de permisos", "Permite consultar el catálogo completo de permisos en solo lectura.", "central", "permisos_ver"),
    DefinicionPermiso(Permisos.CENTRAL_SESIONES_VER, "Ver sesiones activas", "Permite auditar sesiones activas de los usuarios.", "central", "sesiones_ver"),
    DefinicionPermiso(Permisos.CENTRAL_SESIONES_REVOCAR, "Revocar sesiones activas", "Permite forzar el cierre de sesión de usuarios conectados.", "central", "sesiones_revocar"),
    DefinicionPermiso(Permisos.CENTRAL_BITACORA_VER, "Ver bitácora de accesos", "Permite auditar ingresos y eventos de seguridad.", "central", "bitacora_ver"),
)

Permisos.TODOS = frozenset(d.codigo for d in CATALOGO)

# Permisos asignados por defecto a los grupos del sistema
PERMISOS_DOCENTE: tuple[str, ...] = tuple(
    d.codigo for d in CATALOGO
    if d.codigo not in (
        Permisos.ACTIVIDADES_RESOLVER,
        Permisos.ENTREGAS_ENVIAR,
        Permisos.CENTRAL_ACCEDER,
        Permisos.CENTRAL_USUARIOS_VER,
        Permisos.CENTRAL_USUARIOS_CREAR,
        Permisos.CENTRAL_USUARIOS_EDITAR,
        Permisos.CENTRAL_USUARIOS_DESACTIVAR,
        Permisos.CENTRAL_ROLES_VER,
        Permisos.CENTRAL_ROLES_CREAR,
        Permisos.CENTRAL_ROLES_EDITAR,
        Permisos.CENTRAL_ROLES_ELIMINAR,
        Permisos.CENTRAL_PERMISOS_VER,
        Permisos.CENTRAL_SESIONES_VER,
        Permisos.CENTRAL_SESIONES_REVOCAR,
        Permisos.CENTRAL_BITACORA_VER,
    )
)

PERMISOS_ESTUDIANTE: tuple[str, ...] = (
    Permisos.SISTEMAS_VER,
    Permisos.INFERENCIA_EJECUTAR,
    Permisos.SIMULACION_INICIAR,
    Permisos.SIMULACION_CONTROLAR,
    Permisos.ACTIVIDADES_RESOLVER,
    Permisos.ENTREGAS_ENVIAR,
)

PERMISOS_ADMIN_CENTRAL: tuple[str, ...] = (
    Permisos.CENTRAL_ACCEDER,
    Permisos.CENTRAL_USUARIOS_VER,
    Permisos.CENTRAL_USUARIOS_CREAR,
    Permisos.CENTRAL_USUARIOS_EDITAR,
    Permisos.CENTRAL_USUARIOS_DESACTIVAR,
    Permisos.CENTRAL_ROLES_VER,
    Permisos.CENTRAL_ROLES_CREAR,
    Permisos.CENTRAL_ROLES_EDITAR,
    Permisos.CENTRAL_ROLES_ELIMINAR,
    Permisos.CENTRAL_PERMISOS_VER,
    Permisos.CENTRAL_SESIONES_VER,
    Permisos.CENTRAL_SESIONES_REVOCAR,
    Permisos.CENTRAL_BITACORA_VER,
)

GRUPOS_CONFIG: dict[str, tuple[str, ...]] = {
    "Docente": PERMISOS_DOCENTE,
    "Estudiante": PERMISOS_ESTUDIANTE,
    "Administrador central": PERMISOS_ADMIN_CENTRAL,
}
