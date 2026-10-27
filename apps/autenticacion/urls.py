from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginAPIView,
    LogoutAPIView,
    RegistroEstudianteAPIView,
    YoAPIView,
)

app_name = "autenticacion"

urlpatterns = [
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/registro-estudiante/", RegistroEstudianteAPIView.as_view(), name="registro_estudiante"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/yo/", YoAPIView.as_view(), name="yo"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
]
