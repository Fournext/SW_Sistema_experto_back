from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "email", "nombre_completo", "is_staff", "is_active", "date_joined")
    search_fields = ("username", "email", "nombre_completo")
    fieldsets = UserAdmin.fieldsets + (
        ("Datos adicionales", {"fields": ("nombre_completo", "telefono", "biografia", "foto_perfil")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Datos adicionales", {"fields": ("email", "nombre_completo", "telefono")}),
    )
