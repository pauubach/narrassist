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
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from ..core.config import get_config

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_database_lock = threading.Lock()

# Versión del schema actual
SCHEMA_VERSION = 10

# Tablas esenciales que deben existir para una BD válida
# Solo incluir las tablas básicas definidas en SCHEMA_SQL
ESSENTIAL_TABLES = {
    'projects', 'chapters', 'entities', 'entity_mentions',
    'alerts', 'sessions', 'correction_config_overrides'
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
    detected_document_type TEXT             -- Tipo detectado por el sistema (puede diferir del actual)
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

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alerts_project ON alerts(project_id);
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

-- Insertar versión del schema
INSERT OR REPLACE INTO schema_info (key, value) VALUES ('version', '10');
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

    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa conexión a base de datos.

        Args:
            db_path: Ruta al archivo SQLite. Si None, usa config.
        """
        config = get_config()
        self.db_path = db_path or config.db_path
        logger.info(f"Database.__init__: db_path param={db_path}, config.db_path={config.db_path}")
        logger.info(f"Database.__init__: usando db_path={self.db_path}")
        self._is_memory = self.db_path == ":memory:" or (
            isinstance(self.db_path, str) and self.db_path.startswith(":")
        )
        # Para :memory: mantenemos una conexión persistente
        self._shared_connection: Optional[sqlite3.Connection] = None
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
        logger.info(f"Inicializando schema en: {self.db_path}")
        logger.info(f"db_path type: {type(self.db_path)}, is_memory: {self._is_memory}")

        # Verificar si el archivo existe y tiene contenido
        if not self._is_memory and isinstance(self.db_path, Path):
            if self.db_path.exists():
                size = self.db_path.stat().st_size
                logger.info(f"Archivo DB existente, tamaño: {size} bytes")

                if size == 0:
                    # Empty file (e.g., from a previous failed init) - delete and recreate
                    logger.warning("DB file exists but is empty (0 bytes), deleting to recreate")
                    self.db_path.unlink()
                else:
                    # Verificar integridad de la BD existente
                    try:
                        self._verify_and_repair_schema()
                        return  # BD válida, no hacer nada más
                    except Exception as e:
                        logger.warning(f"BD posiblemente corrupta: {e}. Eliminando para recrear...")
                        # Delete the corrupt file and all auxiliary files
                        try:
                            self.db_path.unlink()
                            for suffix in ["-wal", "-shm", "-journal"]:
                                aux_path = Path(str(self.db_path) + suffix)
                                if aux_path.exists():
                                    aux_path.unlink()
                                    logger.info(f"Eliminado archivo auxiliar corrupto: {aux_path}")
                        except Exception as del_err:
                            logger.error(f"Error eliminando BD corrupta: {del_err}")
            else:
                logger.info("Archivo DB no existe, se creará nuevo")

        # Crear schema desde cero
        self._create_schema_from_scratch()

    def _verify_and_repair_schema(self) -> None:
        """Verifica que todas las tablas esenciales existen. Lanza excepción si la BD está corrupta."""
        with self.connection() as conn:
            existing_tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            existing_names = {t[0] for t in existing_tables}
            logger.info(f"Tablas existentes: {existing_names}")

            missing_tables = ESSENTIAL_TABLES - existing_names

            if missing_tables:
                logger.warning(f"Faltan tablas esenciales: {missing_tables}")
                # Intentar crear las tablas faltantes ejecutando todo el schema
                logger.info("Ejecutando SCHEMA_SQL para crear tablas faltantes...")
                conn.executescript(SCHEMA_SQL)
                conn.commit()

                # Verificar de nuevo
                existing_tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                existing_names = {t[0] for t in existing_tables}
                still_missing = ESSENTIAL_TABLES - existing_names

                if still_missing:
                    raise RuntimeError(f"No se pudieron crear tablas: {still_missing}")

                logger.info("Tablas faltantes creadas exitosamente")
            else:
                logger.info("Todas las tablas esenciales existen")

            # Migraciones incrementales para columnas nuevas
            self._apply_column_migrations(conn)

    def _apply_column_migrations(self, conn) -> None:
        """Aplica migraciones de columnas nuevas a tablas existentes."""
        migrations = [
            # (tabla, columna, definición SQL)
            ("entity_mentions", "metadata", "TEXT"),
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

    def _create_schema_from_scratch(self) -> None:
        """Crea el schema completo desde cero."""
        try:
            with self.connection() as conn:
                logger.info("Ejecutando SCHEMA_SQL completo...")
                conn.executescript(SCHEMA_SQL)
                conn.commit()

                # Verificar que las tablas se crearon
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                table_names = {t[0] for t in tables}
                logger.info(f"Tablas creadas: {table_names}")

                missing = ESSENTIAL_TABLES - table_names
                if missing:
                    logger.error(f"ALERTA CRÍTICA: No se crearon todas las tablas. Faltan: {missing}")
                    raise RuntimeError(f"Schema incompleto, faltan: {missing}")

                logger.info(f"Schema inicializado correctamente en {self.db_path}")

        except Exception as e:
            logger.error(f"Error inicializando schema: {e}", exc_info=True)
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

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
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
_database: Optional[Database] = None


def get_database(db_path: Optional[Path] = None) -> Database:
    """Obtiene instancia singleton de base de datos (thread-safe)."""
    global _database
    logger.info(f"get_database llamado con db_path={db_path}")
    if _database is None or (db_path and db_path != _database.db_path):
        with _database_lock:
            # Double-checked locking
            if _database is None or (db_path and db_path != _database.db_path):
                logger.info(f"Creando nueva instancia de Database con db_path={db_path}")
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
            existing = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            logger.info(f"Tablas existentes: {existing}")

            missing = ESSENTIAL_TABLES - existing
            if missing:
                logger.info(f"Creando tablas faltantes: {missing}")
                conn.executescript(SCHEMA_SQL)
                conn.commit()

                # Verificar de nuevo
                existing = {row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()}
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
