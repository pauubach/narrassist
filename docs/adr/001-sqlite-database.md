# ADR-001: Usar SQLite como Base de Datos

## Estado

**Aceptada** — 2025-12-20

## Contexto

El sistema necesita persistir:
- Proyectos de manuscritos
- Entidades detectadas (personajes, lugares, objetos)
- Alertas de inconsistencias
- Relaciones entre entidades
- Historial de cambios y versiones
- Métricas de análisis

Requisitos clave:
1. **Privacidad**: Los datos NUNCA deben salir del ordenador del usuario
2. **Zero-config**: No requerir instalación de servidor de base de datos
3. **Portable**: Funcionar en Windows, macOS y Linux
4. **Performance**: Soportar documentos de 100k+ palabras con miles de entidades
5. **Transaccionalidad**: Garantizar consistencia en análisis parciales

Alternativas consideradas:
- **PostgreSQL**: Requiere servidor separado, complejo para usuarios no-técnicos
- **MySQL/MariaDB**: Mismo problema que PostgreSQL
- **JSON files**: No soporta queries complejas, problemas con concurrencia
- **SQLite**: Embebido, zero-config, transaccional

## Decisión

Usar **SQLite 3** con las siguientes configuraciones:

```python
# WAL mode para mejor concurrencia
PRAGMA journal_mode=WAL;

# Foreign keys habilitadas
PRAGMA foreign_keys=ON;

# Timeout para evitar locks
PRAGMA busy_timeout=5000;
```

**Ubicación de datos**:
- `~/.narrative_assistant/data/projects.db` (proyectos, entidades, alertas)
- Backups automáticos en `~/.narrative_assistant/backups/`

**Gestión de schema**:
- Variable `SCHEMA_VERSION` en `persistence/database.py`
- Migraciones manuales incrementales (v29 → v30, etc.)
- Validación de versión al inicio

## Consecuencias

### Positivas ✅

1. **Zero-config**: No requiere instalación ni configuración de servidor
2. **Privacidad garantizada**: Archivo local, nunca sale del disco del usuario
3. **Portable**: Funciona idéntico en Windows/macOS/Linux
4. **Backup simple**: Copiar un solo archivo `.db`
5. **ACID compliant**: Transacciones garantizadas
6. **WAL mode**: Lecturas no bloquean escrituras
7. **Python stdlib**: `sqlite3` incluido en Python, no añade dependencias

### Negativas ⚠️

1. **Concurrencia limitada**: Solo 1 escritor a la vez (mitigado por WAL + busy_timeout)
2. **Sin replicación nativa**: No es un problema (single-user desktop app)
3. **Tamaño máximo teórico**: 281 TB (no es limitante para este caso de uso)
4. **Migraciones manuales**: No hay framework de migrations (aceptable, schemas estables)

### Mitigaciones

- **Lock contention**: WAL mode + `busy_timeout=5000ms` + transacciones cortas
- **Corrupción**: Backups automáticos antes de cada análisis
- **Schema evolution**: Migraciones incrementales con rollback en caso de error

## Notas de Implementación

Ver:
- `src/narrative_assistant/persistence/database.py` — configuración y conexión
- `src/narrative_assistant/persistence/project.py` — repository pattern
- Esquema actual: SCHEMA_VERSION = 29 (v0.10.15)

## Referencias

- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [When to Use SQLite](https://www.sqlite.org/whentouse.html)
- Proyecto usa SQLite desde v0.1.0, con 30 migraciones hasta v0.10.15
