# API Reference - Narrative Assistant

> Documentación de APIs internas para integración del pipeline
> Generado: 2026-01-09

## Índice
- [Parsers](#parsers)
- [NLP](#nlp)
- [Persistence](#persistence)
- [Analysis](#analysis)
- [Alerts](#alerts)
- [Entities](#entities)

---

## Parsers

### `parsers.base`

#### `detect_format(path: Path) -> DocumentFormat`
- **Retorna**: `DocumentFormat` (enum) directamente
- **No** retorna `Result`
- **Valores**: DOCX, TXT, MARKDOWN, PDF, EPUB, UNKNOWN

#### `get_parser(path: Path) -> DocumentParser`
- **Retorna**: Instancia del parser apropiado
- **No** retorna `Result`
- **Ejemplo**: `TxtParser()`, `DocxParser()`

#### `DocumentParser.parse(path: Path) -> Result[RawDocument]`
- **Retorna**: `Result[RawDocument]`
- **RawDocument.full_text**: str (NO `.text`)
- **RawDocument.paragraphs**: list[Paragraph]
- **RawDocument.headings**: list[Heading]

### `parsers.structure_detector`

#### `StructureDetector.detect(document: RawDocument) -> Result[DocumentStructure]`
- **Parámetro**: `RawDocument` (NO texto plano)
- **Retorna**: `Result[DocumentStructure]`
- **DocumentStructure.chapters**: list[Chapter]

---

## NLP

### `nlp.ner`

#### `NERExtractor.extract_entities(text: str) -> Result[list[dict]]`
- **Método correcto**: `extract_entities` (NO `extract`)
- **Retorna**: `Result[list[dict]]`
- **Dict keys**: `text`, `entity_type`, `start_char`, `end_char`, `confidence`
- **Puede retornar**: `Result.success(None)` si no hay entidades

### `nlp.attributes`

#### `AttributeExtractor.extract_attributes(text: str, entities: list[dict]) -> Result[list[ExtractedAttribute]]`
- **Retorna**: `Result[list[ExtractedAttribute]]`
- **entities formato**: list de dicts con keys `text`, `entity_type`

---

## Persistence

### `persistence.document_fingerprint`

#### `generate_fingerprint(text: str) -> DocumentFingerprint`
- **Retorna**: `DocumentFingerprint` directamente
- **No** retorna `Result`
- **Atributos**:
  - `.full_hash`: str (SHA-256) - **NO** `.sha256_hash`
  - `.sample_hash`: str
  - `.ngram_shingles`: list

### `persistence.project`

#### `ProjectManager()`
- **Constructor**: Sin parámetros

#### `ProjectManager.get_by_fingerprint(fingerprint: str) -> Project | None`
- **Retorna**: `Project` object o `None`
- **No** retorna `Result`

#### `ProjectManager.create_from_document(text: str, name: str, document_format: str, document_path: Path = None, description: str = '', check_existing: bool = True) -> Result[Project]`
- **Retorna**: `Result[Project]`
- **Parámetro crítico**: `text` (texto completo del documento)
- **document_format**: str (value del enum DocumentFormat)
- **Project.id**: int
- **Project.name**: str

### `persistence.session`

#### `SessionManager(project_id: int)`
- **Constructor**: Requiere `project_id`

#### `SessionManager.start() -> Session`
- **Sin parámetros** (NO `session_type`)
- **Retorna**: `Session` object directamente
- **Session.id**: int

---

## Analysis

### `analysis.attribute_consistency`

#### `AttributeConsistencyChecker.check(attributes: list[ExtractedAttribute]) -> Result[list[AttributeInconsistency]]`
- **Clase correcta**: `AttributeConsistencyChecker` (NO `AttributeConsistencyAnalyzer`)
- **Método**: `check` (NO `analyze`)
- **Retorna**: `Result[list[AttributeInconsistency]]`

#### `AttributeInconsistency`
- **Atributos**:
  - `entity_name`: str
  - `entity_id`: int (añadido recientemente)
  - `attribute_key`: AttributeKey
  - `value1`, `value2`: str
  - `value1_chapter`, `value2_chapter`: int | None
  - `value1_excerpt`, `value2_excerpt`: str
  - `inconsistency_type`: InconsistencyType
  - `confidence`: float
  - `explanation`: str

---

## Alerts

### `alerts.engine`

#### `get_alert_engine() -> AlertEngine`
- **Singleton**: Usar función `get_alert_engine()`
- **Thread-safe**

#### `AlertEngine.create_from_attribute_inconsistency(project_id, entity_name, entity_id, attribute_key, value1, value2, value1_source, value2_source, explanation, confidence) -> Result[Alert]`
- **Retorna**: `Result[Alert]`
- **value1_source**, **value2_source**: dict con keys `chapter`, `position`, `text`

---

## Entities

### `entities.repository`

#### `get_entity_repository() -> EntityRepository`
- **Singleton**: Usar función `get_entity_repository()`

#### `EntityRepository.create(entity: Entity) -> Result[Entity]`
- **Retorna**: `Result[Entity]`
- **Entity creado tiene `.id` asignado por DB

#### `EntityRepository.search_by_name(project_id: int, name: str) -> Result[list[Entity]]`
- **Retorna**: `Result[list[Entity]]`
- **Puede retornar lista vacía** si no encuentra

---

## Resumen de Inconsistencias Encontradas

### ❌ APIs que NO retornan Result:
1. `detect_format()` → retorna `DocumentFormat`
2. `get_parser()` → retorna `DocumentParser`
3. `generate_fingerprint()` → retorna `DocumentFingerprint`
4. `ProjectManager.get_by_fingerprint()` → retorna `Project | None`
5. `SessionManager.start()` → retorna `Session`

### ❌ Nomenclatura incorrecta:
1. `RawDocument.text` → correcto: `.full_text`
2. `DocumentFingerprint.sha256_hash` → correcto: `.full_hash`
3. `NERExtractor.extract()` → correcto: `.extract_entities()`
4. `AttributeConsistencyAnalyzer` → correcto: `AttributeConsistencyChecker`
5. `AttributeConsistencyChecker.analyze()` → correcto: `.check()`

### ⚠️ Comportamientos especiales:
1. `NERExtractor.extract_entities()` puede retornar `Result.success(None)`
2. `SessionManager` constructor requiere `project_id`
3. `SessionManager.start()` no acepta parámetros
4. `StructureDetector.detect()` requiere `RawDocument` completo (no texto plano)
5. `AttributeInconsistency.entity_id` debe ser `0` como placeholder si no se conoce

---

## Changelog

### 2026-01-09
- Documentación inicial creada durante debugging del pipeline
- Identificadas 10+ inconsistencias de API
- Todas las inconsistencias han sido corregidas en `analysis_pipeline.py`
