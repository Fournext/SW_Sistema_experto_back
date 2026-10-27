from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado para el software de Sistemas Expertos.
    Permite autenticación por username o correo, y desacopla el esquema
    de usuarios del default de Django.
    """
    email = models.EmailField(
        unique=True,
        verbose_name="Correo electrónico",
        help_text="Dirección de correo electrónico institucional o personal única.",
    )
    nombre_completo = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Nombre completo",
        help_text="Nombres y apellidos completos del usuario.",
    )
    telefono = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Teléfono / Celular",
    )
    biografia = models.TextField(
        blank=True,
        verbose_name="Biografía o descripción",
    )
    foto_perfil = models.URLField(
        blank=True,
        verbose_name="URL de foto de perfil",
    )
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "usuarios"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return f"{self.username} ({self.nombre_completo or self.get_full_name() or self.email})"

    @property
    def nombre_para_mostrar(self) -> str:
        return self.nombre_completo or self.get_full_name() or self.username

    @property
    def es_estudiante(self) -> bool:
        return self.groups.filter(name="Estudiante").exists()

    @property
    def es_docente(self) -> bool:
        return self.groups.filter(name="Docente").exists()

    @property
    def es_admin_central(self) -> bool:
        if self.is_superuser:
            return True
        # Verifica si tiene el permiso para acceder al admin central
        return self.has_perm("permisos.sistema_experto_central_acceder")

    def obtener_permisos_lista(self) -> list[str]:
        """
        Retorna la lista de códigos de permisos asignados al usuario
        (directos o a través de sus roles/grupos).
        """
        if self.is_superuser:
            from apps.permisos.codigos import Permisos
            return list(Permisos.TODOS)

        todos_permisos = self.get_all_permissions()
        codigos = []
        for p in todos_permisos:
            # Los permisos de django tienen formato 'app_label.cod_permiso'
            if "." in p:
                codigos.append(p.split(".", 1)[1])
            else:
                codigos.append(p)
        return sorted(list(set(codigos)))
