# Software Educativo Interactivo de Apoyo Docente para la Enseñanza de Sistemas Expertos

Backend correspondiente al **Sprint 1** del proyecto de software educativo, diseñado para apoyar a docentes en la enseñanza y demostración práctica de sistemas expertos basados en reglas y encadenamiento hacia adelante (*Forward Chaining*).

---

## 1. Descripción General

Este backend provee la API REST y el motor de inferencia desacoplado para:
- Crear y modelar **Sistemas Expertos**.
- Gestionar su **Base de Conocimiento** (Hechos, Variables, Reglas, Condiciones lógicas y Conclusiones).
- Representar y organizar gráficamente el grafo de conocimiento en un **Lienzo Visual** (Nodos y Conexiones).
- Ejecutar el **Motor de Inferencia por Encadenamiento hacia Adelante** con trazabilidad completa de cada paso (reglas evaluadas, rechazadas, activadas y ejecutadas) y resolución de conflictos por prioridad.

> **Alcance Sprint 1**: Enfocado exclusivamente en el docente. No incluye usuarios, autenticación, roles, cursos ni modelos de lenguaje / IA.

---

## 2. Arquitectura de Software

El proyecto sigue una arquitectura de **Monolito Modular por Capas** con separación estricta de responsabilidades:

1. **Capa de Presentación / API (`api/`)**:
   - Vistas de API REST (`vistas.py`)
   - Serializadores DRF (`serializadores.py`)
   - Enrutamiento (`urls.py`)
   - Documentación OpenAPI/Swagger con `drf-spectacular`.

2. **Capa de Aplicación (`aplicacion/`)**:
   - Casos de uso de negocio (`casos_de_uso.py`)
   - Orquestación entre el dominio y los adaptadores de infraestructura.

3. **Capa de Dominio (`dominio/`)**:
   - Entidades puras en Python (`entidades.py`)
   - Validadores de reglas de negocio (`validadores.py`)
   - Excepciones de dominio (`excepciones.py`)
   - Puertos / Interfaces abstractas de repositorios (`repositorios.py`)
   - **Motor de inferencia** puro, evaluador lógico y estrategias de resolución de conflictos (`motor.py`, `evaluador.py`, `resolucion_conflictos.py`).

4. **Capa de Infraestructura (`infraestructura/`)**:
   - Modelos ORM Django (`modelos.py`)
   - Adaptadores de repositorios con Django ORM (`repositorios.py`)
   - Persistencia relacional en PostgreSQL (o SQLite).

---

## 3. Estructura del Directorio

```text
back/
├── manage.py
├── requirements.txt
├── .env.example
├── .env
├── pytest.ini
├── README.md
│
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── apps/
│   ├── sistemas_expertos/       # HU-01: Gestión de sistemas expertos
│   │   ├── dominio/             # Entidades, validadores, interfaces
│   │   ├── aplicacion/          # Casos de uso (Crear, Actualizar, etc.)
│   │   ├── infraestructura/     # Modelos ORM y repositorios Django
│   │   ├── api/                 # Serializadores y vistas REST
│   │   ├── management/commands/ # Comando seed_sprint1
│   │   └── tests/               # Pruebas unitarias y de integración
│   │
│   ├── base_conocimiento/       # HU-05, HU-06, HU-07: Hechos, variables, reglas
│   │   ├── dominio/
│   │   ├── aplicacion/
│   │   ├── infraestructura/
│   │   ├── api/
│   │   └── tests/
│   │
│   ├── editor_visual/           # HU-02, HU-03, HU-04: Nodos y conexiones
│   │   ├── dominio/
│   │   ├── aplicacion/
│   │   ├── infraestructura/
│   │   ├── api/
│   │   └── tests/
│   │
│   └── inferencia/              # HU-08, HU-09, HU-10: Motor y traza
│       ├── dominio/             # motor.py, evaluador.py, resolucion_conflictos.py
│       ├── aplicacion/
│       ├── infraestructura/
│       ├── api/
│       └── tests/
│
└── compartido/                  # Componentes transversales
    ├── constantes/              # Enums de estado, tipos de dato, operadores
    ├── excepciones/             # Excepciones base y manejador global DRF
    ├── respuestas/              # Helpers de respuesta JSON uniforme
    └── paginacion/              # Paginador estandarizado
```

---

## 4. Requisitos del Sistema

- **Python**: 3.12 o 3.13+
- **PostgreSQL**: 14+ (o SQLite para desarrollo local)
- **Pip**: >= 23.0

---

## 5. Instalación y Puesta en Marcha

### Paso 1: Clonar o ubicarse en el directorio del proyecto
```bash
cd back
```

### Paso 2: Crear y activar el entorno virtual
En Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

En Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Paso 3: Instalar dependencias
```bash
pip install -r requirements.txt
```

### Paso 4: Configurar variables de entorno
Copiar el archivo de ejemplo:
```bash
cp .env.example .env
```
Editar el archivo `.env` según tu base de datos:
```env
DEBUG=True
SECRET_KEY=clave-secreta-de-desarrollo
DB_ENGINE=django.db.backends.postgresql  # o django.db.backends.sqlite3 para desarrollo local
DB_NAME=sistemas_expertos_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
MAX_INFERENCE_ITERATIONS=100
```

### Paso 5: Aplicar migraciones
```bash
python manage.py migrate
```

### Paso 6: Cargar datos de prueba (Seed Sprint 1)
Ejecuta el comando para poblar el sistema experto de ejemplo (*"Recomendador de metodología de desarrollo"*):
```bash
python manage.py seed_sprint1
```

### Paso 7: Iniciar el servidor de desarrollo
```bash
python manage.py runserver
```
El servidor estará accesible en: `http://localhost:8000/`

---

## 6. Documentación de la API (Swagger / OpenAPI)

Una vez iniciado el servidor, accede a:

- **Swagger UI**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **ReDoc**: [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)
- **OpenAPI Schema JSON/YAML**: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)

---

## 7. Ejecución de Pruebas Automatizadas

La suite incluye pruebas de modelos, casos de uso, API REST y los 6 escenarios del motor de inferencia:

```bash
# Ejecutar toda la suite de pruebas
pytest -v

# Ejecutar por módulo
pytest apps/sistemas_expertos/tests/ -v
pytest apps/base_conocimiento/tests/ -v
pytest apps/editor_visual/tests/ -v
pytest apps/inferencia/tests/ -v

# Ejecutar pruebas puras del motor de inferencia
pytest apps/inferencia/tests/test_motor.py -v
```

---

## 8. Principales Endpoints de la API REST

### Sistemas Expertos
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/v1/sistemas-expertos/` | Listar sistemas expertos |
| `POST` | `/api/v1/sistemas-expertos/` | Crear sistema experto (crea automáticamente su BC 1:1) |
| `GET` | `/api/v1/sistemas-expertos/{id}/` | Detalle del sistema experto |
| `PUT` | `/api/v1/sistemas-expertos/{id}/` | Actualización completa |
| `PATCH` | `/api/v1/sistemas-expertos/{id}/` | Actualización parcial |
| `DELETE` | `/api/v1/sistemas-expertos/{id}/` | Eliminación en cascada |

### Base de Conocimiento, Hechos, Variables y Reglas
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/v1/sistemas-expertos/{id}/base-conocimiento/` | Consultar base de conocimiento asociada |
| `GET` | `/api/v1/bases-conocimiento/{id}/hechos/` | Listar hechos de la base |
| `POST` | `/api/v1/bases-conocimiento/{id}/hechos/` | Crear hecho |
| `GET` / `PUT` / `DELETE` | `/api/v1/hechos/{id}/` | Detalle, editar o borrar hecho |
| `GET` | `/api/v1/bases-conocimiento/{id}/variables/` | Listar variables de la base |
| `POST` | `/api/v1/bases-conocimiento/{id}/variables/` | Crear variable |
| `GET` / `PUT` / `DELETE` | `/api/v1/variables/{id}/` | Detalle, editar o borrar variable |
| `GET` | `/api/v1/bases-conocimiento/{id}/reglas/` | Listar reglas de la base |
| `POST` | `/api/v1/bases-conocimiento/{id}/reglas/` | Crear regla (prioridad, factor certeza) |
| `GET` / `PUT` / `DELETE` | `/api/v1/reglas/{id}/` | Detalle, editar o borrar regla |
| `POST` | `/api/v1/reglas/{id}/condiciones/` | Agregar condición lógica a regla |
| `PUT` / `DELETE` | `/api/v1/condiciones/{id}/` | Modificar o eliminar condición |
| `POST` | `/api/v1/reglas/{id}/conclusiones/` | Agregar conclusión a regla |
| `PUT` / `DELETE` | `/api/v1/conclusiones/{id}/` | Modificar o eliminar conclusión |

### Editor Visual
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/v1/sistemas-expertos/{id}/editor/` | Obtener lienzo completo (nodos y conexiones) |
| `POST` | `/api/v1/sistemas-expertos/{id}/nodos/` | Crear nodo visual en el lienzo |
| `PATCH` | `/api/v1/nodos/{id}/` | Mover posición espacial (X, Y) de un nodo |
| `DELETE` | `/api/v1/nodos/{id}/` | Eliminar nodo visual |
| `POST` | `/api/v1/sistemas-expertos/{id}/conexiones/` | Conectar dos nodos del lienzo |
| `DELETE` | `/api/v1/conexiones/{id}/` | Eliminar conexión |

### Inferencia
| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/v1/sistemas-expertos/{id}/inferencias/` | **Ejecutar motor de inferencia** y obtener traza |
| `GET` | `/api/v1/inferencias/{id}/` | Consultar estado general de una ejecución |
| `GET` | `/api/v1/inferencias/{id}/detalles/` | Consultar traza paso a paso (reglas evaluadas, rechazadas, activadas, ejecutadas) |

---

## 9. Formato Estándar de Respuestas

### Respuesta Exitosa:
```json
{
  "success": true,
  "message": "Inferencia ejecutada correctamente.",
  "data": {
    "ejecucion_id": "16c69c06-2f89-4fc0-8e60-9e6ff4891365",
    "estado": "FINALIZADA",
    "hechos_iniciales": [
      { "nombre": "equipo_pequeno", "valor": true },
      { "nombre": "requisitos_cambiantes", "valor": true }
    ],
    "reglas_evaluadas": [
      {
        "regla": "R1 - Recomendar Scrum",
        "regla_id": "...",
        "estado": "EJECUTADA",
        "condiciones_cumplidas": true,
        "orden": 3,
        "resultado_generado": "recomendacion = Scrum"
      }
    ],
    "hechos_generados": [
      { "nombre": "recomendacion", "valor": "Scrum" }
    ],
    "conclusion_final": "Scrum"
  }
}
```

### Respuesta de Error de Validación:
```json
{
  "success": false,
  "message": "Error de validación en los datos enviados.",
  "errors": {
    "nombre": [ "El campo 'nombre' es obligatorio." ]
  }
}
```
