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
    nombre_completo = serializers.CharField(max_length=200, required=False)
    nombre = serializers.CharField(max_length=200, required=False, write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)
    confirmar_password = serializers.CharField(write_only=True, min_length=6, required=False)
    password_confirm = serializers.CharField(write_only=True, min_length=6, required=False)

    def validate_username(self, value):
        if Usuario.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya está registrado.")
        return value

    def validate_email(self, value):
        if Usuario.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Este correo electrónico ya está registrado.")
        return value

    def validate(self, attrs):
        nombre = attrs.get("nombre_completo") or attrs.get("nombre")
        if not nombre:
            raise serializers.ValidationError({"nombre_completo": "Este campo es requerido."})
        attrs["nombre_completo"] = nombre
        attrs.pop("nombre", None)

        confirmar = (
            attrs.get("confirmar_password")
            or attrs.get("password_confirm")
        )
        if not confirmar:
            confirmar = attrs.get("password")

        if attrs.get("password") != confirmar:
            raise serializers.ValidationError({"confirmar_password": "Las contraseñas no coinciden."})
        attrs["confirmar_password"] = confirmar
        attrs.pop("password_confirm", None)
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


class RegistroCorporativoStudioSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    nombre_completo = serializers.CharField(max_length=200)
    rol = serializers.ChoiceField(choices=["Docente", "Estudiante"])
    password = serializers.CharField(write_only=True, min_length=6, required=False)

    def create_or_sync(self):
        import secrets
        from apps.permisos.services import PermisoService

        email = self.validated_data["email"].strip().lower()
        username = self.validated_data["username"].strip()
        nombre_completo = self.validated_data["nombre_completo"].strip()
        rol = self.validated_data["rol"]
        password = self.validated_data.get("password")

        usuario = Usuario.objects.filter(email__iexact=email).first()
        if not usuario:
            usuario = Usuario.objects.filter(username__iexact=username).first()

        if usuario:
            if nombre_completo and not usuario.nombre_completo:
                usuario.nombre_completo = nombre_completo
                usuario.save(update_fields=["nombre_completo"])
        else:
            usuario = Usuario.objects.create_user(
                username=username,
                email=email,
                nombre_completo=nombre_completo,
                password=password or secrets.token_urlsafe(24),
                is_active=True,
            )

        grupo, created = Group.objects.get_or_create(name=rol)
        if created or grupo.permissions.count() == 0:
            PermisoService.escanear_y_generar_permisos(verbose=False)
            grupo = Group.objects.get(name=rol)

        # Mantener coherencia entre Docente y Estudiante
        otro_rol = "Estudiante" if rol == "Docente" else "Docente"
        usuario.groups.remove(*Group.objects.filter(name=otro_rol))
        usuario.groups.add(grupo)
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
            "terminos_aceptados",
            "terminos_aceptados_en",
            "roles",
            "permisos",
            "date_joined",
        )

    def get_roles(self, obj) -> list[str]:
        return list(obj.groups.values_list("name", flat=True))

    def get_permisos(self, obj) -> list[str]:
        return obj.obtener_permisos_lista()
