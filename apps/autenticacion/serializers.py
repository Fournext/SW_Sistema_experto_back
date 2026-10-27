from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

Usuario = get_user_model()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username_or_email = attrs.get("username", "").strip()
        password = attrs.get("password")

        user = None
        # Si parece un email, buscar por email primero
        if "@" in username_or_email:
            u = Usuario.objects.filter(email__iexact=username_or_email).first()
            if u:
                user = authenticate(username=u.username, password=password)

        if not user:
            user = authenticate(username=username_or_email, password=password)

        if not user:
            raise serializers.ValidationError("Usuario o contraseña incorrectos.")

        if not user.is_active:
            raise serializers.ValidationError("Esta cuenta ha sido desactivada. Comuníquese con el administrador.")

        attrs["user"] = user
        return attrs


class RegistroEstudianteSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    nombre_completo = serializers.CharField(max_length=200)
    password = serializers.CharField(write_only=True, min_length=6)
    confirmar_password = serializers.CharField(write_only=True, min_length=6)

    def validate_username(self, value):
        if Usuario.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya está registrado.")
        return value

    def validate_email(self, value):
        if Usuario.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Este correo electrónico ya está registrado.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirmar_password"]:
            raise serializers.ValidationError({"confirmar_password": "Las contraseñas no coinciden."})
        return attrs

    def create(self, validated_data):
        usuario = Usuario.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            nombre_completo=validated_data["nombre_completo"],
            password=validated_data["password"],
            is_active=True,
        )
        # Asignación automática del rol Estudiante
        grupo_estudiante, _ = Group.objects.get_or_create(name="Estudiante")
        usuario.groups.add(grupo_estudiante)
        return usuario


class UsuarioYoSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    permisos = serializers.SerializerMethodField()
    es_admin_central = serializers.BooleanField(read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id",
            "username",
            "email",
            "nombre_completo",
            "es_admin_central",
            "roles",
            "permisos",
            "date_joined",
        )

    def get_roles(self, obj) -> list[str]:
        return list(obj.groups.values_list("name", flat=True))

    def get_permisos(self, obj) -> list[str]:
        return obj.obtener_permisos_lista()
