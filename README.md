# Cuaderno: FastAPI + React + Gemini

Aplicación para guardar cuestionarios PDF, DOCX, XLSX y XLS, extraer sus preguntas con Gemini y conservar el JSON por usuario. El backend usa **FastAPI + SQLAlchemy + Alembic** y el frontend **React + Vite**. No requiere Django ni Jinja2. Este stack coincide con el solicitado en la prueba técnica.

## Arranque en esta carpeta

Las dependencias están instaladas, el frontend está compilado y los datos anteriores ya fueron importados. Desde PowerShell, en la raíz:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Abrí <http://127.0.0.1:8000/>. FastAPI sirve la aplicación React compilada y la API en el mismo origen. La documentación de los endpoints está en <http://127.0.0.1:8000/api/docs>.

Podés ingresar con tu usuario y contraseña anteriores. Las sesiones de Django no se migran: hace falta iniciar sesión de nuevo. La clave de Gemini configurada en `.env` se conserva.

## Docker: frontend y backend juntos

Con Docker Desktop iniciado y configurado para contenedores Linux, ejecutá desde la raíz:

```powershell
docker compose up --build -d
```

Abrí <http://localhost:8000/>. El Dockerfile compila React en una etapa Node y copia el resultado a una imagen Python que ejecuta FastAPI. Frontend y API comparten el puerto 8000, sin necesitar un segundo servidor. Al arrancar se aplican las migraciones de Alembic; si una migración falla, el servidor no inicia. El proceso se ejecuta con un usuario sin privilegios y el healthcheck comprueba tanto la API como la página inicial.

El servidor y el healthcheck leen `PORT` al arrancar; si no está definida, usan `8000`. Compose fija `PORT=8000` para coincidir con su mapeo local. En Vercel con el preset **Container**, la imagen respeta el puerto que espera la plataforma (por defecto `80`): no hace falta forzarlo a `8000`. Después de cambiar estos archivos, subí los cambios al repositorio conectado y desplegá una nueva versión para reconstruir la imagen. Referencia: [puerto del contenedor en Vercel](https://vercel.com/docs/functions/runtimes/container#port-resolution).

Esto corrige el arranque, pero Vercel no conserva el volumen de Compose: usuarios, resultados y documentos todavía necesitan almacenamiento persistente externo para ese despliegue.

Si la API responde **403 «Origen no permitido»** al enviar un formulario, configurá `APP_ORIGINS` en Vercel con el origen HTTPS exacto que aparece en el navegador (por ejemplo, `https://tu-proyecto.vercel.app`, sin `/cuenta/...` ni otras rutas), y volvé a desplegar. Para varias direcciones, separalas con comas. El backend también agrega automáticamente las URLs HTTPS informadas por `VERCEL_URL`, `VERCEL_BRANCH_URL` y `VERCEL_PROJECT_PRODUCTION_URL`; habilitá **Enable access to System Environment Variables** en el proyecto para que estén disponibles. Los dominios personalizados adicionales se declaran en `APP_ORIGINS`. Referencia: [variables de sistema de Vercel](https://vercel.com/docs/environment-variables/system-environment-variables).

React llama a `/api` en el mismo dominio de la página. La validación admite únicamente los orígenes configurados, conserva la protección CSRF y no confía en un comodín `*.vercel.app` ni en el encabezado `Host` de la petición.

Compose toma de `.env` la clave y configuración de Gemini. Si no existe `.env`, copiá `.env.example` y completá `GEMINI_API_KEY` antes de procesar documentos. El archivo `.env`, las bases locales, los archivos subidos y los backups se excluyen del contexto de construcción y de la imagen.

Los datos del contenedor se guardan en el volumen persistente `app-data`, bajo `/data/app.sqlite3` y `/data/media`. **La primera ejecución crea una biblioteca vacía:** no importa ni modifica automáticamente los usuarios/documentos de la base local del proyecto. Los datos creados en Docker se conservan al reconstruir o detener los contenedores con `docker compose down`. Eliminar el volumen elimina esos datos; no uses `down -v` si querés conservarlos.

```powershell
docker compose ps
docker compose logs -f app
docker compose down
```

Para reconstruir después de un cambio, repetí `docker compose up --build -d`. Si tenés Uvicorn local usando el puerto 8000, detenelo antes. Esta configuración publica el puerto solo en localhost y usa `APP_DEBUG=true` por defecto para permitir las cookies de sesión en HTTP local. En producción con HTTPS, configurá `APP_DEBUG=false` y `APP_ORIGINS` con tu dominio.

También podés usar solamente el Dockerfile:

```powershell
docker build -t cuaderno .
docker run --rm --name cuaderno -p 127.0.0.1:8000:8000 --env-file .env -e APP_DEBUG=true -e DATABASE_PATH=/data/app.sqlite3 -e MEDIA_ROOT=/data/media -v cuaderno-data:/data cuaderno
```

El volumen `cuaderno-data` de este ejemplo es distinto del volumen administrado por Compose. Usá una modalidad de forma consistente para ver la misma biblioteca.

## Instalación desde cero

Requiere Python 3.10+ y Node 18+ compatible con Vite 6 (se recomienda una versión LTS vigente). Vite 6 se eligió para admitir el Node 18 instalado en este equipo. El archivo `frontend/package-lock.json` fija las versiones de JavaScript usadas.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
npm --prefix frontend ci
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

No sobrescribas `.env` si ya existe. `requirements.txt` contiene dependencias de ejecución; `requirements-dev.txt` agrega herramientas de pruebas y generación de ejemplos. Para reproducir exactamente el entorno Python verificado, se puede instalar `requirements-lock.txt`, que incluye también las dependencias de desarrollo.

En Linux/macOS se usa `.venv/bin/python` en lugar de `.\.venv\Scripts\python.exe`.

## Desarrollo con recarga de React

En una terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

En otra:

```powershell
npm --prefix frontend run dev
```

Abrí <http://127.0.0.1:5173/>. Vite reenvía `/api` a FastAPI en el puerto 8000, incluyendo cookies. No hace falta CORS abierto. Después de modificar React, ejecutá `npm --prefix frontend run build` para actualizar la interfaz que sirve el puerto 8000.

## Estructura

```text
backend/
  main.py                 Aplicación FastAPI, errores, cabeceras y frontend compilado
  config.py               Variables de entorno
  database.py             Engine y sesiones SQLAlchemy
  models.py               User, AuthSession, Document y UserDocument
  auth.py                 Registro, login, logout y sesión actual
  security.py             Hashes, cookies y protección CSRF
  documents.py            API de biblioteca, carga, extracción y descargas
  schemas.py              Contrato y validación del resultado de Gemini
  services/
    files.py              Validación y lectura de PDF/Office
    storage.py            Rutas privadas dentro de MEDIA_ROOT
    gemini.py             Integración con el SDK oficial de Google
    pipeline.py           Guardado, deduplicación y procesamiento
frontend/
  src/                    Páginas y componentes React, cliente API y estilos
  package.json            Scripts de desarrollo, pruebas y compilación
  package-lock.json       Versiones de dependencias
  dist/                   Compilación local, ignorada por Git
migrations/               Migraciones Alembic
scripts/migrate_django.py  Importación de la base anterior sin modificarla
scripts/create_examples.py Generador de ejemplos inventados
examples/                 Archivos de prueba y JSON de referencia
tests/                    Pruebas de backend y migración
```

## Modelo de datos

| Tabla | Responsabilidad |
| --- | --- |
| `users` | Usuario, email, contraseña hasheada y estado activo |
| `auth_sessions` | Sesiones revocables, hash del token, token CSRF y vencimiento |
| `documents` | Ruta privada, nombre, formato, tamaño y texto extraído |
| `user_documents` | Relación usuario-documento, SHA-256, estado, JSON y errores |

Un usuario tiene muchos registros `UserDocument`; cada registro tiene un documento privado. La restricción única `(user_id, sha256)` evita duplicar la misma entrada para ese usuario. El resultado queda en `UserDocument.result`. Otra cuenta obtiene su propia copia y extracción aunque suba los mismos bytes.

Las nuevas contraseñas usan Argon2. Los hashes PBKDF2-SHA256 importados de Django se verifican sin depender de Django y se actualizan a Argon2 al iniciar sesión correctamente. La cookie de sesión es HttpOnly y SameSite=Lax; con `APP_DEBUG=false` también es Secure. Los tokens de sesión se guardan como hashes, vencen a los siete días y se revocan al salir. El token CSRF se obtiene de `/api/auth/me` o de login/registro y React lo envía en `X-CSRF-Token` para las operaciones autenticadas de escritura. No se guardan tokens en localStorage.

## API

| Método | Ruta | Acción |
| --- | --- | --- |
| POST | `/api/auth/register` | Crear cuenta e iniciar sesión |
| POST | `/api/auth/login` | Iniciar sesión |
| GET | `/api/auth/me` | Usuario actual y token CSRF |
| POST | `/api/auth/logout` | Revocar sesión |
| GET | `/api/documents?page=1` | Biblioteca paginada y totales del usuario |
| POST | `/api/documents` | Subir archivo como multipart: `file`, `public_content=true` |
| GET | `/api/documents/{id}` | Metadatos, estado y resultado |
| POST | `/api/documents/{id}/process` | Procesar o recuperar el resultado guardado |
| GET | `/api/documents/{id}/original` | Descargar original privado |
| GET | `/api/documents/{id}/result` | Descargar JSON |
| GET | `/api/health` | Comprobar disponibilidad |

Los endpoints de documentos filtran por usuario autenticado e ID. `MEDIA_ROOT` no se monta como directorio público. Las descargas y respuestas de la API usan `Cache-Control: private, no-store`. Los formularios y componentes React representan el contenido como texto escapado.

## Gemini y extracción

Configurá en `.env` una clave de un proyecto de [Google AI Studio](https://aistudio.google.com/api-keys) con capa gratuita:

```dotenv
GEMINI_API_KEY=tu-clave
GEMINI_MODEL=gemini-2.5-flash-lite
```

La credencial se usa únicamente en el servidor. Nunca se incluye en el bundle React. El modelo por defecto figura con entrada y salida gratuitas en los [precios de Google](https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-flash-lite); disponibilidad y cuotas dependen del proyecto y pueden cambiar. La aplicación no modifica la facturación de tu proyecto ni cambia automáticamente a modelos pagos. Los reintentos son manuales, y un error de cuota conserva el archivo para intentarlo después.

1. Se valida el contenido y se calcula SHA-256. Si la cuenta ya tiene ese archivo, se recupera su registro.
2. La carga guarda el original. El usuario inicia la extracción mediante el botón **Procesar con Gemini**.
3. Los PDF se envían como `application/pdf` para lectura visual. DOCX se lee con `python-docx`, XLSX con `openpyxl` y XLS con `xlrd`, preservando texto, filas y hojas. No se ejecutan macros ni fórmulas.
4. El [SDK oficial](https://googleapis.github.io/python-genai/) solicita JSON Schema y Pydantic valida nuevamente la respuesta. Se rechazan JSON inválidos y documentos sin preguntas.
5. Se guarda el resultado y se reutiliza sin otra llamada a Gemini. Una actualización condicional impide que dos solicitudes reclamen simultáneamente el mismo procesamiento. Un intento interrumpido puede reclamarse luego de cinco minutos, y su identificador impide que sobrescriba un intento más nuevo.

El contrato conserva `titulo`, `idioma`, `total_items` e `items`. Cada ítem tiene `numero`, `enunciado`, `tipo`, `alternativas` y `respuesta_correcta`. Se admiten `escala_likert`, `seleccion_multiple`, `verdadero_falso`, `desarrollo` y `emparejamiento`, y códigos de idioma ISO 639-1, incluyendo `es`, `it` y `en`.

## Migración desde Django

En este equipo ya se importaron **1 usuario y 2 documentos**, con sus relaciones y resultados. La nueva base es `app.sqlite3`; `db.sqlite3` se conservó como respaldo del origen y los archivos de `media/` mantienen sus rutas. El código anterior está en `backups/legacy-django/` y existe una copia de sus fuentes en `backups/django-source.zip`, ambos fuera del versionado. Ninguno forma parte de la aplicación activa.

Para importar otra instalación, detener primero su servidor Django, conservar su carpeta `media/`, crear una base de destino vacía y ejecutar:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.migrate_django --source ruta/a/db.sqlite3
```

El origen se abre en modo solo lectura. El importador preserva IDs, hashes de contraseña, fechas, nombres y resultados; normaliza los UUID y comprueba la presencia de los originales. Revierte toda la transacción si falta un archivo y rechaza destinos con datos. No ejecutar nuevamente sobre la base ya importada. Los intentos que estaban en curso quedan disponibles para reintentar. Las sesiones y el panel `/admin/` de Django no se trasladan; el frontend conserva el sistema de cuentas y documentos solicitado.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest
npm --prefix frontend test
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m alembic check
```

Las pruebas de backend cubren formatos reales e inválidos, límites, PDF cifrado, esquema, permisos, CSRF, caducidad de sesión, registro/login/logout, descargas, deduplicación, errores y reintentos. La migración se prueba con datos sintéticos, preservación de contraseñas, actualización a Argon2 y rollback. Las pruebas React cubren errores de autenticación, contraseñas distintas, carga multipart, progreso, resultados y escape de texto.

Gemini está simulado en las pruebas: no consumen cuota ni validan la disponibilidad de un modelo real. La revisión visual y la ejecución real de Gemini quedan a cargo del usuario.

Los archivos `examples/cuestionario_inventado.{pdf,docx,xlsx,xls}` son inventados y cubren los cinco tipos. El `.json` es una referencia escrita manualmente, no la salida de una llamada real. Se regeneran con `python scripts/create_examples.py` después de instalar las dependencias de desarrollo.

## Variables y límites

| Variable | Valor por defecto / uso |
| --- | --- |
| `APP_DEBUG` | `true` en local; usar `false` con HTTPS en producción |
| `PORT` | Puerto del contenedor; `8000` si no se define, o el valor indicado por el hosting |
| `APP_ORIGINS` | Orígenes completos permitidos, separados por comas; localhost:8000 y localhost:5173 en local. Se agregan las URLs de sistema de Vercel si están disponibles |
| `GEMINI_API_KEY` | Credencial del servidor para procesar |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` |
| `GEMINI_TIMEOUT_SECONDS` | `90`, máximo `120` |
| `MAX_UPLOAD_MB` | `10` |
| `DATABASE_PATH` | `app.sqlite3` en la raíz |
| `MEDIA_ROOT` | `media/` en la raíz |

Supuestos conservados: la respuesta correcta solo se solicita si está explícita; el modelo puede equivocarse y el resultado debe revisarse. Desarrollo usa alternativas vacías y respuesta null. Emparejamiento conserva ambas columnas en el enunciado y usa un mapa de claves si hay respuesta explícita. Un archivo idéntico conserva el resultado anterior aunque cambie el modelo.

Límites: 100 páginas PDF; 150.000 caracteres de Office; 5000 filas y 100 columnas por hoja; 30 MB descomprimidos y 2000 entradas por archivo Office. No se extraen gráficos/imágenes de Office ni se calculan fórmulas sin valores guardados. El procesamiento es síncrono y esta versión usa SQLite; una cola y una base compartida serían necesarias para mayor concurrencia.

## Despliegue

No hay una publicación externa realizada. Para un servidor Python con HTTPS, instalar `requirements.txt`, compilar React con `npm --prefix frontend ci` y `npm --prefix frontend run build`, ejecutar `alembic upgrade head` y arrancar `uvicorn backend.main:app --host 0.0.0.0 --port 8000` detrás de un proxy. Configurar `APP_DEBUG=false`, `APP_ORIGINS` con el dominio real, y disco persistente para base y archivos. Mantener una instancia con SQLite, permitir el tiempo de extracción y limitar las peticiones en el proxy. No publicar `MEDIA_ROOT`. El frontend se sirve desde el mismo origen que la API.

Las referencias de implementación son la [documentación de FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/quickstart.html), [React](https://react.dev/learn/build-a-react-app-from-scratch) y [Vite 6](https://v6.vite.dev/guide/).
