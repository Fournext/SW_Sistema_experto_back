"""
Rutas de API REST para el módulo de Actividades Educativas (Sprint 2 - HU-23, HU-24, HU-25).
"""
from django.urls import path
from apps.actividades.cursos_api import (CursosListCreateAPIView, CursoDetailAPIView, CursoUnirseAPIView,
    CursoRegenerarInvitacionAPIView, CursoMiembrosAPIView, CursoMiembroDetailAPIView)
from apps.actividades.api_v2 import (ActividadesAPIView, ActividadAPIView, AsignacionesAPIView, ContextoAsignacionAPIView,
    ActividadesEstudianteAPIView, EntregaEstudianteV2APIView, EnviarEntregaV2APIView, EntregasDocenteAPIView,
    EntregaDetailV2APIView, ComentarioEntregaAPIView, ReabrirEntregaAPIView)
from apps.actividades.trabajo_api import TrabajoActividadAPIView

from apps.actividades.views import (
    ActividadDetailAPIView,
    ActividadListCreateAPIView,
    AsignacionListCreateAPIView,
    CursoListCreateAPIView,
    EntregaEstudianteAPIView,
    EnviarEntregaAPIView,
    EstudianteActividadesListAPIView,
)

app_name = "actividades"


urlpatterns = [
    # Cursos
    path("cursos/", CursosListCreateAPIView.as_view(), name="cursos-list-create"),
    path("cursos/unirse/", CursoUnirseAPIView.as_view(), name="curso-unirse"),
    path("cursos/<uuid:id>/", CursoDetailAPIView.as_view(), name="curso-detail"),
    path("cursos/<uuid:id>/invitacion/regenerar/", CursoRegenerarInvitacionAPIView.as_view(), name="curso-invitacion"),
    path("cursos/<uuid:id>/miembros/", CursoMiembrosAPIView.as_view(), name="curso-miembros"),
    path("cursos/<uuid:id>/miembros/<int:estudiante_id>/", CursoMiembroDetailAPIView.as_view(), name="curso-miembro"),
    # HU-23: Gestión de Actividades
    path("actividades/", ActividadesAPIView.as_view(), name="actividades-list-create"),
    path(
        "actividades/<uuid:id_actividad>/",
        ActividadAPIView.as_view(),
        name="actividad-detail",
    ),
    # HU-24: Asignación de Actividades
    path("asignaciones/", AsignacionesAPIView.as_view(), name="asignaciones-list-create"),
    path("asignaciones/<uuid:id_asignacion>/", ContextoAsignacionAPIView.as_view(), name="asignacion-contexto"),
    path("asignaciones/<uuid:id_asignacion>/trabajo/<path:ruta>", TrabajoActividadAPIView.as_view(), name="asignacion-trabajo"),
    path("asignaciones/<uuid:id_asignacion>/entregas/", EntregasDocenteAPIView.as_view(), name="asignacion-entregas"),
    path("entregas/<uuid:id_entrega>/", EntregaDetailV2APIView.as_view(), name="entrega-detail"),
    path("entregas/<uuid:id_entrega>/comentarios/", ComentarioEntregaAPIView.as_view(), name="entrega-comentarios"),
    path("entregas/<uuid:id_entrega>/reabrir/", ReabrirEntregaAPIView.as_view(), name="entrega-reabrir"),
    # HU-25: Resolución de Actividades
    path(
        "estudiante/actividades/",
        ActividadesEstudianteAPIView.as_view(),
        name="estudiante-actividades-list",
    ),
    path(
        "asignaciones/<uuid:id_asignacion>/entrega/",
        EntregaEstudianteV2APIView.as_view(),
        name="entrega-borrador-detail",
    ),
    path(
        "asignaciones/<uuid:id_asignacion>/enviar/",
        EnviarEntregaV2APIView.as_view(),
        name="entrega-enviar",
    ),
]
