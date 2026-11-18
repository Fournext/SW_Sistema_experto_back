import pytest
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.mark.django_db
@override_settings(STUDIO_SERVICE_KEY="test-studio-service-key")
def test_registro_corporativo_crea_docente_y_estudiante_y_acepta_terminos():
    client = APIClient()

    # Clave inválida -> 403
    bad_res = client.post(
        "/api/v1/auth/registro-corporativo/",
        {
            "username": "docente1",
            "email": "docente1@universidad.edu.bo",
            "nombre_completo": "Ing. Docente Uno",
            "rol": "Docente",
        },
        format="json",
        HTTP_X_STUDIO_SERVICE_KEY="wrong-key",
    )
    assert bad_res.status_code == 403

    # Registro Docente -> 200 con tokens y rol Docente
    doc_res = client.post(
        "/api/v1/auth/registro-corporativo/",
        {
            "username": "docente1",
            "email": "docente1@universidad.edu.bo",
            "nombre_completo": "Ing. Docente Uno",
            "rol": "Docente",
        },
        format="json",
        HTTP_X_STUDIO_SERVICE_KEY="test-studio-service-key",
    )
    assert doc_res.status_code == 200
    data = doc_res.json()["data"]
    assert "Docente" in data["user"]["roles"]
    assert data["user"]["terminos_aceptados"] is False
    access_token = data["access"]

    # Primer ingreso: aceptar términos sin marcar -> 400
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    reject_terms = client.post("/api/v1/auth/aceptar-terminos/", {"aceptado": False}, format="json")
    assert reject_terms.status_code == 400

    # Aceptar términos -> 200 y queda persistido
    accept_terms = client.post("/api/v1/auth/aceptar-terminos/", {"aceptado": True}, format="json")
    assert accept_terms.status_code == 200
    assert accept_terms.json()["data"]["terminos_aceptados"] is True

    # Registro Estudiante -> 200 con rol Estudiante
    est_res = client.post(
        "/api/v1/auth/registro-corporativo/",
        {
            "username": "estudiante1",
            "email": "estudiante1@universidad.edu.bo",
            "nombre_completo": "Estudiante Uno",
            "rol": "Estudiante",
        },
        format="json",
        HTTP_X_STUDIO_SERVICE_KEY="test-studio-service-key",
    )
    assert est_res.status_code == 200
    assert "Estudiante" in est_res.json()["data"]["user"]["roles"]
