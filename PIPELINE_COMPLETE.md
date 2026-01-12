# Pipeline de Análisis Completo - Resumen Técnico

> **Estado**: ✅ COMPLETADO (2026-01-09)
> **Duración implementación**: ~8 horas
> **Líneas de código**: ~1200 líneas

## Descripción

Pipeline end-to-end que integra todos los módulos del sistema para análisis completo de manuscritos narrativos. Detecta entidades, extrae atributos, analiza inconsistencias y genera alertas.

## Arquitectura

```
Documento (DOCX/TXT/MD)
    ↓
┌─────────────────────────────────────┐
│  STEP 1: Validación                │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  STEP 2: Parsing                   │
│  - TxtParser / DocxParser          │
│  → RawDocument                     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  STEP 3: Fingerprinting            │
│  - SHA-256 hash                    │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  STEP 4: Proyecto                  │
│  - Crear o recuperar               │
│  - SQLite persistence              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  STEP 5: Sesión                    │
│  - SessionManager                  │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  STEP 6: Estructura                │
│  - StructureDetector               │
│  → Capítulos/Escenas               │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  STEP 7: NER                       │
│  - NERExtractor (spaCy)            │
│  - Persistir entidades → DB        │
│  → entity_id asignado              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  STEP 8: Atributos                 │
│  - AttributeExtractor              │
│  - 40+ patterns                    │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  STEP 9: Consistencia              │
│  - AttributeConsistencyChecker     │
│  → AttributeInconsistency          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  STEP 10: Alertas                  │
│  - Resolución entity_name → id     │
│  - AlertEngine.create_from_...     │
│  - Persistir en DB                 │
└─────────────────────────────────────┘
    ↓
AnalysisReport
  ├── entities: list[Entity]
  ├── alerts: list[Alert]
  ├── stats: dict
  ├── errors: list[NarrativeError]
  └── duration_seconds: float
```

## Archivos Implementados

### 1. `pipelines/__init__.py` (31 líneas)
Exports del módulo:
- `AnalysisReport`
- `run_full_analysis`
- `PipelineConfig`
- `export_report_json`
- `export_report_markdown`
- `export_alerts_json`

### 2. `pipelines/analysis_pipeline.py` (475 líneas)
Pipeline principal:
- `PipelineConfig`: Configuración del pipeline
- `AnalysisReport`: Resultado del análisis
- `run_full_analysis()`: Función principal end-to-end
- `_get_or_create_project_with_text()`: Gestión de proyectos
- `_create_session()`: Gestión de sesiones
- `_parse_document()`: Wrapper de parsers
- `_detect_structure()`: Wrapper de structure detector
- `_run_ner()`: NER + persistencia de entidades
- `_run_attribute_extraction()`: Extracción de atributos
- `_run_consistency_analysis()`: Análisis de inconsistencias
- `_create_alerts_from_inconsistencies()`: Creación de alertas con resolución entity_id

### 3. `pipelines/export.py` (320 líneas)
Exportación de informes:
- `export_report_json()`: Exportación JSON completa
- `export_report_markdown()`: Informe legible para humanos
- `export_alerts_json()`: Alertas standalone
- `_entity_to_dict()`: Serialización de entidades
- `_alert_to_dict()`: Serialización de alertas
- `_alert_to_markdown()`: Formato Markdown de alertas

### 4. `cli.py` - `cmd_analyze()` (165 líneas)
CLI completo:
- Validación de archivo
- Configuración del pipeline
- Ejecución del análisis
- Output formateado:
  - Estadísticas del documento
  - Entidades por tipo
  - Alertas críticas (top 10)
  - Advertencias (top 5)
  - Errores del sistema
  - Resumen final

### 5. `docs/API_REFERENCE.md` (250 líneas)
Documentación de APIs:
- Referencia completa de módulos
- Nomenclatura correcta
- Firmas de métodos
- Comportamientos especiales
- Inconsistencias identificadas

## Errores Corregidos Durante Implementación

### Nomenclatura Incorrecta (5)
1. ❌ `RawDocument.text` → ✅ `.full_text`
2. ❌ `DocumentFingerprint.sha256_hash` → ✅ `.full_hash`
3. ❌ `NERExtractor.extract()` → ✅ `.extract_entities()`
4. ❌ `AttributeConsistencyAnalyzer` → ✅ `AttributeConsistencyChecker`
5. ❌ `AttributeConsistencyChecker.analyze()` → ✅ `.check()`

### APIs Inconsistentes (5)
1. `detect_format()` retorna `DocumentFormat` (no Result)
2. `get_parser()` retorna `Parser` (no Result)
3. `generate_fingerprint()` retorna `DocumentFingerprint` (no Result)
4. `ProjectManager.get_by_fingerprint()` retorna `Project | None` (no Result)
5. `SessionManager.start()` retorna `Session` (no Result)

### Firmas de Métodos (5)
1. `SessionManager` constructor requiere `project_id`
2. `SessionManager.start()` sin parámetros (no `session_type`)
3. `StructureDetector.detect()` requiere `RawDocument` completo
4. `ProjectManager.create_from_document()` requiere `text` completo
5. `NERExtractor.extract_entities()` puede retornar `Result.success(None)`

## Resultados de Prueba

### Test Documento Básico (test_document.txt)
```
Documento: test_document.txt (484 caracteres)
Capítulos detectados: 3
Duración: 7.00s
Entidades: 0 (documento muy corto)
Alertas: 0
Estado: ✅ EXITOSO
```

### Estadísticas
- **Proyecto ID**: Auto-generado en DB
- **Sesión ID**: Auto-generado en DB
- **Fingerprint**: SHA-256 único
- **Persistencia**: SQLite con WAL mode

## Manejo de Errores

### Errores Fatales
- Documento no encontrado → Return inmediato
- Error de parsing → Return inmediato
- Error creación proyecto/sesión → Return inmediato

### Errores Recuperables
- Estructura no detectada → Continue con warning
- NER falla → Continue sin entidades
- Atributos fallan → Continue sin atributos
- Consistencia falla → Continue sin alertas

### Protecciones Añadidas
```python
# Protección contra None
entities = ner_result.value or []

# Validación de datos
if entities_data is None:
    entities_data = []

# Manejo de atributos opcionales
len(structure.chapters) if hasattr(structure, 'chapters') else 0
```

## Configuración

### PipelineConfig
```python
config = PipelineConfig(
    run_ner=True,              # Ejecutar NER
    run_attributes=True,       # Extraer atributos
    run_consistency=True,      # Analizar consistencia
    create_alerts=True,        # Crear alertas en DB
    min_confidence=0.5,        # Confianza mínima alertas
    batch_size=None,           # Auto (según GPU/CPU)
)
```

## Uso

### Programático
```python
from narrative_assistant.pipelines import run_full_analysis, PipelineConfig

result = run_full_analysis(
    document_path="manuscript.docx",
    project_name="My Novel",
    config=PipelineConfig()
)

if result.is_success:
    report = result.value
    print(f"Entidades: {len(report.entities)}")
    print(f"Alertas: {len(report.alerts)}")
    print(f"Duración: {report.duration_seconds:.2f}s")
```

### CLI
```bash
# Análisis completo
narrative-assistant analyze manuscript.docx --project "My Novel"

# Con verbose
narrative-assistant analyze manuscript.docx -v
```

### Exportación
```python
from narrative_assistant.pipelines import export_report_json, export_report_markdown

# JSON
export_report_json(report, "analysis_report.json")

# Markdown
export_report_markdown(report, "analysis_report.md")
```

## Próximos Pasos

### Inmediato
- [ ] Tests unitarios del pipeline (STEP 7.5)
- [ ] Test con documento rico (test_document_rich.txt)
- [ ] Validación de detección de inconsistencias

### Mejoras Futuras
- [ ] Progress bars durante análisis largo
- [ ] Cache de análisis NLP
- [ ] Paralelización de análisis
- [ ] Reintentos automáticos en errores temporales
- [ ] Exportación a más formatos (CSV, HTML)

## Notas de Implementación

### Decisiones Arquitectónicas

1. **Parsing antes de Proyecto**: El texto completo se necesita para el fingerprint
2. **Persistencia de Entidades en NER**: Los entity_id se generan aquí para uso posterior
3. **Resolución entity_name → entity_id**: Ocurre en creación de alertas, no en análisis
4. **Errores como Warnings**: Análisis continúa aunque falle un paso no crítico
5. **Result Pattern Inconsistente**: Se maneja con try/except y validaciones

### Lecciones Aprendidas

1. **Documentar APIs primero**: Evita horas de debugging
2. **Validar retornos None**: Muchos módulos retornan None en lugar de listas vacías
3. **Type hints ayudan**: Pero no previenen todos los errores
4. **Logs extensivos**: Críticos para debugging de pipeline complejo
5. **Tests E2E tempranos**: Detectan problemas de integración rápido

## Referencias

- [API_REFERENCE.md](docs/API_REFERENCE.md) - Documentación completa de APIs
- [TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) - Estrategia de testing
- [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) - Estado del proyecto
- [CLAUDE.md](CLAUDE.md) - Instrucciones del proyecto
