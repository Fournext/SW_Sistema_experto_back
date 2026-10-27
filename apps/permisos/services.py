import logging
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .codigos import CATALOGO, GRUPOS_CONFIG
from .models import Permiso

logger = logging.getLogger(__name__)


class PermisoService:
    """
    Servicio de sincronización de permisos entre el catálogo en código
    y la base de datos de Django (auth.Permission y auth.Group).
    """

    @classmethod
    def escanear_y_generar_permisos(
        cls,
        verbose: bool = True,
        eliminar_obsoletos: bool = True,
        sincronizar_grupos: bool = True,
    ) -> dict[str, int]:
        imprimir = print if verbose else (lambda *args, **kwargs: None)
        imprimir("\nSincronizando catalogo de permisos con Django...")

        content_type, _ = ContentType.objects.get_or_create(
            app_label="permisos",
            model="permiso",
        )

        creados = 0
        actualizados = 0
        eliminados = 0

        # 1. Sincronizar catálogo de permisos
        for definicion in CATALOGO:
            try:
                permiso_obj, was_created = Permission.objects.update_or_create(
                    codename=definicion.codigo,
                    content_type=content_type,
                    defaults={
                        "name": definicion.nombre,
                    },
                )
                if was_created:
                    creados += 1
                    imprimir(f"  [+] Creado: {definicion.codigo} - {definicion.nombre}")
                else:
                    actualizados += 1
                    imprimir(f"  [*] Actualizado: {definicion.codigo}")
            except Exception as e:
                logger.warning("Error al sincronizar permiso %s: %s", definicion.codigo, e)
                imprimir(f"  [-] Error en {definicion.codigo}: {e}")

        # 2. Eliminar permisos obsoletos si se solicita
        if eliminar_obsoletos:
            codigos_validos = {definicion.codigo for definicion in CATALOGO}
            obsoletos = Permission.objects.filter(
                content_type=content_type
            ).exclude(codename__in=codigos_validos)

            for p in obsoletos:
                imprimir(f"  [-] Eliminando permiso obsoleto: {p.codename}")
                p.delete()
                eliminados += 1

        # 3. Sincronizar grupos base y sus permisos
        if sincronizar_grupos:
            imprimir("\nSincronizando roles/grupos base...")
            for nombre_grupo, lista_codigos in GRUPOS_CONFIG.items():
                grupo, g_created = Group.objects.get_or_create(name=nombre_grupo)
                permisos_qs = Permission.objects.filter(
                    content_type=content_type,
                    codename__in=lista_codigos,
                )
                # Se asignan los permisos del catálogo
                grupo.permissions.set(permisos_qs)
                accion = "Creado" if g_created else "Actualizado"
                imprimir(f"  [+] Grupo {accion}: {nombre_grupo} ({len(permisos_qs)} permisos)")

        resumen = {
            "creados": creados,
            "actualizados": actualizados,
            "eliminados": eliminados,
        }
        imprimir(f"\nProceso completado: {creados} creados, {actualizados} actualizados, {eliminados} eliminados.\n")
        return resumen
