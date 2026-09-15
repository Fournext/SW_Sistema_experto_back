# ==========================================
# Dockerfile para Backend (Django REST Framework)
# ==========================================
FROM python:3.12-slim

# Metadatos del contenedor
LABEL maintainer="Equipo Sistemas Expertos"
LABEL description="Backend Django REST para Software Educativo de Sistemas Expertos"

# Variables de entorno para optimización de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Directorio de trabajo en el contenedor
WORKDIR /app

# Instalar dependencias del sistema necesarias (curl para healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python primero (aprovechando caché de capas)
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente del proyecto
COPY . /app/

# Preparar script de entrada (sanitizar saltos de línea CRLF -> LF para compatibilidad Windows/Linux)
RUN sed -i 's/\r$//' /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Crear directorio para archivos estáticos si no existe
RUN mkdir -p /app/staticfiles

# Exponer el puerto del servicio
EXPOSE 8000

# Script de arranque para verificar base de datos y correr migraciones
ENTRYPOINT ["/app/entrypoint.sh"]

# Comando por defecto: Servidor WSGI Gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
