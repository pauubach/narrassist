# Narrative Assistant - API Server

Servidor FastAPI que actúa como puente entre el frontend Tauri (Vue 3) y el backend Python (narrative_assistant).

## Instalación

```bash
# Desde la raíz del proyecto
pip install -r api-server/requirements.txt
```

O si ya tienes el paquete narrative_assistant instalado:

```bash
cd api-server
pip install fastapi uvicorn[standard] pydantic python-multipart
```

## Uso

### Modo Desarrollo (con auto-reload)

```bash
cd api-server
python start_server.py
```

O directamente con uvicorn:

```bash
cd api-server
uvicorn main:app --reload --host 127.0.0.1 --port 8008
```

### Modo Producción

```bash
cd api-server
python start_server.py --production
```

## Endpoints Disponibles

### Sistema

- `GET /api/health` - Health check del servidor
- `GET /api/info` - Información del sistema (GPU, modelos, etc.)

### Proyectos

- `GET /api/projects` - Lista todos los proyectos
- `GET /api/projects/{id}` - Obtiene un proyecto por ID
- `POST /api/projects` - Crea un nuevo proyecto
- `DELETE /api/projects/{id}` - Elimina un proyecto

### Entidades

- `GET /api/projects/{id}/entities` - Lista entidades de un proyecto

### Alertas

- `GET /api/projects/{id}/alerts` - Lista alertas de un proyecto
- `GET /api/projects/{id}/alerts?status=open` - Filtra alertas por estado

## Documentación Interactiva

Una vez iniciado el servidor, visita:

- **Swagger UI**: http://127.0.0.1:8008/docs
- **ReDoc**: http://127.0.0.1:8008/redoc

## Configuración

### Puerto

El servidor escucha en `127.0.0.1:8008` por defecto. Para cambiar el puerto, modifica `main.py` o `start_server.py`.

### CORS

El servidor permite peticiones desde:

- `http://localhost:5173` (Vite dev server)
- `tauri://localhost` (Tauri production)

Para añadir más orígenes, modifica el middleware CORS en `main.py`.

## Integración con Frontend

El frontend Vue 3 usa un proxy de Vite configurado en `frontend/vite.config.ts`:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8008',
      changeOrigin: true
    }
  }
}
```

Esto permite hacer peticiones a `/api/...` desde el frontend sin preocuparse por CORS durante el desarrollo.

## Estructura de Respuestas

Todas las respuestas siguen el formato `ApiResponse`:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "message": "Mensaje opcional"
}
```

En caso de error:

```json
{
  "success": false,
  "data": null,
  "error": "Descripción del error",
  "message": null
}
```

## Logs

El servidor registra todas las peticiones y errores. Nivel de log: `INFO`.

Para cambiar el nivel de log, modifica la configuración en `start_server.py` o usa la variable de entorno `NA_LOG_LEVEL`.
