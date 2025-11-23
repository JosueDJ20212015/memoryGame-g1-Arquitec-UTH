# 🧠 MEMORY GAME — Proyecto Final de Arquitectura de Computadorase

### Grupo #1 — Arquitectura de Computarodas - UTH
## 🎮 Descripción del Proyecto
Memory Game es una aplicación web interactiva desarrollada con Django que simula el clásico juwego de memoria, donde el usuario debe encontrar pares de tarjetas iguales. Este proyecto se integró con características modernas como:
- Sistema de usuarios con inicio de sesión tradicional y con Google OAuth (django-allauth).
- Registro de puntajes y progreso.
- Diseño responsivo y dinámico.
- Sonidos, animaciones y experiencia optimizada.

Este proyecto forma parte del curso de Arquitectura y Organización de Computadoras, donde se aplicaron conceptos clave de infraestructura, modularidad, redes, optimización y despliegue.

## 🏗️ Arquitectura del Sistema
El sistema opera bajo una arquitectura de tres servicios contenedorizados:
```
┌─────────────────────────────┐
│          NGINX              │
│ (Reverse Proxy + Static)    │
└───────────────▲─────────────┘
                │
        Docker Network
                │
┌───────────────┴─────────────┐
│            WEB               │
│  Django + Gunicorn (WSGI)    │
└───────────────▲─────────────┘
                │
        Docker Network
                │
┌───────────────┴─────────────┐
│            DB                │
│       PostgreSQL 15          │
└──────────────────────────────┘
```

Tecnologías principales:

- Django 5
- Gunicorn
- Nginx
- Docker / Docker Compose
- PostgreSQL 15
- Let’s Encrypt / Certbot
- OAuth con Google

  ## 🚀 Despliegue en Producción

  El proyecto fue desplegado en una instancia:

- AWS EC2 Ubuntu 22.04
- Dominio: memorygame-grupo1.com
- Certificado SSL activo
- Contenedores orquestados mediante Docker Compose

## 📂 Estructura del Proyecto

``` copy 
memorygame/
│── backend/               # Código Django
│── docker/
│    └── nginx/
│         ├── nginx.conf   # Reverse proxy
│         └── ssl/         # Certificados SSL
│── Dockerfile             # Imagen del backend
│── docker-compose.yml     # Orquestación
│── requirements.txt       # Dependencias
│── .env                   # Variables de entorno

```

## ⚙️ Instalación y Ejecución Local
1. Clonar el repositorio
``` copy
git clone https://github.com/JosueDJ20212015/memoryGame-g1-Arquitec-UTH.git
cd memorygame
```

2. Crear entorno virtual
``` copy
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Base de datos local (SQLite por defecto)
``` copy
python manage.py migrate
```
