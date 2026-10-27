from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import serializers
from apps.permisos.codigos import CATALOGO
from .models import RegistroAcceso

Usuario = get_user_model()


class PermisoSerializer(serializers.Serializer):
    codigo = serializers.CharField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField()
    recurso = serializers.CharField()
    operacion = serializers.CharField()


class RolSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="name", read_only=True)
    permisos = serializers.SerializerMethodField()
    usuarios_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ("id", "name", "nombre", "permisos", "usuarios_count")

    def get_permisos(self, obj) -> list[str]:
        return list(obj.permissions.values_list("codename", flat=True))

    def get_usuarios_count(self, obj) -> int:
        return obj.user_set.count()


class RolCreateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    nombre = serializers.CharField(max_length=150, required=False)
    permisos = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )

    def validate(self, attrs):
        nombre = attrs.get("nombre") or attrs.get("name")
        if not nombre:
            raise serializers.ValidationError({"nombre": "El nombre del rol es requerido."})
        grupo_id = self.context.get("rol_id")
        qs = Group.objects.filter(name=nombre)
        if grupo_id:
            qs = qs.exclude(id=grupo_id)
        if qs.exists():
            raise serializers.ValidationError({"nombre": "Ya existe un rol con este nombre."})
        attrs["name"] = nombre
        return attrs


class UsuarioListSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="nombre_para_mostrar", read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            "id",
            "username",
            "email",
            "nombre",
            "nombre_completo",
            "is_active",
            "is_staff",
            "is_superuser",
            "roles",
            "date_joined",
            "last_login",
        )

    def get_roles(self, obj) -> list[dict]:
        return [
            {
                "id": g.id,
                "nombre": g.name,
                "name": g.name,
                "permisos": list(g.permissions.values_list("codename", flat=True)),
            }
            for g in obj.groups.all()
        ]


class UsuarioDetailSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="nombre_para_mostrar", read_only=True)
    roles = serializers.SerializerMethodField()
    permisos_efectivos = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            "id",
            "username",
            "email",
            "nombre",
            "nombre_completo",
            "telefono",
            "biografia",
            "foto_perfil",
            "is_active",
            "is_staff",
            "is_superuser",
            "roles",
            "permisos_efectivos",
            "date_joined",
            "last_login",
        )

    def get_roles(self, obj) -> list[dict]:
        return [
            {
                "id": g.id,
                "nombre": g.name,
                "name": g.name,
                "permisos": list(g.permissions.values_list("codename", flat=True)),
            }
            for g in obj.groups.all()
        ]

    def get_permisos_efectivos(self, obj) -> list[str]:
        return obj.obtener_permisos_lista()


class UsuarioCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    nombre = serializers.CharField(max_length=200, required=False, allow_blank=True)
    nombre_completo = serializers.CharField(max_length=200, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=6)
    roles = serializers.ListField(required=False, default=list)
    is_active = serializers.BooleanField(default=True)

    def validate_username(self, value):
        if Usuario.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya está en uso.")
        return value

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este correo electrónico ya está registrado.")
        return value


class UsuarioUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    nombre = serializers.CharField(max_length=200, required=False, allow_blank=True)
    nombre_completo = serializers.CharField(max_length=200, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=30, required=False, allow_blank=True)
    biografia = serializers.CharField(required=False, allow_blank=True)
    roles = serializers.ListField(required=False)
    is_active = serializers.BooleanField(required=False)

    def validate_email(self, value):
        user_id = self.context.get("user_id")
        if Usuario.objects.filter(email=value).exclude(id=user_id).exists():
            raise serializers.ValidationError("Este correo ya está en uso por otro usuario.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=6)


class RegistroAccesoSerializer(serializers.ModelSerializer):
    usuario = serializers.SerializerMethodField()
    usuario_detalle = serializers.SerializerMethodField()
    resultado = serializers.SerializerMethodField()
    evento_display = serializers.CharField(source="get_evento_display", read_only=True)

    class Meta:
        model = RegistroAcceso
        fields = (
            "id",
            "usuario",
            "usuario_detalle",
            "username_ingresado",
            "evento",
            "evento_display",
            "resultado",
            "ip",
            "user_agent",
            "detalles",
            "fecha",
        )

    def get_usuario(self, obj) -> str:
        if obj.usuario:
            return obj.usuario.username
        return obj.username_ingresado or "Anónimo"

    def get_resultado(self, obj) -> str:
        if "ok" in obj.evento or obj.evento in ("registro", "logout"):
            return "Exitoso"
        if obj.evento == "sesion_revocada":
            return "Revocada"
        return "Fallido"

    def get_usuario_detalle(self, obj):
        if not obj.usuario:
            return None
        return {
            "id": obj.usuario.id,
            "username": obj.usuario.username,
            "nombre": obj.usuario.nombre_para_mostrar,
        }
