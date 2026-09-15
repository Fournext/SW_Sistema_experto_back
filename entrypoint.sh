#!/bin/sh
set -e

# Esperar a PostgreSQL si se utiliza dicho motor
if [ "$DB_ENGINE" != "django.db.backends.sqlite3" ]; then
    echo "==> Verificando conexión con la base de datos PostgreSQL ($DB_HOST:$DB_PORT)..."
    while ! python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(2); s.connect(('${DB_HOST:-postgres}', int('${DB_PORT:-5432}'))); s.close()" 2>/dev/null; do
        echo "PostgreSQL aún no está disponible. Reintentando en 1 segundo..."
        sleep 1
    done
    echo "==> Conexión exitosa con PostgreSQL."
fi

# Aplicar migraciones
echo "==> Aplicando migraciones de Django..."
python manage.py migrate --noinput

# Recolectar archivos estáticos
echo "==> Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

# Poblar datos iniciales de Sprint 1 si se indica
if [ "${SEED_DATA:-false}" = "true" ]; then
    echo "==> Ejecutando seeder del Sprint 1 (seed_sprint1)..."
    python manage.py seed_sprint1 || echo "Aviso: El seeder finalizó o ya existían datos previos."
fi

echo "==> Iniciando servidor Django..."
exec "$@"
