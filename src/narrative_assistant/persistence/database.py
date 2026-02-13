"""
Gestión de base de datos SQLite.

Incluye:
- Conexión segura con permisos restrictivos
- Migraciones de schema
- Transacciones y rollback
"""

import logging
import sqlite3
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from ..core.config import get_config

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_database_lock = threading.Lock()

# Versión del schema actual
SCHEMA_VERSION = 20

# Tablas esenciales que deben existir para una BD válida
# Solo incluir las tablas básicas definidas en SCHEMA_SQL
ESSENTIAL_TABLES = {
    "projects",
    "chapters",
    "entities",
    "entity_mentions",
    "alerts",
    "sessions",
    "correction_config_overrides",
}

# SQL de creación de tablas
SCHEMA_SQL = """
-- Proyectos (un manuscrito = un proyecto)
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    document_path TEXT,
    document_fingerprint TEXT NOT NULL,
    document_format TEXT NOT NULL,
    word_count INTEGER,
    chapter_count INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_opened_at TEXT,
    analysis_status TEXT DEFAULT 'pending',
    analysis_progress REAL DEFAULT 0.0,
    settings_json TEXT,

    -- Tipo de documento (versión 9)
    document_type TEXT DEFAULT 'FIC',       -- FIC, MEM, BIO, CEL, DIV, ENS, AUT, TEC, PRA, GRA, INF, DRA
    document_subtype TEXT,                  -- Subtipo específico según la categoría
    document_type_confirmed INTEGER DEFAULT 0,  -- 1 si el usuario ha confirmado el tipo
    detected_document_type TEXT,            -- Tipo detectado por el sistema (puede diferir del actual)

    -- Colección / saga (versión 14)
    collection_id INTEGER,
    collection_order INTEGER DEFAULT 0,

    -- Demo project (versión 17) — no cuenta para cuota de licencia
    is_demo INTEGER DEFAULT 0,

    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE SET NULL
);

-- Índice para búsqueda por fingerprint
CREATE INDEX IF NOT EXISTS idx_projects_fingerprint ON projects(document_fingerprint);

-- Capítulos detectados
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_number INTEGER NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    word_count INTEGER,
    structure_type TEXT DEFAULT 'chapter',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    -- Métricas de enriquecimiento (computadas post-análisis)
    dialogue_ratio REAL,
    avg_sentence_length REAL,
    scene_count INTEGER,
    characters_present_count INTEGER,
    pov_character TEXT,
    dominant_tone TEXT,
    tone_intensity REAL,
    reading_time_minutes INTEGER,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chapters_project ON chapters(project_id);

-- Secciones dentro de capítulos (H2, H3, H4)
CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    parent_section_id INTEGER,  -- NULL si es sección de nivel superior, sino ID de la sección padre
    section_number INTEGER NOT NULL,
    title TEXT,
    heading_level INTEGER NOT NULL,  -- 2=H2, 3=H3, 4=H4, etc.
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_section_id) REFERENCES sections(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sections_project ON sections(project_id);
CREATE INDEX IF NOT EXISTS idx_sections_chapter ON sections(chapter_id);
CREATE INDEX IF NOT EXISTS idx_sections_parent ON sections(parent_section_id);

-- Entidades (personajes, lugares, objetos)
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL,  -- character, location, object, organization
    canonical_name TEXT NOT NULL,
    importance TEXT DEFAULT 'secondary',  -- protagonist, secondary, minor, mentioned
    description TEXT,
    first_appearance_char INTEGER,
    mention_count INTEGER DEFAULT 0,
    merged_from_ids TEXT,  -- JSON array de IDs fusionados
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);

-- Menciones de entidades en el texto
CREATE TABLE IF NOT EXISTS entity_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    chapter_id INTEGER,
    surface_form TEXT NOT NULL,  -- Texto tal como aparece
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    context_before TEXT,
    context_after TEXT,
    confidence REAL DEFAULT 1.0,
    source TEXT DEFAULT 'ner',  -- ner, coref, manual, gazetteer
    metadata TEXT,  -- JSON con datos adicionales (voting_detail para coref)
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_mentions_entity ON entity_mentions(entity_id);
CREATE INDEX IF NOT EXISTS idx_mentions_chapter ON entity_mentions(chapter_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mentions_unique_position ON entity_mentions(entity_id, start_char, end_char);

-- Atributos de entidades
CREATE TABLE IF NOT EXISTS entity_attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    attribute_type TEXT NOT NULL,  -- physical, psychological, social, role
    attribute_key TEXT NOT NULL,
    attribute_value TEXT NOT NULL,
    source_mention_id INTEGER,
    chapter_id INTEGER,                  -- S8a-06: capítulo donde se detectó el atributo
    confidence REAL DEFAULT 1.0,
    is_verified INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (source_mention_id) REFERENCES entity_mentions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_attributes_entity ON entity_attributes(entity_id);

-- Evidencias de atributos (múltiples ubicaciones para un mismo atributo)
CREATE TABLE IF NOT EXISTS attribute_evidences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attribute_id INTEGER NOT NULL,

    -- Ubicación en el documento
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    chapter INTEGER,
    page INTEGER,           -- Calculado con calculate_page_and_line()
    line INTEGER,           -- Calculado con calculate_page_and_line()

    -- Contexto
    excerpt TEXT NOT NULL,

    -- Metadata de extracción
    extraction_method TEXT NOT NULL,  -- direct_description, action_inference, dialogue, unknown
    keywords TEXT,                    -- JSON array: ["decidida", "determinación"]
    confidence REAL DEFAULT 1.0,

    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (attribute_id) REFERENCES entity_attributes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_evidence_attribute ON attribute_evidences(attribute_id);
CREATE INDEX IF NOT EXISTS idx_evidence_chapter ON attribute_evidences(chapter);

-- Alertas generadas (sistema centralizado)
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,

    -- Clasificación
    category TEXT NOT NULL,  -- consistency, style, focalization, structure, world, entity, other
    severity TEXT NOT NULL,  -- critical, warning, info, hint
    alert_type TEXT NOT NULL,  -- Tipo específico (attribute_inconsistency, lexical_repetition, etc.)

    -- Contenido
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    explanation TEXT NOT NULL,
    suggestion TEXT,

    -- Ubicación
    chapter INTEGER,
    scene INTEGER,
    start_char INTEGER,
    end_char INTEGER,
    excerpt TEXT DEFAULT '',

    -- Entidades relacionadas (JSON array de IDs)
    entity_ids TEXT DEFAULT '[]',

    -- Metadata
    confidence REAL DEFAULT 0.8,
    source_module TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,

    -- Estado
    status TEXT DEFAULT 'new',  -- new, open, acknowledged, in_progress, resolved, dismissed, auto_resolved
    resolved_at TEXT,
    resolution_note TEXT DEFAULT '',

    -- Datos adicionales específicos del tipo (JSON)
    extra_data TEXT DEFAULT '{}',

    -- Hash de contenido para persistir dismissals entre re-análisis (versión 12)
    content_hash TEXT DEFAULT '',

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alerts_project ON alerts(project_id);
CREATE INDEX IF NOT EXISTS idx_alerts_content_hash ON alerts(content_hash);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_category ON alerts(category);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_chapter ON alerts(chapter);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_project_status ON alerts(project_id, status);

-- Historial de acciones del revisor
CREATE TABLE IF NOT EXISTS review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,  -- alert_resolved, alert_dismissed, entity_merged, etc.
    target_type TEXT,  -- alert, entity, attribute
    target_id INTEGER,
    old_value_json TEXT,
    new_value_json TEXT,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_history_project ON review_history(project_id);
CREATE INDEX IF NOT EXISTS idx_history_action ON review_history(action_type);

-- Sesiones de trabajo
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at TEXT,
    duration_seconds INTEGER,
    alerts_reviewed INTEGER DEFAULT 0,
    alerts_resolved INTEGER DEFAULT 0,
    entities_merged INTEGER DEFAULT 0,
    last_position_char INTEGER,
    last_chapter_id INTEGER,
    notes TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);

-- Declaraciones de focalización
CREATE TABLE IF NOT EXISTS focalization_declarations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    scene INTEGER,  -- NULL = todo el capítulo

    -- Tipo y focalizadores
    focalization_type TEXT NOT NULL,  -- zero, internal_fixed, internal_variable, internal_multiple, external
    focalizer_ids TEXT,  -- JSON array de entity IDs

    -- Metadata
    declared_at TEXT NOT NULL DEFAULT (datetime('now')),
    declared_by TEXT DEFAULT 'user',  -- 'user' o 'system_suggestion'
    notes TEXT,

    -- Validación
    is_validated INTEGER DEFAULT 0,
    violations_count INTEGER DEFAULT 0,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id, chapter, scene)
);

CREATE INDEX IF NOT EXISTS idx_focalization_project ON focalization_declarations(project_id);
CREATE INDEX IF NOT EXISTS idx_focalization_chapter ON focalization_declarations(project_id, chapter);

-- Reglas editoriales personalizadas por proyecto
CREATE TABLE IF NOT EXISTS editorial_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    rules_text TEXT NOT NULL,  -- Texto libre con las reglas del corrector
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id)  -- Solo un registro de reglas por proyecto
);

CREATE INDEX IF NOT EXISTS idx_editorial_rules_project ON editorial_rules(project_id);

-- Entidades rechazadas por el usuario (feedback loop para validación NER)
CREATE TABLE IF NOT EXISTS rejected_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    entity_text TEXT NOT NULL,  -- Texto normalizado (lowercase) de la entidad rechazada
    rejection_reason TEXT,      -- Razón opcional del rechazo
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id, entity_text)  -- Una entidad solo puede rechazarse una vez por proyecto
);

CREATE INDEX IF NOT EXISTS idx_rejected_entities_project ON rejected_entities(project_id);

-- Metadatos del schema
CREATE TABLE IF NOT EXISTS schema_info (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Timeline: Eventos temporales del proyecto
CREATE TABLE IF NOT EXISTS timeline_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    event_id TEXT NOT NULL,              -- ID único del evento en el timeline
    chapter INTEGER,
    paragraph INTEGER,
    description TEXT NOT NULL,
    story_date TEXT,                     -- Fecha en la historia (ISO format o NULL)
    story_date_resolution TEXT,          -- EXACT_DATE, MONTH, YEAR, SEASON, RELATIVE, UNKNOWN
    narrative_order TEXT DEFAULT 'CHRONOLOGICAL',  -- CHRONOLOGICAL, ANALEPSIS, PROLEPSIS
    discourse_position INTEGER,          -- Orden en el discurso narrativo
    confidence REAL DEFAULT 0.5,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_timeline_events_project ON timeline_events(project_id);
CREATE INDEX IF NOT EXISTS idx_timeline_events_chapter ON timeline_events(chapter);

-- Timeline: Marcadores temporales extraídos del texto
CREATE TABLE IF NOT EXISTS temporal_markers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    marker_type TEXT NOT NULL,           -- ABSOLUTE_DATE, RELATIVE_TIME, SEASON_EPOCH, CHARACTER_AGE, DURATION, FREQUENCY
    text TEXT NOT NULL,                  -- Texto original del marcador
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    confidence REAL DEFAULT 0.5,
    -- Componentes parseados (para fechas absolutas)
    year INTEGER,
    month INTEGER,
    day INTEGER,
    -- Para marcadores relativos
    direction TEXT,                      -- past, future
    quantity INTEGER,
    magnitude TEXT,                      -- days, weeks, months, years
    -- Para edades de personajes
    age INTEGER,
    entity_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_temporal_markers_project ON temporal_markers(project_id);
CREATE INDEX IF NOT EXISTS idx_temporal_markers_chapter ON temporal_markers(chapter);

-- ===================================================================
-- NUEVAS TABLAS: Persistencia de resultados de análisis (versión 6)
-- ===================================================================

-- Ejecuciones de análisis
CREATE TABLE IF NOT EXISTS analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    session_id INTEGER,
    config_json TEXT,                    -- UnifiedConfig serializado
    quality_profile TEXT,                -- 'express', 'standard', 'deep', 'complete'
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    status TEXT DEFAULT 'running',       -- 'running', 'completed', 'failed', 'cancelled'
    error_message TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_project ON analysis_runs(project_id);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_status ON analysis_runs(status);

-- Fases de análisis ejecutadas en cada run
CREATE TABLE IF NOT EXISTS analysis_phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    phase_name TEXT NOT NULL,            -- 'parsing', 'ner', 'coreference', 'attributes', 'relationships', etc.
    executed INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    result_count INTEGER DEFAULT 0,      -- Número de items encontrados
    error_message TEXT,
    metadata_json TEXT,                  -- Metadata adicional de la fase
    FOREIGN KEY (run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_analysis_phases_run ON analysis_phases(run_id);
CREATE INDEX IF NOT EXISTS idx_analysis_phases_name ON analysis_phases(phase_name);

-- Relaciones entre entidades
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    entity1_id INTEGER NOT NULL,
    entity2_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,         -- 'FAMILY', 'ROMANTIC', 'PROFESSIONAL', 'FRIENDSHIP', 'RIVALRY', 'HIERARCHICAL'
    subtype TEXT,                        -- 'hermano', 'esposo', 'jefe', 'mentor', etc.
    direction TEXT DEFAULT 'bidirectional',  -- 'bidirectional', 'from_1_to_2', 'from_2_to_1'
    confidence REAL DEFAULT 0.8,
    chapter_id INTEGER,
    start_char INTEGER,
    end_char INTEGER,
    source_text TEXT,
    detection_method TEXT,               -- 'pattern', 'clustering', 'llm', 'dependency'
    is_inferred INTEGER DEFAULT 0,       -- 1 si fue inferido, 0 si explícito
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (entity1_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (entity2_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_relationships_project ON relationships(project_id);
CREATE INDEX IF NOT EXISTS idx_relationships_entity1 ON relationships(entity1_id);
CREATE INDEX IF NOT EXISTS idx_relationships_entity2 ON relationships(entity2_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relation_type);

-- Interacciones entre entidades
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    entity1_id INTEGER NOT NULL,
    entity2_id INTEGER,                  -- NULL para acciones unilaterales
    interaction_type TEXT NOT NULL,      -- 'DIALOGUE', 'PHYSICAL', 'THOUGHT', 'OBSERVATION', 'REFERENCE'
    tone TEXT DEFAULT 'NEUTRAL',         -- 'POSITIVE', 'NEGATIVE', 'NEUTRAL', 'MIXED'
    intensity REAL DEFAULT 0.5,          -- 0.0 - 1.0
    chapter_id INTEGER,
    position INTEGER,
    start_char INTEGER,
    end_char INTEGER,
    text_excerpt TEXT,
    is_in_dialogue INTEGER DEFAULT 0,    -- 1 si ocurre dentro de diálogo
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (entity1_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (entity2_id) REFERENCES entities(id) ON DELETE SET NULL,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_interactions_project ON interactions(project_id);
CREATE INDEX IF NOT EXISTS idx_interactions_entity1 ON interactions(entity1_id);
CREATE INDEX IF NOT EXISTS idx_interactions_chapter ON interactions(chapter_id);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON interactions(interaction_type);

-- Cambios de registro detectados
CREATE TABLE IF NOT EXISTS register_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    from_register TEXT NOT NULL,         -- 'formal', 'coloquial', 'tecnico', 'poetico'
    to_register TEXT NOT NULL,
    chapter_id INTEGER,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    position INTEGER,
    text_excerpt TEXT,
    severity TEXT DEFAULT 'medium',      -- 'low', 'medium', 'high'
    explanation TEXT,
    confidence REAL DEFAULT 0.8,
    is_justified INTEGER DEFAULT 0,      -- 1 si es cambio intencionado (diálogo, cita)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_register_changes_project ON register_changes(project_id);
CREATE INDEX IF NOT EXISTS idx_register_changes_chapter ON register_changes(chapter_id);

-- Métricas de pacing por capítulo
CREATE TABLE IF NOT EXISTS pacing_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    sentence_count INTEGER,
    paragraph_count INTEGER,
    dialogue_count INTEGER,              -- Número de diálogos
    dialogue_ratio REAL,                 -- 0.0 - 1.0
    avg_sentence_length REAL,
    avg_paragraph_length REAL,
    lexical_density REAL,                -- Type-token ratio
    unique_words INTEGER,
    longest_sentence_words INTEGER,
    action_verb_ratio REAL,              -- Ratio de verbos de acción
    pacing_score REAL,                   -- 0.0 (lento) - 1.0 (rápido)
    balance_deviation REAL,              -- Desviación respecto a la media del libro
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
    UNIQUE (project_id, chapter_id)
);

CREATE INDEX IF NOT EXISTS idx_pacing_metrics_project ON pacing_metrics(project_id);
CREATE INDEX IF NOT EXISTS idx_pacing_metrics_chapter ON pacing_metrics(chapter_id);

-- Arcos emocionales (sentimiento por segmento)
CREATE TABLE IF NOT EXISTS emotional_arcs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    segment_index INTEGER NOT NULL,      -- Índice del segmento dentro del capítulo
    segment_start INTEGER NOT NULL,
    segment_end INTEGER NOT NULL,
    sentiment_label TEXT,                -- 'positive', 'negative', 'neutral'
    sentiment_score REAL,                -- -1.0 (negativo) a 1.0 (positivo)
    dominant_emotion TEXT,               -- 'joy', 'sadness', 'anger', 'fear', 'surprise', 'disgust'
    emotion_confidence REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_emotional_arcs_project ON emotional_arcs(project_id);
CREATE INDEX IF NOT EXISTS idx_emotional_arcs_chapter ON emotional_arcs(chapter_id);

-- Perfiles de voz por personaje
CREATE TABLE IF NOT EXISTS voice_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    avg_sentence_length REAL,
    vocabulary_richness REAL,            -- Type-token ratio
    formality_score REAL,                -- 0 (informal) - 1 (formal)
    dialogue_count INTEGER,              -- Número de diálogos analizados
    characteristic_words TEXT,           -- JSON array de palabras características
    filler_words TEXT,                   -- JSON array de muletillas
    exclamation_ratio REAL,
    question_ratio REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    UNIQUE (project_id, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_voice_profiles_project ON voice_profiles(project_id);
CREATE INDEX IF NOT EXISTS idx_voice_profiles_entity ON voice_profiles(entity_id);

-- Eventos de estado vital: muertes y apariciones post-mortem (S8a-03)
CREATE TABLE IF NOT EXISTS vital_status_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    entity_name TEXT NOT NULL,
    event_type TEXT NOT NULL,             -- 'death' | 'post_mortem_appearance'
    chapter INTEGER NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    excerpt TEXT,
    confidence REAL DEFAULT 0.5,
    -- Campos específicos de muerte
    death_type TEXT,                      -- 'direct', 'narrated', 'reported', 'implied'
    -- Campos específicos de aparición post-mortem
    death_chapter INTEGER,               -- En qué capítulo murió (para post_mortem)
    appearance_type TEXT,                 -- 'dialogue', 'action', 'narration'
    is_valid INTEGER DEFAULT 0,          -- 1 si es flashback/recuerdo válido
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vital_status_project ON vital_status_events(project_id);
CREATE INDEX IF NOT EXISTS idx_vital_status_entity ON vital_status_events(entity_id);

-- Eventos de ubicación de personajes (S8a-04)
CREATE TABLE IF NOT EXISTS character_location_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    entity_name TEXT NOT NULL,
    location_name TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    excerpt TEXT,
    change_type TEXT NOT NULL,            -- 'arrival', 'departure', 'presence', 'implied'
    confidence REAL DEFAULT 0.5,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_char_location_project ON character_location_events(project_id);
CREATE INDEX IF NOT EXISTS idx_char_location_entity ON character_location_events(entity_id);

-- Eventos out-of-character (S8a-05)
CREATE TABLE IF NOT EXISTS ooc_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    entity_name TEXT NOT NULL,
    deviation_type TEXT NOT NULL,         -- 'register', 'formality', 'vocabulary', etc.
    severity TEXT NOT NULL,               -- 'low', 'medium', 'high'
    description TEXT,
    expected TEXT,
    actual TEXT,
    chapter INTEGER,
    excerpt TEXT,
    confidence REAL DEFAULT 0.5,
    is_intentional INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ooc_events_project ON ooc_events(project_id);
CREATE INDEX IF NOT EXISTS idx_ooc_events_entity ON ooc_events(entity_id);

-- ===================================================================
-- NUEVAS TABLAS: Sistema híbrido de filtros de entidades (versión 7)
-- ===================================================================

-- Patrones de falsos positivos del sistema (predefinidos, solo lectura para usuario)
-- El usuario solo puede activar/desactivar patrones, no modificarlos
CREATE TABLE IF NOT EXISTS system_entity_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,                -- Texto o patrón regex
    pattern_type TEXT NOT NULL,           -- 'exact', 'regex', 'startswith', 'endswith', 'contains'
    entity_type TEXT,                     -- NULL = aplica a todos los tipos
    language TEXT DEFAULT 'es',           -- Idioma al que aplica
    category TEXT,                        -- Categoría (temporal, numeric, article, etc.)
    description TEXT,                     -- Descripción para mostrar al usuario
    is_active INTEGER DEFAULT 1,          -- Si el usuario ha activado/desactivado este patrón
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (pattern, pattern_type, entity_type, language)
);

CREATE INDEX IF NOT EXISTS idx_system_patterns_active ON system_entity_patterns(is_active);
CREATE INDEX IF NOT EXISTS idx_system_patterns_type ON system_entity_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_system_patterns_language ON system_entity_patterns(language);

-- Entidades rechazadas a nivel global del usuario (aplica a todos sus proyectos)
CREATE TABLE IF NOT EXISTS user_rejected_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT NOT NULL,            -- Texto normalizado (lowercase)
    entity_type TEXT,                     -- Tipo de entidad (NULL = todos los tipos)
    reason TEXT,                          -- Razón del rechazo
    rejected_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (entity_name, entity_type)     -- Una entidad/tipo solo puede rechazarse una vez
);

CREATE INDEX IF NOT EXISTS idx_user_rejected_name ON user_rejected_entities(entity_name);
CREATE INDEX IF NOT EXISTS idx_user_rejected_type ON user_rejected_entities(entity_type);

-- Overrides a nivel de proyecto (máxima prioridad)
-- Permite rechazar o forzar inclusión de entidades específicas por proyecto
CREATE TABLE IF NOT EXISTS project_entity_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    entity_name TEXT NOT NULL,            -- Texto normalizado (lowercase)
    entity_type TEXT,                     -- Tipo de entidad (NULL = todos los tipos)
    action TEXT NOT NULL,                 -- 'reject' o 'force_include'
    reason TEXT,                          -- Razón del override
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id, entity_name, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_project_overrides_project ON project_entity_overrides(project_id);
CREATE INDEX IF NOT EXISTS idx_project_overrides_action ON project_entity_overrides(action);

-- ===================================================================
-- NUEVAS TABLAS: Sistema de etiquetado de escenas (versión 8)
-- ===================================================================

-- Escenas detectadas y persistidas
CREATE TABLE IF NOT EXISTS scenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    scene_number INTEGER NOT NULL,         -- 1-indexed within chapter
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    separator_type TEXT,                   -- asterisk, dash, hash, blank_lines, none
    word_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
    UNIQUE (project_id, chapter_id, scene_number)
);

CREATE INDEX IF NOT EXISTS idx_scenes_project ON scenes(project_id);
CREATE INDEX IF NOT EXISTS idx_scenes_chapter ON scenes(chapter_id);

-- Etiquetas predefinidas de escenas (una fila por escena)
CREATE TABLE IF NOT EXISTS scene_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,

    -- Tipo de escena (predefinido)
    scene_type TEXT,                       -- action, dialogue, exposition, introspection, flashback, dream, transition

    -- Tono emocional (predefinido)
    tone TEXT,                             -- tense, calm, happy, sad, romantic, mysterious, ominous, hopeful, nostalgic, neutral

    -- Ubicación (enlazado a entidad tipo location)
    location_entity_id INTEGER,

    -- Personajes presentes en la escena (JSON array de entity IDs)
    participant_ids TEXT DEFAULT '[]',

    -- Resumen y notas del usuario
    summary TEXT,
    notes TEXT,

    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE CASCADE,
    FOREIGN KEY (location_entity_id) REFERENCES entities(id) ON DELETE SET NULL,
    UNIQUE (scene_id)
);

CREATE INDEX IF NOT EXISTS idx_scene_tags_scene ON scene_tags(scene_id);
CREATE INDEX IF NOT EXISTS idx_scene_tags_type ON scene_tags(scene_type);
CREATE INDEX IF NOT EXISTS idx_scene_tags_tone ON scene_tags(tone);
CREATE INDEX IF NOT EXISTS idx_scene_tags_location ON scene_tags(location_entity_id);

-- Etiquetas personalizadas del usuario (múltiples por escena)
CREATE TABLE IF NOT EXISTS scene_custom_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    tag_name TEXT NOT NULL,                -- Nombre de la etiqueta definida por el usuario
    tag_color TEXT,                        -- Color hex opcional (#FF5733)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_custom_tags_scene ON scene_custom_tags(scene_id);
CREATE INDEX IF NOT EXISTS idx_custom_tags_name ON scene_custom_tags(tag_name);

-- Catálogo de etiquetas personalizadas por proyecto (para reutilización)
CREATE TABLE IF NOT EXISTS project_custom_tag_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    tag_name TEXT NOT NULL,
    tag_color TEXT,                        -- Color por defecto para esta etiqueta
    usage_count INTEGER DEFAULT 0,         -- Número de veces usada
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id, tag_name)
);

CREATE INDEX IF NOT EXISTS idx_tag_catalog_project ON project_custom_tag_catalog(project_id);

-- Overrides de configuración de corrección por tipo/subtipo (versión 10)
-- Permite al usuario personalizar los defaults de tipos/subtipos sin modificar código
CREATE TABLE IF NOT EXISTS correction_config_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_code TEXT NOT NULL,              -- 'FIC', 'MEM', 'INF', etc.
    subtype_code TEXT,                    -- NULL = override de tipo, valor = override de subtipo
    overrides_json TEXT NOT NULL,         -- JSON con los parámetros modificados (solo delta)
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (type_code, subtype_code)      -- Una fila por combinación tipo/subtipo
);

CREATE INDEX IF NOT EXISTS idx_config_overrides_type ON correction_config_overrides(type_code);

-- Correcciones manuales de correferencias (versión 11)
CREATE TABLE IF NOT EXISTS coreference_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    mention_start_char INTEGER NOT NULL,
    mention_end_char INTEGER NOT NULL,
    mention_text TEXT NOT NULL,
    chapter_number INTEGER,
    original_entity_id INTEGER,          -- Asignación automática original (NULL si sin asignar)
    corrected_entity_id INTEGER,         -- Asignación manual del usuario (NULL = desvincular)
    correction_type TEXT NOT NULL DEFAULT 'reassign',  -- reassign, unlink, confirm
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (original_entity_id) REFERENCES entities(id) ON DELETE SET NULL,
    FOREIGN KEY (corrected_entity_id) REFERENCES entities(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_coref_corrections_project ON coreference_corrections(project_id);
CREATE INDEX IF NOT EXISTS idx_coref_corrections_mention ON coreference_corrections(project_id, mention_start_char, mention_end_char);

-- Correcciones manuales de atribución de diálogos (versión 11)
CREATE TABLE IF NOT EXISTS speaker_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_number INTEGER NOT NULL,
    dialogue_start_char INTEGER NOT NULL,
    dialogue_end_char INTEGER NOT NULL,
    dialogue_text TEXT NOT NULL,
    original_speaker_id INTEGER,          -- Hablante asignado automáticamente (NULL si no asignado)
    corrected_speaker_id INTEGER,         -- Hablante correcto según el usuario
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (original_speaker_id) REFERENCES entities(id) ON DELETE SET NULL,
    FOREIGN KEY (corrected_speaker_id) REFERENCES entities(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_speaker_corrections_project ON speaker_corrections(project_id);
CREATE INDEX IF NOT EXISTS idx_speaker_corrections_chapter ON speaker_corrections(project_id, chapter_number);

-- ===================================================================
-- NUEVAS TABLAS: Persistencia de dismissals (versión 12)
-- ===================================================================

-- Dismissals de alertas (persisten entre re-análisis vía content_hash)
CREATE TABLE IF NOT EXISTS alert_dismissals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    content_hash TEXT NOT NULL,          -- Hash del contenido de la alerta (match entre reruns)
    scope TEXT NOT NULL DEFAULT 'instance',  -- instance, document, project
    reason TEXT DEFAULT '',              -- Razón del descarte (false_positive, not_applicable, etc.)
    alert_type TEXT DEFAULT '',          -- Tipo de alerta (para estadísticas)
    source_module TEXT DEFAULT '',       -- Módulo fuente (para estadísticas)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id, content_hash)   -- Un hash solo puede descartarse una vez por proyecto
);

CREATE INDEX IF NOT EXISTS idx_dismissals_project ON alert_dismissals(project_id);
CREATE INDEX IF NOT EXISTS idx_dismissals_hash ON alert_dismissals(content_hash);
CREATE INDEX IF NOT EXISTS idx_dismissals_type ON alert_dismissals(alert_type);

-- Calibración de confianza por detector (versión 18, BK-22)
CREATE TABLE IF NOT EXISTS detector_calibration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    alert_type TEXT NOT NULL,
    source_module TEXT NOT NULL DEFAULT '',
    total_alerts INTEGER DEFAULT 0,
    total_dismissed INTEGER DEFAULT 0,
    fp_rate REAL DEFAULT 0.0,            -- ratio false positives
    calibration_factor REAL DEFAULT 1.0, -- multiplicador: effective = original * factor
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id, alert_type, source_module)
);

CREATE INDEX IF NOT EXISTS idx_calibration_project ON detector_calibration(project_id);

-- Reglas de supresión definidas por el usuario
CREATE TABLE IF NOT EXISTS suppression_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,                  -- NULL = regla global (todos los proyectos)
    rule_type TEXT NOT NULL,             -- alert_type, category, entity, source_module
    pattern TEXT NOT NULL,               -- Patrón a suprimir (ej: "attribute_inconsistency", "spelling_*")
    entity_name TEXT,                    -- Si rule_type='entity', nombre de la entidad
    reason TEXT DEFAULT '',              -- Explicación de la regla
    is_active INTEGER DEFAULT 1,         -- Si la regla está activa
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_suppression_project ON suppression_rules(project_id);
CREATE INDEX IF NOT EXISTS idx_suppression_active ON suppression_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_suppression_type ON suppression_rules(rule_type);

-- ===================================================================
-- NUEVAS TABLAS: Snapshots de análisis (versión 14, BK-05)
-- ===================================================================

-- Snapshots de análisis (una foto del estado antes de re-analizar)
CREATE TABLE IF NOT EXISTS analysis_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    document_fingerprint TEXT,
    alert_count INTEGER DEFAULT 0,
    entity_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'complete',      -- complete, partial
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snapshots_project ON analysis_snapshots(project_id);

-- Alertas capturadas en el snapshot
CREATE TABLE IF NOT EXISTS snapshot_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    alert_type TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    chapter INTEGER,
    start_char INTEGER,
    end_char INTEGER,
    excerpt TEXT DEFAULT '',
    content_hash TEXT DEFAULT '',
    confidence REAL DEFAULT 0.8,
    entity_ids TEXT DEFAULT '[]',
    related_entity_names TEXT DEFAULT '[]',
    extra_data TEXT DEFAULT '{}',
    FOREIGN KEY (snapshot_id) REFERENCES analysis_snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snap_alerts_snapshot ON snapshot_alerts(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_snap_alerts_project ON snapshot_alerts(project_id, snapshot_id);
CREATE INDEX IF NOT EXISTS idx_snap_alerts_hash ON snapshot_alerts(content_hash);

-- Entidades capturadas en el snapshot
CREATE TABLE IF NOT EXISTS snapshot_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    original_entity_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    aliases TEXT DEFAULT '[]',
    importance TEXT DEFAULT 'secondary',
    mention_count INTEGER DEFAULT 0,
    FOREIGN KEY (snapshot_id) REFERENCES analysis_snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snap_entities_snapshot ON snapshot_entities(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_snap_entities_project ON snapshot_entities(project_id, snapshot_id);

-- ===================================================================
-- NUEVAS TABLAS: Colecciones / Sagas (versión 14, BK-07)
-- ===================================================================

-- Colecciones (agrupación de proyectos en saga/serie)
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Enlaces de entidades entre libros de una colección
CREATE TABLE IF NOT EXISTS collection_entity_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL,
    source_entity_id INTEGER NOT NULL,
    target_entity_id INTEGER NOT NULL,
    source_project_id INTEGER NOT NULL,
    target_project_id INTEGER NOT NULL,
    similarity REAL DEFAULT 1.0,
    match_type TEXT DEFAULT 'manual',    -- manual, suggested_accepted
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
    FOREIGN KEY (source_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (source_project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (target_project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (collection_id, source_entity_id, target_entity_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_links_collection ON collection_entity_links(collection_id);
CREATE INDEX IF NOT EXISTS idx_entity_links_source ON collection_entity_links(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_links_target ON collection_entity_links(target_entity_id);

-- Cache de enrichment (S8a-11): resultados pre-computados de análisis derivados
-- Evita recomputar on-the-fly cuando el usuario abre un tab
CREATE TABLE IF NOT EXISTS enrichment_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    enrichment_type TEXT NOT NULL,       -- e.g. 'character_network', 'voice_profiles', 'echo_report'
    entity_scope TEXT,                   -- NULL=global, 'entity:42'=per-entity scope
    status TEXT NOT NULL DEFAULT 'pending',  -- pending/computing/completed/failed/stale
    input_hash TEXT,                     -- hash of inputs (for invalidation)
    output_hash TEXT,                    -- hash of output (for early cutoff)
    result_json TEXT,                    -- JSON blob with cached result
    error_message TEXT,                  -- error details if status='failed'
    phase INTEGER,                      -- pipeline phase that produced this (10-13)
    revision INTEGER NOT NULL DEFAULT 0,
    computed_at TEXT,                    -- timestamp of last successful computation
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id, enrichment_type, entity_scope)
);

CREATE INDEX IF NOT EXISTS idx_enrichment_project ON enrichment_cache(project_id);
CREATE INDEX IF NOT EXISTS idx_enrichment_type ON enrichment_cache(project_id, enrichment_type);
CREATE INDEX IF NOT EXISTS idx_enrichment_status ON enrichment_cache(project_id, status);

-- Eventos de invalidación granular (S8c)
CREATE TABLE IF NOT EXISTS invalidation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,             -- merge, undo_merge, reject, attribute_create, attribute_edit, attribute_delete
    entity_ids TEXT NOT NULL DEFAULT '[]', -- JSON array of affected entity IDs
    detail TEXT,                          -- JSON with event-specific details
    revision INTEGER NOT NULL DEFAULT 1,  -- monotonically increasing per project
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_invalidation_project ON invalidation_events(project_id);
CREATE INDEX IF NOT EXISTS idx_invalidation_revision ON invalidation_events(project_id, revision);

-- Glosario de usuario → inyección en NER (BK-17)
CREATE TABLE IF NOT EXISTS user_glossary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    term TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT 'PER',  -- PER, LOC, ORG, MISC
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id, term, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_glossary_project ON user_glossary(project_id);

-- Insertar versión del schema
INSERT OR REPLACE INTO schema_info (key, value) VALUES ('version', '20');
"""


class Database:
    """
    Conexión a base de datos SQLite con medidas de seguridad.

    Características:
    - Permisos restrictivos en archivo (solo owner)
    - WAL mode para mejor concurrencia
    - Foreign keys habilitadas
    - Transacciones explícitas
    """

    def __init__(self, db_path: Path | None = None):
        """
        Inicializa conexión a base de datos.

        Args:
            db_path: Ruta al archivo SQLite. Si None, usa config.
        """
        config = get_config()
        self.db_path = db_path or config.db_path
        logger.info(
            f"Database.__init__: db_path param={db_path}, config.db_path={config.db_path}"
        )
        logger.info(f"Database.__init__: usando db_path={self.db_path}")
        self._is_memory = self.db_path == ":memory:" or (
            isinstance(self.db_path, str) and self.db_path.startswith(":")
        )
        # Para :memory: mantenemos una conexión persistente
        self._shared_connection: sqlite3.Connection | None = None
        self._ensure_secure_permissions()
        self._initialize_schema()

    def _ensure_secure_permissions(self) -> None:
        """Asegura que solo el owner pueda acceder al archivo (Unix only)."""
        # chmod no funciona en Windows
        if sys.platform == "win32":
            return

        # Si es :memory: o db_path es un string especial, no hacer nada
        if isinstance(self.db_path, str):
            if self.db_path == ":memory:" or self.db_path.startswith(":"):
                return
            self.db_path = Path(self.db_path)

        if self.db_path.exists():
            self.db_path.chmod(0o600)

        # Lo mismo para WAL y journal
        for suffix in ["-wal", "-shm", "-journal"]:
            aux_path = Path(str(self.db_path) + suffix)
            if aux_path.exists():
                aux_path.chmod(0o600)

    def _initialize_schema(self) -> None:
        """Crea tablas si no existen. Detecta BD corrupta y la recrea si es necesario."""
        logger.info(f"[DB_INIT] Inicializando schema en: {self.db_path}")
        logger.info(
            f"[DB_INIT] db_path type: {type(self.db_path)}, is_memory: {self._is_memory}"
        )
        logger.info(f"[DB_INIT] db_path resolved: {self.db_path}")

        # Verificar si el archivo existe y tiene contenido
        if not self._is_memory and isinstance(self.db_path, Path):
            logger.info(f"[DB_INIT] Parent dir exists: {self.db_path.parent.exists()}")
            logger.info(f"[DB_INIT] Parent dir: {self.db_path.parent}")
            if self.db_path.exists():
                size = self.db_path.stat().st_size
                logger.info(f"[DB_INIT] Archivo DB existente, tamaño: {size} bytes")

                if size == 0:
                    # Empty file (e.g., from a previous failed init) - delete and recreate
                    logger.warning(
                        "[DB_INIT] DB file exists but is empty (0 bytes), deleting to recreate"
                    )
                    self.db_path.unlink()
                else:
                    # Verificar integridad de la BD existente
                    try:
                        self._verify_and_repair_schema()
                        logger.info("[DB_INIT] Schema verificado OK, retornando")
                        return  # BD válida, no hacer nada más
                    except Exception as e:
                        logger.warning(
                            f"[DB_INIT] BD posiblemente corrupta: {e}. Eliminando para recrear..."
                        )
                        # Delete the corrupt file and all auxiliary files
                        try:
                            self.db_path.unlink()
                            for suffix in ["-wal", "-shm", "-journal"]:
                                aux_path = Path(str(self.db_path) + suffix)
                                if aux_path.exists():
                                    aux_path.unlink()
                                    logger.info(
                                        f"[DB_INIT] Eliminado archivo auxiliar corrupto: {aux_path}"
                                    )
                        except Exception as del_err:
                            logger.error(
                                f"[DB_INIT] Error eliminando BD corrupta: {del_err}"
                            )
            else:
                logger.info(
                    f"[DB_INIT] Archivo DB no existe, se creará nuevo en: {self.db_path}"
                )

        # Crear schema desde cero
        logger.info("[DB_INIT] Llamando _create_schema_from_scratch()...")
        self._create_schema_from_scratch()
        logger.info("[DB_INIT] _create_schema_from_scratch() completado")

    def _verify_and_repair_schema(self) -> None:
        """Verifica que todas las tablas esenciales existen. Lanza excepción si la BD está corrupta."""
        logger.info("[VERIFY] Verificando schema de BD existente...")
        with self.connection() as conn:
            # Primero verificar integridad
            try:
                integrity = conn.execute("PRAGMA integrity_check").fetchone()
                logger.info(
                    f"[VERIFY] Integrity check: {integrity[0] if integrity else 'N/A'}"
                )
            except Exception as e:
                logger.warning(f"[VERIFY] Integrity check failed: {e}")

            existing_tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            existing_names = {t[0] for t in existing_tables}
            logger.info(
                f"[VERIFY] Tablas existentes ({len(existing_names)}): {existing_names}"
            )
            logger.info(f"[VERIFY] Tablas requeridas: {ESSENTIAL_TABLES}")

            missing_tables = ESSENTIAL_TABLES - existing_names

            if missing_tables:
                logger.warning(f"[VERIFY] Faltan tablas esenciales: {missing_tables}")
                # Intentar crear las tablas faltantes ejecutando todo el schema
                logger.info(
                    "[VERIFY] Ejecutando SCHEMA_SQL para crear tablas faltantes..."
                )
                conn.executescript(SCHEMA_SQL)
                conn.commit()
                logger.info("[VERIFY] SCHEMA_SQL ejecutado y commit hecho")

                # Verificar de nuevo
                existing_tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                existing_names = {t[0] for t in existing_tables}
                still_missing = ESSENTIAL_TABLES - existing_names
                logger.info(f"[VERIFY] Tablas tras reparación: {existing_names}")

                if still_missing:
                    logger.error(
                        f"[VERIFY] FALLO: No se pudieron crear tablas: {still_missing}"
                    )
                    raise RuntimeError(f"No se pudieron crear tablas: {still_missing}")

                logger.info("[VERIFY] Tablas faltantes creadas exitosamente")
            else:
                logger.info("[VERIFY] Todas las tablas esenciales existen")

            # Migraciones incrementales para columnas nuevas
            self._apply_column_migrations(conn)

    def _apply_column_migrations(self, conn) -> None:
        """Aplica migraciones de columnas nuevas a tablas existentes."""
        migrations = [
            # (tabla, columna, definición SQL)
            ("entity_mentions", "metadata", "TEXT"),
            ("alerts", "content_hash", "TEXT DEFAULT ''"),
            # S-6: Métricas de enriquecimiento por capítulo
            ("chapters", "dialogue_ratio", "REAL"),
            ("chapters", "avg_sentence_length", "REAL"),
            ("chapters", "scene_count", "INTEGER"),
            ("chapters", "characters_present_count", "INTEGER"),
            ("chapters", "pov_character", "TEXT"),
            ("chapters", "dominant_tone", "TEXT"),
            ("chapters", "tone_intensity", "REAL"),
            ("chapters", "reading_time_minutes", "INTEGER"),
            # Timeline: soporte para day_offset (Día 0, Día +1, etc.)
            ("timeline_events", "day_offset", "INTEGER"),
            ("timeline_events", "weekday", "TEXT"),
            # Timeline: instancia temporal (viajes en el tiempo: A@40 vs A@45)
            ("timeline_events", "temporal_instance_id", "TEXT"),
            # v14: Colecciones / Sagas (BK-07)
            ("projects", "collection_id", "INTEGER"),
            ("projects", "collection_order", "INTEGER DEFAULT 0"),
            # v15: chapter_id en entity_attributes (S8a-06)
            ("entity_attributes", "chapter_id", "INTEGER"),
            # v17: Demo project flag (PP-3c)
            ("projects", "is_demo", "INTEGER DEFAULT 0"),
            # v21: Alert linking para Revision Intelligence (S14, BK-25)
            ("alerts", "previous_snapshot_alert_id", "INTEGER"),
            ("alerts", "match_confidence", "REAL"),
            ("alerts", "resolution_reason", "TEXT"),
        ]
        for table, column, col_def in migrations:
            try:
                cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
                col_names = {c[1] for c in cols}
                if column not in col_names:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
                    logger.info(f"Migración: añadida columna {table}.{column}")
            except Exception as e:
                logger.warning(f"Error en migración {table}.{column}: {e}")

        # Migraciones de tablas nuevas (CREATE TABLE IF NOT EXISTS)
        table_migrations = [
            # v19: Invalidación granular (S8c)
            """CREATE TABLE IF NOT EXISTS invalidation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                entity_ids TEXT NOT NULL DEFAULT '[]',
                detail TEXT,
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_invalidation_project ON invalidation_events(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_invalidation_revision ON invalidation_events(project_id, revision)",
            # v20: Glosario de usuario → NER (BK-17)
            """CREATE TABLE IF NOT EXISTS user_glossary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                term TEXT NOT NULL,
                entity_type TEXT NOT NULL DEFAULT 'PER',
                confidence REAL NOT NULL DEFAULT 1.0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE (project_id, term, entity_type)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_glossary_project ON user_glossary(project_id)",
            # v21: Snapshot chapter texts para content diffing (S14, BK-25)
            """CREATE TABLE IF NOT EXISTS snapshot_chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                chapter_number INTEGER NOT NULL,
                content_hash TEXT DEFAULT '',
                content_text TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (snapshot_id) REFERENCES analysis_snapshots(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_snap_chapters_snapshot ON snapshot_chapters(snapshot_id)",
        ]
        for sql in table_migrations:
            try:
                conn.execute(sql)
            except Exception as e:
                logger.warning(f"Error en migración de tabla: {e}")

    def _create_schema_from_scratch(self) -> None:
        """Crea el schema completo desde cero."""
        try:
            logger.info(f"[SCHEMA] Creando schema desde cero en: {self.db_path}")
            logger.info(f"[SCHEMA] SCHEMA_SQL length: {len(SCHEMA_SQL)} chars")
            logger.info(f"[SCHEMA] ESSENTIAL_TABLES: {ESSENTIAL_TABLES}")

            with self.connection() as conn:
                logger.info("[SCHEMA] Conexión abierta, ejecutando SCHEMA_SQL...")
                conn.executescript(SCHEMA_SQL)
                logger.info("[SCHEMA] executescript completado")
                conn.commit()
                logger.info("[SCHEMA] commit completado")

                # Verificar que las tablas se crearon (misma conexión)
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                table_names = {t[0] for t in tables}
                logger.info(f"[SCHEMA] Tablas en misma conexión: {table_names}")

                missing = ESSENTIAL_TABLES - table_names
                if missing:
                    logger.error(
                        f"[SCHEMA] ALERTA CRÍTICA: Faltan tablas tras executescript: {missing}"
                    )
                    raise RuntimeError(f"Schema incompleto, faltan: {missing}")

            # Verificación INDEPENDIENTE: abrir nueva conexión para confirmar persistencia
            if not self._is_memory:
                logger.info("[SCHEMA] Verificación independiente con nueva conexión...")
                verify_conn = sqlite3.connect(str(self.db_path))
                try:
                    verify_tables = verify_conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                    verify_names = {t[0] for t in verify_tables}
                    logger.info(
                        f"[SCHEMA] Tablas en conexión independiente: {verify_names}"
                    )
                    verify_missing = ESSENTIAL_TABLES - verify_names
                    if verify_missing:
                        logger.error(
                            f"[SCHEMA] FALLO PERSISTENCIA: tablas no persistidas a disco: {verify_missing}"
                        )
                        # Forzar WAL checkpoint
                        logger.info("[SCHEMA] Forzando WAL checkpoint...")
                        verify_conn.execute("PRAGMA wal_checkpoint(FULL)")
                        verify_tables2 = verify_conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        ).fetchall()
                        verify_names2 = {t[0] for t in verify_tables2}
                        logger.info(f"[SCHEMA] Tablas post-checkpoint: {verify_names2}")
                        if ESSENTIAL_TABLES - verify_names2:
                            raise RuntimeError(
                                f"Schema no persistido a disco: {ESSENTIAL_TABLES - verify_names2}"
                            )
                finally:
                    verify_conn.close()

            logger.info(f"[SCHEMA] Schema inicializado y verificado en {self.db_path}")

            # Log file size
            if (
                not self._is_memory
                and isinstance(self.db_path, Path)
                and self.db_path.exists()
            ):
                logger.info(
                    f"[SCHEMA] DB file size: {self.db_path.stat().st_size} bytes"
                )

        except Exception as e:
            logger.error(f"[SCHEMA] Error inicializando schema: {e}", exc_info=True)
            raise

    def _create_connection(self) -> sqlite3.Connection:
        """Crea y configura una nueva conexión."""
        conn = sqlite3.connect(
            str(self.db_path),
            isolation_level="DEFERRED",
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.execute("PRAGMA foreign_keys = ON")
        # WAL no funciona con :memory:
        if not self._is_memory:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """
        Context manager para conexión segura.

        Para bases de datos en memoria, reutiliza la misma conexión.
        Para bases de datos en archivo, crea una nueva conexión por operación.

        Yields:
            Conexión SQLite configurada
        """
        if self._is_memory:
            # Para :memory: usamos conexión compartida
            if self._shared_connection is None:
                self._shared_connection = self._create_connection()
            try:
                yield self._shared_connection
                self._shared_connection.commit()
            except Exception:
                self._shared_connection.rollback()
                raise
        else:
            # Para archivos, nueva conexión por operación
            conn = self._create_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """
        Context manager para transacción explícita.

        Uso:
            with db.transaction() as conn:
                conn.execute("INSERT ...")
                conn.execute("UPDATE ...")
                # Commit automático al salir, rollback si excepción
        """
        if self._is_memory:
            # Para :memory: usamos conexión compartida
            if self._shared_connection is None:
                self._shared_connection = self._create_connection()
            try:
                self._shared_connection.execute("BEGIN IMMEDIATE")
                yield self._shared_connection
                self._shared_connection.commit()
            except Exception:
                self._shared_connection.rollback()
                raise
        else:
            # Para archivos, nueva conexión
            conn = self._create_connection()
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Ejecuta SQL y retorna cursor."""
        with self.connection() as conn:
            return conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list[tuple]) -> sqlite3.Cursor:
        """Ejecuta SQL múltiples veces."""
        with self.connection() as conn:
            return conn.executemany(sql, params_list)

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """Ejecuta y retorna una fila."""
        with self.connection() as conn:
            return conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Ejecuta y retorna todas las filas."""
        with self.connection() as conn:
            return conn.execute(sql, params).fetchall()

    def get_schema_version(self) -> int:
        """Retorna versión actual del schema."""
        row = self.fetchone("SELECT value FROM schema_info WHERE key = 'version'")
        return int(row["value"]) if row else 0


# Singleton
_database: Database | None = None


def get_database(db_path: Path | None = None) -> Database:
    """Obtiene instancia singleton de base de datos (thread-safe)."""
    global _database
    logger.info(f"get_database llamado con db_path={db_path}")
    if _database is None or (db_path and db_path != _database.db_path):
        with _database_lock:
            # Double-checked locking
            if _database is None or (db_path and db_path != _database.db_path):
                logger.info(
                    f"Creando nueva instancia de Database con db_path={db_path}"
                )
                _database = Database(db_path)
                logger.info(f"Database creada, db_path efectivo: {_database.db_path}")
    else:
        logger.info(f"Reutilizando instancia existente, db_path: {_database.db_path}")
    return _database


def reset_database() -> None:
    """Resetea el singleton de base de datos (thread-safe, para testing)."""
    global _database
    with _database_lock:
        _database = None


def repair_database() -> tuple[bool, str]:
    """
    Intenta reparar una base de datos corrupta SIN perder datos.

    Pasos de reparación:
    1. Verifica integridad con PRAGMA integrity_check
    2. Intenta crear tablas faltantes
    3. Intenta recuperar con backup y restore

    Returns:
        Tupla (éxito: bool, mensaje: str)
    """
    global _database
    from ..core.config import get_config

    config = get_config()
    db_path = config.db_path

    if not isinstance(db_path, Path) or not db_path.exists():
        return False, "No existe archivo de base de datos para reparar"

    logger.info(f"Iniciando reparación de BD: {db_path}")

    with _database_lock:
        # Cerrar conexión existente
        _database = None

        try:
            # Paso 1: Verificar integridad
            conn = sqlite3.connect(str(db_path), timeout=30)
            conn.row_factory = sqlite3.Row

            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            logger.info(f"Integrity check: {integrity}")

            if integrity != "ok":
                logger.warning(f"BD con problemas de integridad: {integrity}")
                # Intentar VACUUM para reparar
                try:
                    conn.execute("VACUUM")
                    conn.commit()
                    logger.info("VACUUM ejecutado")
                except Exception as vacuum_err:
                    logger.warning(f"VACUUM falló: {vacuum_err}")

            # Paso 2: Verificar y crear tablas faltantes
            existing = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            logger.info(f"Tablas existentes: {existing}")

            missing = ESSENTIAL_TABLES - existing
            if missing:
                logger.info(f"Creando tablas faltantes: {missing}")
                conn.executescript(SCHEMA_SQL)
                conn.commit()

                # Verificar de nuevo
                existing = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                still_missing = ESSENTIAL_TABLES - existing

                if still_missing:
                    conn.close()
                    return False, f"No se pudieron crear tablas: {still_missing}"

            conn.close()

            # Recrear singleton con BD reparada
            _database = Database(db_path)
            return True, "Base de datos reparada exitosamente"

        except Exception as e:
            logger.error(f"Error en reparación: {e}", exc_info=True)
            return False, f"Error durante reparación: {e}"


def delete_and_recreate_database() -> Database:
    """
    Elimina la base de datos existente y crea una nueva desde cero.

    ¡CUIDADO! Esta operación elimina TODOS los datos.
    Usar solo si repair_database() falla.

    Returns:
        Nueva instancia de Database con schema limpio.
    """
    global _database
    from ..core.config import get_config

    config = get_config()
    db_path = config.db_path

    with _database_lock:
        # Cerrar conexiones existentes
        if _database is not None:
            _database = None

        # Eliminar archivos de la BD
        if isinstance(db_path, Path) and db_path.exists():
            logger.warning(f"Eliminando base de datos: {db_path}")
            db_path.unlink()
            # También eliminar archivos WAL y SHM
            for suffix in ["-wal", "-shm"]:
                aux_path = Path(str(db_path) + suffix)
                if aux_path.exists():
                    aux_path.unlink()
                    logger.info(f"Eliminado archivo auxiliar: {aux_path}")

        # Crear nueva BD
        logger.info("Creando nueva base de datos desde cero...")
        _database = Database(db_path)
        logger.info("Base de datos recreada exitosamente")

        return _database
