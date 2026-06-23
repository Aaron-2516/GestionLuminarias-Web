# LumSys - Sistema de Gestión de Luminarias

LumSys es un sistema web desarrollado con Django para la gestión de luminarias públicas. El sistema permite administrar técnicos, redes, zonas, luminarias y lecturas de consumo.

---

## Tecnologías utilizadas

- Python
- Django
- PostgreSQL
- HTML
- CSS
- JavaScript

---

## Estructura del proyecto

```text
GestionLuminarias-Web/
├── Luminarias/
│   ├── migrations/
│   ├── static/
│   │   └── app/
│   │       ├── css/
│   │       │   ├── base.css
│   │       │   ├── dashboard.css
│   │       │   ├── listado.css
│   │       │   └── login.css
│   │       ├── img/
│   │       └── js/
│   │           ├── detalle_panel.js
│   │           ├── modal_agregar.js
│   │           └── password_toggle.js
│   ├── templates/
│   │   └── luminarias/
│   │       ├── partials/
│   │       ├── agregar_luminarias.html
│   │       ├── agregar_redes.html
│   │       ├── agregar_tecnicos.html
│   │       ├── agregar_zonas.html
│   │       ├── base_supervisor.html
│   │       ├── base_tecnicos.html
│   │       ├── base.html
│   │       ├── cambiar_contrasena.html
│   │       ├── dashboard_supervisor.html
│   │       ├── dashboard_tecnico.html
│   │       ├── generar_informe.html
│   │       ├── login.html
│   │       └── registrar_lecturas.html
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── LumSys/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── manage.py
├── requirements.txt
└── README.md

---
```
## Instalación del entorno

### 1. Clonar el repositorio

```bash
git clone https://github.com/Aaron-2516/GestionLuminarias-Web.git
```
### 2. Entrar a la carpeta del proyecto
```
cd GestionLuminarias-Web
```
### 3. Crear el entorno virtual
```
python -m venv venv
```
### 4. Crear el entorno virtual
```
venv\Scripts\activate
```
### 5. Instalar los requerimientos
```
pip install -r requirements.txt
```
### 6. Crear archivo .env
```
SECRET_KEY=""
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=django.db.backends.postgresql
DB_NAME= "Nombre de tu base de datos"
DB_USER= "Usuario de tu base de datos"
DB_PASSWORD= "Contraseña de tu base datos"
DB_HOST=localhost
DB_PORT=5432
```
### 7. Copiar y pegar script para completar datos fucionales

Utiliza el siguiente script para poder ingresar al sistema como administrador con id = USR001 y contraseña = 2516 y precargar los municipios
```
BEGIN;

-- =========================
-- INSERTAR ROLES
-- =========================

INSERT INTO rol (id_rol, roles)
VALUES 
    (1, 'Supervisor'),
    (2, 'Tecnico')
ON CONFLICT (id_rol) 
DO UPDATE SET
    roles = EXCLUDED.roles;


-- =========================
-- INSERTAR MUNICIPIOS
-- =========================

INSERT INTO municipio (id_municipio, nombre_municipio)
VALUES
    ('MUN001', 'Ayutuxtepeque'),
    ('MUN002', 'Ciudad Delgado'),
    ('MUN003', 'Cuscatancingo'),
    ('MUN004', 'Mejicanos'),
    ('MUN005', 'San Salvador')
ON CONFLICT (id_municipio)
DO UPDATE SET
    nombre_municipio = EXCLUDED.nombre_municipio;


-- =========================
-- INSERTAR USUARIO ADMINISTRADOR
-- =========================

INSERT INTO usuario (
    id_usuario,
    id_rol,
    contrasena,
    nombre_usuario,
    apellido_usuario,
    telefono,
    estado,
    primer_acceso
)
VALUES (
    'USR001',
    1,
    '2516',
    'Administrador',
    'Sistema',
    25160000,
    TRUE,
    FALSE
)
ON CONFLICT (id_usuario)
DO UPDATE SET
    id_rol = EXCLUDED.id_rol,
    contrasena = EXCLUDED.contrasena,
    nombre_usuario = EXCLUDED.nombre_usuario,
    apellido_usuario = EXCLUDED.apellido_usuario,
    telefono = EXCLUDED.telefono,
    estado = EXCLUDED.estado,
    primer_acceso = EXCLUDED.primer_acceso;

COMMIT;
```
