# STEP 7.2: Generador de Fichas de Personaje

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | M (4-6 horas) |
| **Prioridad** | P1 (Alto valor) |
| **Prerequisitos** | STEP 2.3, STEP 5.1 |

---

## Descripción

Generar fichas de personaje automáticas que resumen toda la información extraída sobre cada personaje:
- Atributos físicos
- Menciones y apariciones
- Relaciones detectadas
- Perfil de voz
- Inconsistencias asociadas

---

## Inputs

- Entidades de tipo personaje
- Atributos extraídos
- Menciones/apariciones
- Perfil de voz (si existe)
- Alertas asociadas

---

## Outputs

- `src/narrative_assistant/export/character_sheets.py`
- Ficha en formato estructurado
- Exportación a Markdown
- Exportación a JSON

---

## Modelo de Datos

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

@dataclass
class CharacterRelation:
    related_entity_id: int
    related_entity_name: str
    relation_type: str  # 'family', 'friend', 'enemy', 'colleague', etc.
    evidence: List[str]  # Excerpts que sugieren la relación
    confidence: float

@dataclass
class CharacterAppearance:
    chapter: int
    scene: Optional[int]
    first_mention_char: int
    mention_count: int
    has_dialogue: bool
    is_pov: bool  # Si es focalizador en esta escena

@dataclass
class CharacterSheet:
    # Identificación
    entity_id: int
    canonical_name: str
    aliases: List[str]
    entity_type: str  # 'person', 'organization', etc.

    # Atributos físicos
    physical_attributes: Dict[str, Dict[str, Any]]
    # Formato: { 'eye_color': { 'value': 'verdes', 'confidence': 0.9, 'source': {...} } }

    # Atributos psicológicos
    psychological_attributes: Dict[str, Dict[str, Any]]

    # Apariciones
    appearances: List[CharacterAppearance]
    first_appearance: Optional[int]  # Capítulo
    last_appearance: Optional[int]
    total_mentions: int

    # Relaciones
    relations: List[CharacterRelation]

    # Voz (si hay diálogos)
    voice_profile_summary: Optional[Dict[str, Any]] = None

    # Inconsistencias
    inconsistency_count: int = 0
    inconsistency_summary: List[str] = field(default_factory=list)

    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0  # Confianza general en los datos
```

---

## Implementación

```python
from typing import List, Dict, Optional, Any
from collections import defaultdict
from datetime import datetime

class CharacterSheetGenerator:
    def __init__(
        self,
        entity_repo: 'Repository',
        attribute_repo: 'Repository',
        alert_repo: 'Repository',
        voice_profiles: Optional[Dict[int, 'VoiceProfile']] = None
    ):
        self.entity_repo = entity_repo
        self.attribute_repo = attribute_repo
        self.alert_repo = alert_repo
        self.voice_profiles = voice_profiles or {}

    def generate_sheet(
        self,
        project_id: int,
        entity_id: int
    ) -> CharacterSheet:
        """Genera ficha completa de un personaje."""
        # Obtener entidad
        entity = self.entity_repo.get_entity(entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        # Obtener atributos
        attributes = self.attribute_repo.get_attributes_for_entity(entity_id)

        # Clasificar atributos
        physical_attrs = {}
        psychological_attrs = {}

        for attr in attributes:
            attr_data = {
                'value': attr.value,
                'confidence': attr.confidence,
                'source': {
                    'chapter': attr.source_chapter,
                    'excerpt': attr.source_excerpt
                }
            }

            if attr.attribute_type == 'physical':
                physical_attrs[attr.attribute_key] = attr_data
            elif attr.attribute_type == 'psychological':
                psychological_attrs[attr.attribute_key] = attr_data

        # Obtener menciones/apariciones
        mentions = self.entity_repo.get_mentions_for_entity(entity_id)
        appearances = self._build_appearances(mentions)

        # Obtener relaciones
        relations = self._detect_relations(entity_id, mentions)

        # Obtener inconsistencias
        alerts = self.alert_repo.get_alerts_for_entity(project_id, entity_id)
        inconsistency_summary = [
            a.description for a in alerts
            if a.category.value == 'consistency'
        ]

        # Resumen de perfil de voz
        voice_summary = None
        if entity_id in self.voice_profiles:
            voice_summary = self._summarize_voice_profile(
                self.voice_profiles[entity_id]
            )

        # Calcular confianza general
        confidence = self._calculate_overall_confidence(
            len(attributes),
            len(mentions),
            len(alerts)
        )

        return CharacterSheet(
            entity_id=entity_id,
            canonical_name=entity.canonical_name,
            aliases=list(entity.aliases) if hasattr(entity, 'aliases') else [],
            entity_type=entity.entity_type,
            physical_attributes=physical_attrs,
            psychological_attributes=psychological_attrs,
            appearances=appearances,
            first_appearance=appearances[0].chapter if appearances else None,
            last_appearance=appearances[-1].chapter if appearances else None,
            total_mentions=len(mentions),
            relations=relations,
            voice_profile_summary=voice_summary,
            inconsistency_count=len(inconsistency_summary),
            inconsistency_summary=inconsistency_summary[:5],  # Top 5
            confidence_score=confidence
        )

    def _build_appearances(
        self,
        mentions: List['TextReference']
    ) -> List[CharacterAppearance]:
        """Construye lista de apariciones por capítulo."""
        by_chapter: Dict[int, List] = defaultdict(list)

        for mention in mentions:
            by_chapter[mention.chapter].append(mention)

        appearances = []
        for chapter in sorted(by_chapter.keys()):
            chapter_mentions = by_chapter[chapter]
            appearances.append(CharacterAppearance(
                chapter=chapter,
                scene=None,  # Simplificado
                first_mention_char=min(m.start_char for m in chapter_mentions),
                mention_count=len(chapter_mentions),
                has_dialogue=any(m.context_type == 'dialogue' for m in chapter_mentions),
                is_pov=False  # Se determinaría con información de focalización
            ))

        return appearances

    def _detect_relations(
        self,
        entity_id: int,
        mentions: List['TextReference']
    ) -> List[CharacterRelation]:
        """Detecta relaciones basándose en co-ocurrencias."""
        # Simplificado: detectar entidades que aparecen cerca frecuentemente
        # En implementación completa, usar patrones de relación

        co_occurrences: Dict[int, List[str]] = defaultdict(list)

        for mention in mentions:
            # Buscar otras entidades en el mismo contexto
            context = mention.context or ""
            # Esto requeriría acceso a otras menciones cercanas
            # Placeholder para la lógica real

        relations = []
        # Las relaciones se detectarían con análisis más profundo

        return relations

    def _summarize_voice_profile(
        self,
        profile: 'VoiceProfile'
    ) -> Dict[str, Any]:
        """Resume perfil de voz para la ficha."""
        return {
            'total_interventions': profile.total_interventions,
            'avg_length': round(profile.avg_intervention_length, 1),
            'formality': f"{profile.formality_score:.0%}",
            'type_token_ratio': round(profile.type_token_ratio, 3),
            'characteristic_fillers': list(profile.filler_words.keys())[:3],
            'uses_usted': profile.uses_usted,
            'uses_tu': profile.uses_tu,
        }

    def _calculate_overall_confidence(
        self,
        attr_count: int,
        mention_count: int,
        alert_count: int
    ) -> float:
        """Calcula confianza general en los datos del personaje."""
        # Más menciones y atributos = más confianza
        # Más alertas = menos confianza

        base = 0.5

        # Bonus por cantidad de datos
        if mention_count > 10:
            base += 0.1
        if mention_count > 50:
            base += 0.1
        if attr_count > 3:
            base += 0.1

        # Penalización por inconsistencias
        if alert_count > 0:
            base -= min(0.2, alert_count * 0.05)

        return max(0.1, min(1.0, base))

    def export_to_markdown(self, sheet: CharacterSheet) -> str:
        """Exporta ficha a Markdown."""
        lines = [
            f"# Ficha de Personaje: {sheet.canonical_name}",
            "",
            "## Información General",
            "",
            f"- **ID:** {sheet.entity_id}",
            f"- **Tipo:** {sheet.entity_type}",
            f"- **Aliases:** {', '.join(sheet.aliases) if sheet.aliases else 'Ninguno'}",
            f"- **Menciones totales:** {sheet.total_mentions}",
            f"- **Primera aparición:** Capítulo {sheet.first_appearance or '?'}",
            f"- **Última aparición:** Capítulo {sheet.last_appearance or '?'}",
            f"- **Confianza de datos:** {sheet.confidence_score:.0%}",
            "",
        ]

        # Atributos físicos
        if sheet.physical_attributes:
            lines.extend([
                "## Atributos Físicos",
                "",
                "| Atributo | Valor | Confianza | Fuente |",
                "|----------|-------|-----------|--------|",
            ])
            for key, data in sheet.physical_attributes.items():
                source = f"Cap. {data['source']['chapter']}"
                lines.append(
                    f"| {key} | {data['value']} | {data['confidence']:.0%} | {source} |"
                )
            lines.append("")

        # Perfil de voz
        if sheet.voice_profile_summary:
            vp = sheet.voice_profile_summary
            lines.extend([
                "## Perfil de Voz",
                "",
                f"- **Intervenciones:** {vp['total_interventions']}",
                f"- **Longitud media:** {vp['avg_length']} palabras",
                f"- **Formalidad:** {vp['formality']}",
                f"- **Riqueza léxica (TTR):** {vp['type_token_ratio']}",
                f"- **Usa 'usted':** {'Sí' if vp['uses_usted'] else 'No'}",
                f"- **Usa 'tú':** {'Sí' if vp['uses_tu'] else 'No'}",
            ])
            if vp['characteristic_fillers']:
                lines.append(f"- **Muletillas:** {', '.join(vp['characteristic_fillers'])}")
            lines.append("")

        # Apariciones
        lines.extend([
            "## Apariciones por Capítulo",
            "",
            "| Capítulo | Menciones | ¿Diálogo? |",
            "|----------|-----------|-----------|",
        ])
        for app in sheet.appearances[:10]:  # Primeras 10
            dialogue = "Sí" if app.has_dialogue else "No"
            lines.append(f"| {app.chapter} | {app.mention_count} | {dialogue} |")
        if len(sheet.appearances) > 10:
            lines.append(f"| ... | ({len(sheet.appearances) - 10} más) | |")
        lines.append("")

        # Inconsistencias
        if sheet.inconsistency_count > 0:
            lines.extend([
                "## ⚠️ Inconsistencias Detectadas",
                "",
                f"**Total:** {sheet.inconsistency_count}",
                "",
            ])
            for inc in sheet.inconsistency_summary:
                lines.append(f"- {inc}")
            lines.append("")

        lines.extend([
            "---",
            f"*Generado: {sheet.generated_at.strftime('%Y-%m-%d %H:%M')}*"
        ])

        return "\n".join(lines)

    def export_to_json(self, sheet: CharacterSheet) -> Dict[str, Any]:
        """Exporta ficha a diccionario JSON-serializable."""
        return {
            'entity_id': sheet.entity_id,
            'canonical_name': sheet.canonical_name,
            'aliases': sheet.aliases,
            'entity_type': sheet.entity_type,
            'physical_attributes': sheet.physical_attributes,
            'psychological_attributes': sheet.psychological_attributes,
            'appearances': [
                {
                    'chapter': a.chapter,
                    'mention_count': a.mention_count,
                    'has_dialogue': a.has_dialogue,
                }
                for a in sheet.appearances
            ],
            'first_appearance': sheet.first_appearance,
            'last_appearance': sheet.last_appearance,
            'total_mentions': sheet.total_mentions,
            'voice_profile': sheet.voice_profile_summary,
            'inconsistency_count': sheet.inconsistency_count,
            'confidence_score': sheet.confidence_score,
            'generated_at': sheet.generated_at.isoformat(),
        }

    def generate_all_sheets(
        self,
        project_id: int
    ) -> List[CharacterSheet]:
        """Genera fichas para todos los personajes del proyecto."""
        entities = self.entity_repo.get_entities_by_type(project_id, 'person')
        return [self.generate_sheet(project_id, e.id) for e in entities]
```

---

## Criterio de DONE

```python
from narrative_assistant.export import CharacterSheetGenerator

# Mocks simplificados
class MockEntity:
    def __init__(self):
        self.id = 1
        self.canonical_name = "María García"
        self.entity_type = "person"
        self.aliases = ["María", "La profesora"]

class MockAttribute:
    def __init__(self, key, value, attr_type):
        self.attribute_key = key
        self.value = value
        self.attribute_type = attr_type
        self.confidence = 0.9
        self.source_chapter = 1
        self.source_excerpt = "..."

class MockMention:
    def __init__(self, chapter, start):
        self.chapter = chapter
        self.start_char = start
        self.context_type = "narrative"
        self.context = ""

class MockRepo:
    def get_entity(self, eid):
        return MockEntity()

    def get_attributes_for_entity(self, eid):
        return [
            MockAttribute("eye_color", "verdes", "physical"),
            MockAttribute("hair", "castaño", "physical"),
            MockAttribute("age", "35", "physical"),
        ]

    def get_mentions_for_entity(self, eid):
        return [
            MockMention(1, 100),
            MockMention(1, 500),
            MockMention(2, 200),
            MockMention(3, 300),
        ]

    def get_alerts_for_entity(self, pid, eid):
        return []

    def get_entities_by_type(self, pid, etype):
        return [MockEntity()]

generator = CharacterSheetGenerator(
    entity_repo=MockRepo(),
    attribute_repo=MockRepo(),
    alert_repo=MockRepo()
)

# Generar ficha
sheet = generator.generate_sheet(project_id=1, entity_id=1)

# Verificaciones
assert sheet.canonical_name == "María García"
assert "eye_color" in sheet.physical_attributes
assert sheet.total_mentions == 4
assert len(sheet.appearances) == 3  # Capítulos 1, 2, 3

# Exportar a Markdown
md = generator.export_to_markdown(sheet)
assert "María García" in md
assert "verdes" in md

# Exportar a JSON
json_data = generator.export_to_json(sheet)
assert json_data['entity_id'] == 1

print(f"✅ Ficha de personaje generada")
print(md[:500])
```

---

## Siguiente

[STEP 7.3: Guía de Estilo](./step-7.3-style-guide.md)
