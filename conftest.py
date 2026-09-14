"""
Configuración global y fixtures de Pytest.
"""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Cliente HTTP de prueba para DRF."""
    return APIClient()
