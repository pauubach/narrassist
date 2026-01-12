# Schema de Base de Datos

[← Volver a Arquitectura](./README.md) | [← Índice principal](../../README.md)

---

## Configuración SQLite

```sql
-- SCHEMA: Asistente de Corrección Narrativa
-- Versión: 1.0.0

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
```

---

## Proyecto y Documento

```sql
CREATE TABLE project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'es',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings TEXT DEFAULT '{}'  -- JSON: umbrales, preferencias
);

CREATE TABLE document_version (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,  -- SHA256 para detectar cambios
    word_count INTEGER,
    chapter_hashes TEXT DEFAULT '{}',  -- JSON: {chapter_num: hash}
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_current INTEGER DEFAULT 1,
    UNIQUE(project_id, version_number)
);

CREATE INDEX idx_docversion_project ON document_version(project_id, is_current);

-- Snapshots inmutables para análisis en curso
CREATE TABLE document_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    chapter_data TEXT NOT NULL,  -- JSON: estructura completa de capítulos
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, version_number)
);

CREATE TABLE chapter (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title TEXT,
    start_char INTEGER NOT NULL,  -- Posición en texto plano
    end_char INTEGER NOT NULL,
    focalization_type TEXT,  -- 'zero', 'internal', 'external'
    focalization_character_id INTEGER REFERENCES entity(id),
    UNIQUE(project_id, number)
);

CREATE TABLE scene (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id INTEGER NOT NULL REFERENCES chapter(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    UNIQUE(chapter_id, number)
);
```

---

## Entidades y Menciones

```sql
CREATE TABLE entity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL CHECK(entity_type IN (
        'character', 'location', 'object', 'organization', 'event'
    )),
    canonical_name TEXT NOT NULL,
    aliases TEXT DEFAULT '[]',  -- JSON array
    importance TEXT DEFAULT 'secondary' CHECK(importance IN (
        'protagonist', 'main', 'secondary', 'minor', 'mentioned'
    )),
    first_chapter INTEGER,
    last_chapter INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_by_user INTEGER DEFAULT 0
);

CREATE INDEX idx_entity_project_type ON entity(project_id, entity_type);

CREATE TABLE text_reference (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapter(id) ON DELETE SET NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    surface_form TEXT NOT NULL,  -- Texto tal como aparece
    detection_method TEXT DEFAULT 'ner',  -- 'ner', 'coref', 'manual', 'pattern'
    confidence REAL DEFAULT 1.0
);

CREATE INDEX idx_textref_entity ON text_reference(entity_id);
CREATE INDEX idx_textref_chapter ON text_reference(chapter_id);

-- Anclas resilientes para relocalización ante cambios
CREATE TABLE text_anchor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    -- Contexto estructural (más estable)
    chapter_number INTEGER NOT NULL,
    paragraph_index INTEGER NOT NULL,
    sentence_index INTEGER DEFAULT 0,
    -- Posición absoluta (referencia rápida, puede invalidarse)
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    -- Contenido para relocalización
    text_content TEXT NOT NULL,
    text_hash TEXT NOT NULL,  -- Hash normalizado del contenido
    context_before TEXT DEFAULT '',  -- ~50 chars antes
    context_after TEXT DEFAULT '',   -- ~50 chars después
    context_hash TEXT DEFAULT '',    -- Hash del contexto completo
    -- Metadatos de versión
    source_version INTEGER NOT NULL,
    last_relocated_version INTEGER,
    relocation_confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_anchor_project ON text_anchor(project_id);
CREATE INDEX idx_anchor_chapter ON text_anchor(chapter_number);
CREATE INDEX idx_anchor_hash ON text_anchor(text_hash);

CREATE TABLE merge_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    result_entity_id INTEGER NOT NULL REFERENCES entity(id),
    source_entity_ids TEXT NOT NULL,  -- JSON array de IDs fusionados
    merged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    merged_by TEXT DEFAULT 'user',  -- 'user' o 'auto'
    undone_at TIMESTAMP DEFAULT NULL
);
```

---

## Atributos

```sql
CREATE TABLE attribute (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    attribute_type TEXT NOT NULL,  -- 'physical', 'psychological', 'social', 'background'
    attribute_key TEXT NOT NULL,   -- 'eye_color', 'age', 'profession'
    value TEXT NOT NULL,
    normalized_value TEXT,  -- Para comparación
    source_chapter INTEGER,
    source_page INTEGER,
    source_line INTEGER,
    source_excerpt TEXT,  -- Fragmento de texto original
    extraction_method TEXT DEFAULT 'auto',  -- 'auto', 'manual'
    confidence REAL DEFAULT 1.0,
    validated_by_user INTEGER DEFAULT 0
);

CREATE INDEX idx_attribute_entity ON attribute(entity_id);
CREATE INDEX idx_attribute_key ON attribute(entity_id, attribute_key);
```

---

## Relaciones entre Entidades

```sql
CREATE TABLE relationship (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    entity1_id INTEGER NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    entity2_id INTEGER NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,  -- 'family', 'friend', 'enemy', 'romantic', 'professional'
    relationship_detail TEXT,  -- 'father', 'brother', 'boss'
    source_chapter INTEGER,
    source_excerpt TEXT,
    confidence REAL DEFAULT 1.0,
    CHECK(entity1_id < entity2_id)  -- Evitar duplicados
);

CREATE INDEX idx_relationship_entities ON relationship(entity1_id, entity2_id);
```

---

## Diálogos y Voz

```sql
CREATE TABLE dialogue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapter(id) ON DELETE SET NULL,
    speaker_id INTEGER REFERENCES entity(id) ON DELETE SET NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    text_content TEXT NOT NULL,
    attribution_method TEXT DEFAULT 'proximity',  -- 'explicit', 'proximity', 'manual'
    attribution_confidence REAL DEFAULT 0.5
);

CREATE INDEX idx_dialogue_speaker ON dialogue(speaker_id);

CREATE TABLE voice_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    avg_sentence_length REAL,
    vocabulary_richness REAL,  -- TTR
    formality_score REAL,  -- 0-1
    common_phrases TEXT DEFAULT '[]',  -- JSON array de muletillas
    sample_dialogues TEXT DEFAULT '[]',  -- JSON array de ejemplos
    word_count INTEGER,  -- Total de palabras analizadas
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_id)
);
```

---

## Timeline y Eventos

```sql
CREATE TABLE event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    event_type TEXT DEFAULT 'general',  -- 'birth', 'death', 'marriage', 'travel', 'general'
    temporal_marker TEXT,  -- Expresión original: "tres días después"
    normalized_time TEXT,  -- Formato normalizado: "DAY+3"
    time_certainty TEXT DEFAULT 'uncertain',  -- 'exact', 'approximate', 'uncertain'
    chapter_id INTEGER REFERENCES chapter(id),
    source_excerpt TEXT,
    related_entities TEXT DEFAULT '[]'  -- JSON array de entity_ids
);

CREATE INDEX idx_event_project ON event(project_id);
```

---

## Alertas y Sistema de Historial

```sql
CREATE TABLE alert (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL,  -- 'attribute_inconsistency', 'name_variant', etc.
    severity TEXT NOT NULL CHECK(severity IN (
        'critical', 'warning', 'info', 'hint'
    )),
    confidence REAL NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    confidence_breakdown TEXT,  -- JSON: factores que contribuyen al %
    source_references TEXT NOT NULL,  -- JSON array de {chapter, page, excerpt}
    related_entity_ids TEXT DEFAULT '[]',  -- JSON array
    anchor_id INTEGER REFERENCES text_anchor(id),  -- Ancla para relocalización
    status TEXT DEFAULT 'new' CHECK(status IN (
        'new', 'reviewed', 'pending', 'dismissed', 'resolved',
        'verified', 'auto_resolved', 'reopened', 'obsolete'
    )),
    resolution_note TEXT,
    needs_reverification INTEGER DEFAULT 0,
    document_version INTEGER,  -- Versión donde se detectó
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX idx_alert_project_status ON alert(project_id, status);
CREATE INDEX idx_alert_type ON alert(alert_type);
CREATE INDEX idx_alert_anchor ON alert(anchor_id);

-- Historial de cambios de estado de alertas
CREATE TABLE alert_state_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL REFERENCES alert(id) ON DELETE CASCADE,
    from_state TEXT,  -- NULL para estado inicial
    to_state TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by TEXT DEFAULT 'user',  -- 'user', 'system', 'auto'
    reason TEXT,  -- 'manual', 'reanalysis', 'document_change', etc.
    note TEXT
);

CREATE INDEX idx_alert_history_alert ON alert_state_history(alert_id);
CREATE INDEX idx_alert_history_time ON alert_state_history(changed_at);
```

---

## Notas del Corrector

```sql
CREATE TABLE note (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapter(id) ON DELETE SET NULL,
    start_char INTEGER,
    end_char INTEGER,
    note_type TEXT DEFAULT 'general',  -- 'query_author', 'to_review', 'style', 'general'
    content TEXT NOT NULL,
    linked_entity_id INTEGER REFERENCES entity(id),
    linked_alert_id INTEGER REFERENCES alert(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_note_project ON note(project_id);
```

---

## Configuración y Preferencias

```sql
CREATE TABLE user_decision (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    decision_type TEXT NOT NULL,  -- 'name_normalization', 'entity_merge', 'threshold_adjust'
    decision_key TEXT NOT NULL,
    decision_value TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_decision_project ON user_decision(project_id);
```

---

## Triggers para Timestamps

```sql
-- Actualizar updated_at en project
CREATE TRIGGER update_project_timestamp
AFTER UPDATE ON project
BEGIN
    UPDATE project SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Actualizar updated_at en voice_profile
CREATE TRIGGER update_voice_profile_timestamp
AFTER UPDATE ON voice_profile
BEGIN
    UPDATE voice_profile SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

---

## Vistas Útiles

```sql
-- Resumen de entidades por proyecto
CREATE VIEW v_entity_summary AS
SELECT
    e.project_id,
    e.entity_type,
    e.canonical_name,
    e.importance,
    COUNT(DISTINCT tr.id) as mention_count,
    COUNT(DISTINCT a.id) as attribute_count,
    COUNT(DISTINCT al.id) FILTER (WHERE al.status = 'pending') as pending_alerts
FROM entity e
LEFT JOIN text_reference tr ON tr.entity_id = e.id
LEFT JOIN attribute a ON a.entity_id = e.id
LEFT JOIN alert al ON al.related_entity_ids LIKE '%' || e.id || '%'
GROUP BY e.id;

-- Alertas pendientes por severidad
CREATE VIEW v_pending_alerts AS
SELECT
    project_id,
    severity,
    alert_type,
    COUNT(*) as count
FROM alert
WHERE status = 'pending'
GROUP BY project_id, severity, alert_type
ORDER BY
    CASE severity
        WHEN 'critical' THEN 1
        WHEN 'warning' THEN 2
        WHEN 'info' THEN 3
        WHEN 'hint' THEN 4
    END;
```

---

## Siguiente

Ver [Puntos de Extensión](./extension-points.md) para añadir nuevas heurísticas.
