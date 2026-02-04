# Sistema de Historial y Estados

[← Volver a Arquitectura](./README.md) | [← Índice principal](../../README.md)

---

## Visión General

El sistema mantiene un historial completo de:
1. **Hallazgos** (alertas) y sus estados
2. **Cambios en el documento** (versiones del manuscrito)
3. **Acciones del usuario** sobre los hallazgos

Esto permite:
- No volver a mostrar alertas ya ignoradas
- Analizar solo los cambios (análisis incremental)
- Tener trazabilidad completa del proceso de revisión

---

## Estados de Hallazgos (Alertas)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CICLO DE VIDA DE UNA ALERTA                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                              ┌──────────────┐                               │
│                              │    NUEVA     │                               │
│                              │   (new)      │                               │
│                              └──────┬───────┘                               │
│                                     │                                        │
│                      ┌──────────────┼──────────────┐                        │
│                      │              │              │                        │
│                      ▼              ▼              ▼                        │
│              ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│              │   REVISADA   │ │   IGNORADA   │ │   RESUELTA   │             │
│              │  (reviewed)  │ │  (dismissed) │ │  (resolved)  │             │
│              └──────┬───────┘ └──────────────┘ └──────┬───────┘             │
│                     │                                  │                     │
│                     │         (si cambia el texto      │                     │
│                     │          relacionado)            │                     │
│                     ▼                                  ▼                     │
│              ┌──────────────┐                  ┌──────────────┐             │
│              │  PENDIENTE   │                  │  VERIFICADA  │             │
│              │  (pending)   │                  │  (verified)  │             │
│              └──────────────┘                  └──────────────┘             │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Estados especiales:                                                         │
│  • AUTO_RESOLVED: Se resolvió automáticamente (ej: entidad fusionada)       │
│  • REOPENED: Se reabrió porque el texto cambió de nuevo                     │
│  • OBSOLETE: Ya no aplica (sección eliminada)                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Modelo de Datos: Historial de Alertas

```python
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class AlertState(Enum):
    NEW = "new"                  # Recién detectada
    REVIEWED = "reviewed"        # Usuario la vio pero no actuó
    PENDING = "pending"          # Marcada para revisar después
    DISMISSED = "dismissed"      # Ignorada (falso positivo o decisión)
    RESOLVED = "resolved"        # Corregida manualmente
    VERIFIED = "verified"        # Verificado que se corrigió
    AUTO_RESOLVED = "auto_resolved"  # Resuelta automáticamente
    REOPENED = "reopened"        # Reabierta por cambio en texto
    OBSOLETE = "obsolete"        # Ya no aplica

@dataclass
class AlertStateChange:
    """Registro de cambio de estado de una alerta."""
    id: int
    alert_id: int
    from_state: AlertState
    to_state: AlertState
    changed_at: datetime
    changed_by: str  # 'user' o 'system'
    reason: str = ""
    note: str = ""

@dataclass
class AlertHistory:
    """Historial completo de una alerta."""
    alert_id: int
    current_state: AlertState
    state_changes: List[AlertStateChange] = field(default_factory=list)

    # Timestamps clave
    first_detected: datetime = field(default_factory=datetime.now)
    last_state_change: Optional[datetime] = None

    # Contexto original (para comparar con cambios)
    original_text_hash: str = ""
    original_position: int = 0
    original_chapter: int = 0

    def add_state_change(
        self,
        to_state: AlertState,
        changed_by: str = "user",
        reason: str = "",
        note: str = ""
    ) -> None:
        """Registra un cambio de estado."""
        change = AlertStateChange(
            id=len(self.state_changes) + 1,
            alert_id=self.alert_id,
            from_state=self.current_state,
            to_state=to_state,
            changed_at=datetime.now(),
            changed_by=changed_by,
            reason=reason,
            note=note
        )
        self.state_changes.append(change)
        self.current_state = to_state
        self.last_state_change = datetime.now()

class AlertHistoryService:
    """Servicio para gestionar el historial de alertas."""

    def __init__(self, repository: 'Repository'):
        self.repo = repository

    def dismiss_alert(
        self,
        alert_id: int,
        reason: str = "",
        note: str = "",
        permanent: bool = True
    ) -> AlertHistory:
        """
        Ignora una alerta.

        Args:
            alert_id: ID de la alerta
            reason: Razón para ignorar (ej: 'false_positive', 'intentional')
            note: Nota adicional del usuario
            permanent: Si True, no se mostrará en reanálisis
        """
        history = self.repo.get_alert_history(alert_id)
        history.add_state_change(
            to_state=AlertState.DISMISSED,
            changed_by="user",
            reason=reason,
            note=note
        )

        # Guardar flag de permanencia
        if permanent:
            self.repo.mark_alert_permanent_dismiss(alert_id)

        return self.repo.save_alert_history(history)

    def resolve_alert(
        self,
        alert_id: int,
        note: str = ""
    ) -> AlertHistory:
        """Marca una alerta como resuelta."""
        history = self.repo.get_alert_history(alert_id)
        history.add_state_change(
            to_state=AlertState.RESOLVED,
            changed_by="user",
            note=note
        )
        return self.repo.save_alert_history(history)

    def check_for_reopen(
        self,
        alert_id: int,
        current_text_hash: str
    ) -> bool:
        """
        Verifica si una alerta resuelta debe reabrirse.
        Retorna True si el texto relacionado cambió.
        """
        history = self.repo.get_alert_history(alert_id)

        if history.current_state not in [AlertState.RESOLVED, AlertState.VERIFIED]:
            return False

        if current_text_hash != history.original_text_hash:
            history.add_state_change(
                to_state=AlertState.REOPENED,
                changed_by="system",
                reason="text_changed",
                note="El texto relacionado ha cambiado desde la resolución"
            )
            self.repo.save_alert_history(history)
            return True

        return False

    def get_dismissed_patterns(
        self,
        project_id: int
    ) -> List[dict]:
        """
        Obtiene patrones de alertas ignoradas permanentemente.
        Se usa para no regenerar estas alertas en reanálisis.
        """
        return self.repo.get_permanent_dismissals(project_id)
```

---

## Modelo de Datos: Versiones del Documento

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set
from datetime import datetime
import hashlib

@dataclass
class DocumentVersion:
    """Representa una versión del documento."""
    id: int
    project_id: int
    version_number: int

    # Hashes para detectar cambios
    full_hash: str  # Hash del documento completo
    chapter_hashes: Dict[int, str] = field(default_factory=dict)  # chapter_num -> hash
    paragraph_hashes: Dict[str, str] = field(default_factory=dict)  # para_id -> hash

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    source_file: str = ""
    word_count: int = 0
    character_count: int = 0

    # Cambios respecto a versión anterior
    chapters_modified: Set[int] = field(default_factory=set)
    chapters_added: Set[int] = field(default_factory=set)
    chapters_deleted: Set[int] = field(default_factory=set)

@dataclass
class DocumentChange:
    """Representa un cambio entre dos versiones."""
    version_from: int
    version_to: int
    change_type: str  # 'modified', 'added', 'deleted'
    chapter: int
    paragraph_id: Optional[str] = None

    # Contenido (para comparación)
    old_text: str = ""
    new_text: str = ""

    # Posición
    start_char: int = 0
    end_char: int = 0

class DocumentVersionService:
    """Servicio para gestionar versiones del documento."""

    def __init__(self, repository: 'Repository'):
        self.repo = repository

    def create_version(
        self,
        project_id: int,
        document: 'ParsedDocument'
    ) -> DocumentVersion:
        """Crea una nueva versión del documento."""
        # Obtener versión anterior
        prev_version = self.repo.get_latest_version(project_id)
        version_number = (prev_version.version_number + 1) if prev_version else 1

        # Calcular hashes
        chapter_hashes = {}
        paragraph_hashes = {}

        for chapter in document.chapters:
            chapter_text = chapter.get_text()
            chapter_hashes[chapter.number] = self._hash_text(chapter_text)

            for para in chapter.paragraphs:
                para_id = f"{chapter.number}_{para.index}"
                paragraph_hashes[para_id] = self._hash_text(para.text)

        full_hash = self._hash_text(document.get_full_text())

        version = DocumentVersion(
            id=0,
            project_id=project_id,
            version_number=version_number,
            full_hash=full_hash,
            chapter_hashes=chapter_hashes,
            paragraph_hashes=paragraph_hashes,
            source_file=document.source_path,
            word_count=document.word_count,
            character_count=document.character_count
        )

        # Detectar cambios respecto a versión anterior
        if prev_version:
            version = self._detect_changes(version, prev_version)

        return self.repo.save_document_version(version)

    def _hash_text(self, text: str) -> str:
        """Calcula hash de un texto."""
        normalized = ' '.join(text.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _detect_changes(
        self,
        current: DocumentVersion,
        previous: DocumentVersion
    ) -> DocumentVersion:
        """Detecta qué capítulos cambiaron entre versiones."""
        current_chapters = set(current.chapter_hashes.keys())
        previous_chapters = set(previous.chapter_hashes.keys())

        # Capítulos nuevos
        current.chapters_added = current_chapters - previous_chapters

        # Capítulos eliminados
        current.chapters_deleted = previous_chapters - current_chapters

        # Capítulos modificados
        common_chapters = current_chapters & previous_chapters
        current.chapters_modified = {
            ch for ch in common_chapters
            if current.chapter_hashes[ch] != previous.chapter_hashes[ch]
        }

        return current

    def get_changes(
        self,
        project_id: int,
        from_version: int,
        to_version: int
    ) -> List[DocumentChange]:
        """Obtiene lista detallada de cambios entre versiones."""
        # Implementación simplificada
        return self.repo.get_document_changes(project_id, from_version, to_version)

    def get_modified_chapters(
        self,
        project_id: int
    ) -> Set[int]:
        """Obtiene capítulos modificados desde el último análisis."""
        latest = self.repo.get_latest_version(project_id)
        if not latest:
            return set()

        return latest.chapters_modified | latest.chapters_added
```

---

## Análisis Incremental

```python
class IncrementalAnalyzer:
    """Analiza solo los cambios desde el último análisis."""

    def __init__(
        self,
        full_analyzer: 'AnalysisPipeline',
        version_service: DocumentVersionService,
        history_service: AlertHistoryService,
        repository: 'Repository'
    ):
        self.full_analyzer = full_analyzer
        self.version_service = version_service
        self.history_service = history_service
        self.repo = repository

    def analyze(
        self,
        project_id: int,
        document: 'ParsedDocument',
        force_full: bool = False
    ) -> 'AnalysisResult':
        """
        Analiza el documento, solo cambios si es posible.

        Args:
            project_id: ID del proyecto
            document: Documento parseado
            force_full: Si True, ignora análisis previo y hace análisis completo
        """
        # Crear nueva versión
        version = self.version_service.create_version(project_id, document)

        if force_full or version.version_number == 1:
            # Primer análisis o forzado: análisis completo
            return self._full_analysis(project_id, document, version)
        else:
            # Análisis incremental
            return self._incremental_analysis(project_id, document, version)

    def _full_analysis(
        self,
        project_id: int,
        document: 'ParsedDocument',
        version: DocumentVersion
    ) -> 'AnalysisResult':
        """Ejecuta análisis completo."""
        # Obtener alertas ignoradas permanentemente
        dismissed = self.history_service.get_dismissed_patterns(project_id)

        # Ejecutar pipeline completo
        result = self.full_analyzer.run(document)

        # Filtrar alertas ya ignoradas
        result.alerts = self._filter_dismissed_alerts(result.alerts, dismissed)

        return result

    def _incremental_analysis(
        self,
        project_id: int,
        document: 'ParsedDocument',
        version: DocumentVersion
    ) -> 'AnalysisResult':
        """Ejecuta análisis solo en partes modificadas."""

        modified_chapters = version.chapters_modified | version.chapters_added

        if not modified_chapters:
            # No hay cambios, solo verificar alertas resueltas
            return self._verify_resolved_alerts(project_id, document)

        # 1. Analizar solo capítulos modificados
        result = AnalysisResult()

        for chapter_num in modified_chapters:
            chapter = document.get_chapter(chapter_num)
            if chapter:
                chapter_result = self.full_analyzer.analyze_chapter(chapter)
                result.merge(chapter_result)

        # 2. Re-verificar alertas existentes en capítulos modificados
        existing_alerts = self.repo.get_alerts_for_chapters(
            project_id, list(modified_chapters)
        )

        for alert in existing_alerts:
            self._check_alert_validity(alert, document)

        # 3. Verificar alertas resueltas (por si el texto volvió a cambiar)
        self._check_resolved_alerts(project_id, document, version)

        # 4. Filtrar alertas ya ignoradas
        dismissed = self.history_service.get_dismissed_patterns(project_id)
        result.alerts = self._filter_dismissed_alerts(result.alerts, dismissed)

        # 5. Marcar alertas obsoletas (en capítulos eliminados)
        self._mark_obsolete_alerts(project_id, version.chapters_deleted)

        return result

    def _filter_dismissed_alerts(
        self,
        alerts: List['Alert'],
        dismissed_patterns: List[dict]
    ) -> List['Alert']:
        """Filtra alertas que coinciden con patrones ignorados."""
        filtered = []

        for alert in alerts:
            is_dismissed = False

            for pattern in dismissed_patterns:
                if self._matches_pattern(alert, pattern):
                    is_dismissed = True
                    break

            if not is_dismissed:
                filtered.append(alert)

        return filtered

    def _matches_pattern(self, alert: 'Alert', pattern: dict) -> bool:
        """Verifica si una alerta coincide con un patrón ignorado."""
        # Comparar por tipo y entidades involucradas
        if pattern.get('alert_type') != alert.alert_type:
            return False

        if pattern.get('entity_ids'):
            if not set(pattern['entity_ids']).issubset(set(alert.entity_ids)):
                return False

        # Comparar por contenido similar (si aplica)
        if pattern.get('content_hash'):
            alert_hash = self._hash_alert_content(alert)
            if pattern['content_hash'] != alert_hash:
                return False

        return True

    def _verify_resolved_alerts(
        self,
        project_id: int,
        document: 'ParsedDocument'
    ) -> 'AnalysisResult':
        """Verifica que las alertas resueltas sigan resueltas."""
        resolved_alerts = self.repo.get_alerts_by_state(
            project_id, AlertState.RESOLVED
        )

        for alert in resolved_alerts:
            current_hash = self._get_text_hash_at_position(
                document, alert.chapter, alert.start_char, alert.end_char
            )
            self.history_service.check_for_reopen(alert.id, current_hash)

        return AnalysisResult()  # Sin nuevas alertas

    def _mark_obsolete_alerts(
        self,
        project_id: int,
        deleted_chapters: Set[int]
    ) -> None:
        """Marca como obsoletas las alertas de capítulos eliminados."""
        if not deleted_chapters:
            return

        alerts = self.repo.get_alerts_for_chapters(
            project_id, list(deleted_chapters)
        )

        for alert in alerts:
            history = self.repo.get_alert_history(alert.id)
            history.add_state_change(
                to_state=AlertState.OBSOLETE,
                changed_by="system",
                reason="chapter_deleted",
                note=f"Capítulo {alert.chapter} eliminado"
            )
            self.repo.save_alert_history(history)

    def _hash_alert_content(self, alert: 'Alert') -> str:
        """Genera hash del contenido de una alerta para comparación."""
        content = f"{alert.alert_type}:{alert.entity_ids}:{alert.excerpt}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_text_hash_at_position(
        self,
        document: 'ParsedDocument',
        chapter: int,
        start: int,
        end: int
    ) -> str:
        """Obtiene hash del texto en una posición específica."""
        text = document.get_text_at(chapter, start, end)
        return hashlib.sha256(text.encode()).hexdigest()[:16]
```

---

## Opciones de Reanálisis en UI

```python
class ReanalysisOptions:
    """Opciones disponibles para reanálisis."""

    INCREMENTAL = "incremental"          # Solo cambios (default)
    FULL_KEEP_DECISIONS = "full_keep"    # Completo, respetando ignoradas
    FULL_RESET = "full_reset"            # Completo, desde cero

    @staticmethod
    def get_description(option: str) -> str:
        descriptions = {
            "incremental": (
                "Analiza solo los cambios desde el último análisis. "
                "Mantiene decisiones previas (ignoradas, resueltas)."
            ),
            "full_keep": (
                "Analiza todo el documento de nuevo, pero respeta "
                "las alertas que marcaste como ignoradas."
            ),
            "full_reset": (
                "Análisis completo desde cero. Todas las alertas "
                "se regeneran, incluyendo las ignoradas."
            ),
        }
        return descriptions.get(option, "")

# En la CLI:
"""
$ narrative-assistant analyze mi_novela.docx --mode incremental  # Default
$ narrative-assistant analyze mi_novela.docx --mode full-keep
$ narrative-assistant analyze mi_novela.docx --mode full-reset
"""
```

---

## Siguiente

Ver [Análisis Progresivo](./progressive-analysis.md) para entender cómo se muestra el progreso en tiempo real.
