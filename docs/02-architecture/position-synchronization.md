# Sincronización de Posiciones ante Cambios

[← Volver a Arquitectura](./README.md) | [← Índice principal](../../README.md)

---

## El Problema

Cuando el usuario modifica el manuscrito en Word y vuelve a importar:
- Lo que estaba en la página 10 ahora puede estar en la página 11
- Las posiciones de carácter cambian
- Las referencias de alertas existentes apuntan a posiciones incorrectas
- Los análisis en curso podrían invalidarse

**Principio fundamental:** El sistema debe mantener la **integridad referencial** entre alertas/hallazgos y el texto, incluso cuando el documento cambia.

---

## Estrategia: Análisis sobre Snapshot Inmutable

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     GESTIÓN DE VERSIONES Y ANÁLISIS                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  IMPORT v1                    IMPORT v2                    IMPORT v3        │
│     │                            │                            │             │
│     ▼                            ▼                            ▼             │
│  ┌──────────┐               ┌──────────┐               ┌──────────┐        │
│  │ Snapshot │               │ Snapshot │               │ Snapshot │        │
│  │   v1     │               │   v2     │               │   v3     │        │
│  │ (inmut.) │               │ (inmut.) │               │ (inmut.) │        │
│  └────┬─────┘               └────┬─────┘               └────┬─────┘        │
│       │                          │                          │              │
│       ▼                          ▼                          ▼              │
│  ┌──────────┐               ┌──────────┐               ┌──────────┐        │
│  │ Análisis │──migration───▶│ Análisis │──migration───▶│ Análisis │        │
│  │   v1     │               │   v2     │               │   v3     │        │
│  └──────────┘               └──────────┘               └──────────┘        │
│       │                          │                          │              │
│       └──────────────────────────┼──────────────────────────┘              │
│                                  ▼                                          │
│                          ┌──────────────┐                                   │
│                          │   UI muestra │                                   │
│                          │  versión más │                                   │
│                          │   reciente   │                                   │
│                          └──────────────┘                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Modelo de Referencia Resiliente

### Referencias basadas en Anclas, no en Posiciones Absolutas

```python
from dataclasses import dataclass
from typing import Optional, List, Tuple
import hashlib

@dataclass
class TextAnchor:
    """
    Ancla resiliente a cambios de posición.
    Usa múltiples estrategias para relocalizarse.
    """
    # Identificación primaria
    anchor_id: str

    # Contexto estructural (más estable)
    chapter_number: int
    paragraph_index: int  # Índice dentro del capítulo
    sentence_index: int   # Índice dentro del párrafo

    # Posición absoluta (referencia rápida, puede invalidarse)
    char_start: int
    char_end: int
    page_number: Optional[int] = None

    # Contenido para relocalización
    text_content: str          # El texto exacto referenciado
    text_hash: str = ""        # Hash del contenido
    context_before: str = ""   # ~50 chars antes
    context_after: str = ""    # ~50 chars después
    context_hash: str = ""     # Hash del contexto completo

    # Metadatos de la versión donde se creó
    source_version: int = 1

    def __post_init__(self):
        if not self.text_hash:
            self.text_hash = self._hash(self.text_content)
        if not self.context_hash:
            full_context = f"{self.context_before}{self.text_content}{self.context_after}"
            self.context_hash = self._hash(full_context)

    @staticmethod
    def _hash(text: str) -> str:
        normalized = ' '.join(text.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

@dataclass
class RelocatedAnchor:
    """Resultado de intentar relocalizar un ancla."""
    original: TextAnchor
    found: bool
    new_char_start: Optional[int] = None
    new_char_end: Optional[int] = None
    new_chapter: Optional[int] = None
    new_paragraph: Optional[int] = None
    relocation_method: str = ""  # Cómo se encontró
    confidence: float = 0.0
    text_changed: bool = False   # El contenido cambió (no solo posición)
```

---

## Servicio de Relocalización

```python
from enum import Enum
from typing import List, Dict, Optional
import re
from difflib import SequenceMatcher

class RelocationMethod(Enum):
    EXACT_MATCH = "exact_match"              # Texto idéntico encontrado
    STRUCTURAL = "structural"                 # Mismo cap/párrafo/oración
    CONTEXT_MATCH = "context_match"          # Contexto circundante coincide
    FUZZY_MATCH = "fuzzy_match"              # Coincidencia aproximada
    NOT_FOUND = "not_found"                  # No se pudo relocalizar

class AnchorRelocationService:
    """Servicio para relocalizar anclas cuando el documento cambia."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def relocate_anchor(
        self,
        anchor: TextAnchor,
        new_document: 'ParsedDocument'
    ) -> RelocatedAnchor:
        """
        Intenta relocalizar un ancla en una nueva versión del documento.
        Usa estrategias en cascada, de más precisa a más aproximada.
        """
        # Estrategia 1: Búsqueda exacta del texto
        result = self._try_exact_match(anchor, new_document)
        if result.found:
            return result

        # Estrategia 2: Búsqueda estructural (mismo cap/párrafo)
        result = self._try_structural_match(anchor, new_document)
        if result.found:
            return result

        # Estrategia 3: Búsqueda por contexto
        result = self._try_context_match(anchor, new_document)
        if result.found:
            return result

        # Estrategia 4: Búsqueda fuzzy
        result = self._try_fuzzy_match(anchor, new_document)
        if result.found:
            return result

        # No encontrado
        return RelocatedAnchor(
            original=anchor,
            found=False,
            relocation_method=RelocationMethod.NOT_FOUND.value,
            confidence=0.0
        )

    def _try_exact_match(
        self,
        anchor: TextAnchor,
        doc: 'ParsedDocument'
    ) -> RelocatedAnchor:
        """Busca el texto exacto en el nuevo documento."""
        full_text = doc.get_full_text()
        pos = full_text.find(anchor.text_content)

        if pos != -1:
            # Encontrado exactamente
            chapter, paragraph = doc.get_location_at(pos)
            return RelocatedAnchor(
                original=anchor,
                found=True,
                new_char_start=pos,
                new_char_end=pos + len(anchor.text_content),
                new_chapter=chapter,
                new_paragraph=paragraph,
                relocation_method=RelocationMethod.EXACT_MATCH.value,
                confidence=1.0,
                text_changed=False
            )

        return RelocatedAnchor(original=anchor, found=False)

    def _try_structural_match(
        self,
        anchor: TextAnchor,
        doc: 'ParsedDocument'
    ) -> RelocatedAnchor:
        """Busca en la misma posición estructural."""
        try:
            chapter = doc.get_chapter(anchor.chapter_number)
            if not chapter:
                return RelocatedAnchor(original=anchor, found=False)

            # Verificar si el párrafo existe
            if anchor.paragraph_index >= len(chapter.paragraphs):
                return RelocatedAnchor(original=anchor, found=False)

            paragraph = chapter.paragraphs[anchor.paragraph_index]

            # Comparar contenido
            similarity = SequenceMatcher(
                None,
                anchor.text_content.lower(),
                paragraph.text.lower()
            ).ratio()

            if similarity >= self.similarity_threshold:
                return RelocatedAnchor(
                    original=anchor,
                    found=True,
                    new_char_start=paragraph.start_char,
                    new_char_end=paragraph.end_char,
                    new_chapter=anchor.chapter_number,
                    new_paragraph=anchor.paragraph_index,
                    relocation_method=RelocationMethod.STRUCTURAL.value,
                    confidence=similarity,
                    text_changed=similarity < 1.0
                )

        except (IndexError, AttributeError):
            pass

        return RelocatedAnchor(original=anchor, found=False)

    def _try_context_match(
        self,
        anchor: TextAnchor,
        doc: 'ParsedDocument'
    ) -> RelocatedAnchor:
        """Busca usando el contexto circundante."""
        full_text = doc.get_full_text()

        # Buscar el contexto antes + después
        context_pattern = re.escape(anchor.context_before[-30:]) + \
                         r'(.{1,500})' + \
                         re.escape(anchor.context_after[:30])

        match = re.search(context_pattern, full_text, re.DOTALL)
        if match:
            found_text = match.group(1)
            similarity = SequenceMatcher(
                None,
                anchor.text_content.lower(),
                found_text.lower()
            ).ratio()

            if similarity >= 0.7:  # Umbral más bajo porque el contexto ya coincide
                pos = match.start(1)
                chapter, paragraph = doc.get_location_at(pos)

                return RelocatedAnchor(
                    original=anchor,
                    found=True,
                    new_char_start=pos,
                    new_char_end=pos + len(found_text),
                    new_chapter=chapter,
                    new_paragraph=paragraph,
                    relocation_method=RelocationMethod.CONTEXT_MATCH.value,
                    confidence=similarity * 0.9,  # Penalizar ligeramente
                    text_changed=similarity < 1.0
                )

        return RelocatedAnchor(original=anchor, found=False)

    def _try_fuzzy_match(
        self,
        anchor: TextAnchor,
        doc: 'ParsedDocument'
    ) -> RelocatedAnchor:
        """Búsqueda fuzzy en todo el documento."""
        full_text = doc.get_full_text()

        # Dividir en ventanas y buscar la más similar
        window_size = len(anchor.text_content) * 2
        best_match = None
        best_similarity = 0.0
        best_pos = 0

        for i in range(0, len(full_text) - window_size, window_size // 4):
            window = full_text[i:i + window_size]
            similarity = SequenceMatcher(
                None,
                anchor.text_content.lower(),
                window.lower()
            ).ratio()

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = window
                best_pos = i

        if best_similarity >= self.similarity_threshold:
            chapter, paragraph = doc.get_location_at(best_pos)

            return RelocatedAnchor(
                original=anchor,
                found=True,
                new_char_start=best_pos,
                new_char_end=best_pos + len(best_match),
                new_chapter=chapter,
                new_paragraph=paragraph,
                relocation_method=RelocationMethod.FUZZY_MATCH.value,
                confidence=best_similarity * 0.8,  # Penalizar más
                text_changed=True
            )

        return RelocatedAnchor(original=anchor, found=False)

    def relocate_all_alerts(
        self,
        alerts: List['Alert'],
        new_document: 'ParsedDocument'
    ) -> Dict[int, RelocatedAnchor]:
        """Relocaliza todas las alertas de un proyecto."""
        results = {}

        for alert in alerts:
            if alert.anchor:
                results[alert.id] = self.relocate_anchor(alert.anchor, new_document)

        return results
```

---

## Gestión de Análisis en Curso

```python
from enum import Enum
from datetime import datetime
from typing import Optional
import threading

class AnalysisState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    INVALIDATED = "invalidated"
    MIGRATING = "migrating"

@dataclass
class AnalysisSession:
    """Sesión de análisis vinculada a una versión específica."""
    session_id: str
    project_id: int
    document_version: int
    state: AnalysisState
    started_at: datetime
    current_phase: str
    progress: float

    # El snapshot sobre el que se analiza
    snapshot_id: int

class AnalysisCoordinator:
    """
    Coordina análisis y gestiona cambios de documento.
    Garantiza que un análisis siempre trabaja sobre un snapshot inmutable.
    """

    def __init__(
        self,
        repository: 'Repository',
        relocation_service: AnchorRelocationService
    ):
        self.repo = repository
        self.relocation = relocation_service
        self._lock = threading.Lock()
        self._active_sessions: Dict[int, AnalysisSession] = {}

    def start_analysis(
        self,
        project_id: int,
        document: 'ParsedDocument'
    ) -> AnalysisSession:
        """
        Inicia un nuevo análisis.
        Crea un snapshot inmutable del documento.
        """
        with self._lock:
            # 1. Crear snapshot inmutable
            snapshot = self.repo.create_document_snapshot(project_id, document)

            # 2. Crear sesión de análisis
            session = AnalysisSession(
                session_id=f"{project_id}_{snapshot.version}_{datetime.now().timestamp()}",
                project_id=project_id,
                document_version=snapshot.version,
                state=AnalysisState.RUNNING,
                started_at=datetime.now(),
                current_phase="init",
                progress=0.0,
                snapshot_id=snapshot.id
            )

            self._active_sessions[project_id] = session
            return session

    def handle_document_change(
        self,
        project_id: int,
        new_document: 'ParsedDocument'
    ) -> Dict[str, any]:
        """
        Maneja un cambio en el documento mientras hay análisis activo.

        Estrategia:
        1. Si hay análisis en curso: continúa sobre su snapshot
        2. Crea nuevo snapshot para el documento actualizado
        3. Planifica migración de resultados cuando el análisis termine
        """
        with self._lock:
            result = {
                'action': None,
                'message': '',
                'migration_needed': False
            }

            active_session = self._active_sessions.get(project_id)

            # 1. Crear nuevo snapshot siempre
            new_snapshot = self.repo.create_document_snapshot(project_id, new_document)

            if active_session and active_session.state == AnalysisState.RUNNING:
                # Análisis en curso: no interrumpir
                result['action'] = 'continue_existing'
                result['message'] = (
                    f"Análisis en curso sobre versión {active_session.document_version}. "
                    f"Los resultados se migrarán a v{new_snapshot.version} al completar."
                )
                result['migration_needed'] = True

                # Marcar que necesita migración
                self.repo.schedule_migration(
                    from_version=active_session.document_version,
                    to_version=new_snapshot.version
                )

            else:
                # No hay análisis activo: usar nuevo documento
                result['action'] = 'use_new'
                result['message'] = f"Nueva versión {new_snapshot.version} lista para análisis."

                # Migrar alertas existentes al nuevo documento
                existing_alerts = self.repo.get_alerts(project_id)
                if existing_alerts:
                    self._migrate_alerts(existing_alerts, new_document, new_snapshot.version)
                    result['migration_needed'] = True

            return result

    def _migrate_alerts(
        self,
        alerts: List['Alert'],
        new_document: 'ParsedDocument',
        new_version: int
    ) -> None:
        """Migra alertas existentes al nuevo documento."""
        relocations = self.relocation.relocate_all_alerts(alerts, new_document)

        for alert_id, relocation in relocations.items():
            alert = self.repo.get_alert(alert_id)

            if relocation.found:
                # Actualizar posiciones
                alert.anchor.char_start = relocation.new_char_start
                alert.anchor.char_end = relocation.new_char_end
                alert.anchor.chapter_number = relocation.new_chapter
                alert.anchor.paragraph_index = relocation.new_paragraph
                alert.anchor.source_version = new_version

                if relocation.text_changed:
                    # El texto cambió: podría necesitar re-verificación
                    alert.needs_reverification = True
                    alert.add_note(
                        f"Texto modificado en v{new_version}. "
                        f"Confianza de relocalización: {relocation.confidence:.0%}"
                    )

                self.repo.save_alert(alert)

            else:
                # No se pudo relocalizar: marcar como obsoleta o pendiente
                if alert.status in ['resolved', 'dismissed']:
                    # Ya estaba resuelta/ignorada: marcar obsoleta
                    alert.status = 'obsolete'
                    alert.add_note(f"No se encontró en v{new_version}")
                else:
                    # Estaba pendiente: marcar para revisión manual
                    alert.status = 'relocation_failed'
                    alert.add_note(
                        f"No se pudo relocalizar en v{new_version}. "
                        "Requiere revisión manual."
                    )

                self.repo.save_alert(alert)

    def complete_analysis(self, project_id: int) -> None:
        """
        Marca un análisis como completado.
        Si hay migración pendiente, la ejecuta.
        """
        with self._lock:
            session = self._active_sessions.get(project_id)
            if not session:
                return

            session.state = AnalysisState.COMPLETED

            # Verificar si hay migración pendiente
            pending_migration = self.repo.get_pending_migration(project_id)
            if pending_migration:
                session.state = AnalysisState.MIGRATING

                # Obtener documento de la versión destino
                target_doc = self.repo.get_document_snapshot(pending_migration.to_version)
                alerts = self.repo.get_alerts(project_id)

                self._migrate_alerts(alerts, target_doc, pending_migration.to_version)

                self.repo.complete_migration(pending_migration.id)
                session.state = AnalysisState.COMPLETED

            del self._active_sessions[project_id]
```

---

## Flujo de Usuario

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLUJO: DOCUMENTO CAMBIA                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Usuario abre "novela.docx" v1                                              │
│       │                                                                      │
│       ▼                                                                      │
│  Sistema crea Snapshot v1 (inmutable)                                       │
│       │                                                                      │
│       ▼                                                                      │
│  Análisis comienza sobre Snapshot v1                                        │
│       │                                                                      │
│       │ ─────────────────────────────────────────────────────────           │
│       │    (mientras tanto, usuario edita en Word y guarda)                 │
│       │ ─────────────────────────────────────────────────────────           │
│       │                                                                      │
│       ▼                                                                      │
│  Usuario reimporta "novela.docx" v2                                         │
│       │                                                                      │
│       ▼                                                                      │
│  Sistema detecta análisis en curso                                          │
│       │                                                                      │
│       ├──▶ Crea Snapshot v2 (inmutable)                                     │
│       │                                                                      │
│       ├──▶ Muestra mensaje: "Análisis continúa sobre v1.                    │
│       │    Los resultados se migrarán a v2 al completar."                   │
│       │                                                                      │
│       ├──▶ Usuario puede ver alertas de v1 mientras tanto                   │
│       │    (con indicador de que son de versión anterior)                   │
│       │                                                                      │
│       ▼                                                                      │
│  Análisis v1 completa                                                       │
│       │                                                                      │
│       ▼                                                                      │
│  Sistema migra alertas v1 → v2 automáticamente                              │
│       │                                                                      │
│       ├──▶ Alertas relocalizadas: actualizan posición                       │
│       ├──▶ Texto cambió: marcadas para re-verificación                      │
│       └──▶ No encontradas: marcadas obsoletas o revisión manual             │
│                                                                              │
│       ▼                                                                      │
│  Usuario ve alertas con posiciones correctas en v2                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Consideraciones de UI

```python
class VersionIndicator:
    """Componente de UI para mostrar estado de versión."""

    @staticmethod
    def get_status_message(
        current_version: int,
        analysis_version: Optional[int],
        pending_migration: bool
    ) -> dict:
        """Genera mensaje de estado para la UI."""

        if analysis_version and analysis_version < current_version:
            return {
                'type': 'warning',
                'icon': '🔄',
                'message': f'Analizando v{analysis_version}. Documento actual: v{current_version}.',
                'detail': 'Los resultados se actualizarán automáticamente.',
                'show_progress': True
            }

        if pending_migration:
            return {
                'type': 'info',
                'icon': '⏳',
                'message': 'Actualizando posiciones de alertas...',
                'detail': 'Las referencias se están relocalizando.',
                'show_progress': True
            }

        return {
            'type': 'success',
            'icon': '✓',
            'message': f'Documento v{current_version} sincronizado',
            'detail': None,
            'show_progress': False
        }
```

---

## Siguiente

Ver [Sistema de Historial](./history-system.md) para entender cómo se gestionan los estados de las alertas.
