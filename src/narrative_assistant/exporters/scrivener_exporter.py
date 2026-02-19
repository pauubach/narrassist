"""
Exportador a formato Scrivener (.scriv).

Genera un paquete .scriv compatible con Scrivener 3 que contiene:
- Archivo .scrivx con la estructura del proyecto (XML)
- Archivos RTF con el contenido de cada capítulo
- Metadatos de entidades como notas del documento
- Alertas como anotaciones inline

El formato .scriv es un directorio que se comprime en ZIP
para su descarga y posterior descompresión.

Referencia del formato:
- .scrivx: XML con la estructura del binder (carpetas, documentos)
- Files/Data/{UUID}/content.rtf: Contenido de cada documento
- Files/Data/{UUID}/notes.rtf: Notas del documento
"""

import io
import logging
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from xml.etree import ElementTree as ET

from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result

logger = logging.getLogger(__name__)


# =============================================================================
# Tipos
# =============================================================================


@dataclass
class ScrivenerExportOptions:
    """Opciones de exportación a Scrivener."""

    include_character_notes: bool = True  # Fichas de personaje como notas
    include_alerts_as_notes: bool = True  # Alertas como notas de documento
    include_entity_keywords: bool = True  # Entidades como keywords
    chapter_as_folders: bool = True  # Capítulos como carpetas
    include_synopsis: bool = True  # Sinopsis por capítulo


@dataclass
class ScrivenerChapter:
    """Datos de un capítulo para exportar."""

    number: int
    title: str
    content: str
    word_count: int = 0
    synopsis: str = ""
    entities: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)


@dataclass
class ScrivenerCharacter:
    """Datos de un personaje para la ficha."""

    name: str
    entity_type: str = "character"
    importance: str = ""
    aliases: list[str] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class ScrivenerExportData:
    """Datos completos para exportar a Scrivener."""

    project_name: str
    project_id: int = 0
    author: str = ""
    chapters: list[ScrivenerChapter] = field(default_factory=list)
    characters: list[ScrivenerCharacter] = field(default_factory=list)


# =============================================================================
# Exporter
# =============================================================================


class ScrivenerExporter:
    """
    Exporta un proyecto a formato Scrivener 3 (.scriv).

    El resultado es un archivo ZIP que contiene la estructura
    de un paquete .scriv listo para abrir en Scrivener.
    """

    # Version de formato Scrivener
    SCRIV_VERSION = "3.0"
    SCRIVX_VERSION = "2.0"

    def export(
        self,
        data: ScrivenerExportData,
        options: ScrivenerExportOptions | None = None,
    ) -> Result[bytes]:
        """
        Exporta a formato Scrivener como bytes ZIP.

        Args:
            data: Datos del proyecto a exportar
            options: Opciones de exportación

        Returns:
            Result[bytes] con el contenido ZIP del .scriv
        """
        if options is None:
            options = ScrivenerExportOptions()

        try:
            safe_name = self._sanitize_filename(data.project_name)
            scriv_name = f"{safe_name}.scriv"

            # Generar UUIDs para cada documento
            doc_uuids: dict[str, str] = {}

            # Manuscrito (carpeta raíz)
            manuscript_uuid = self._gen_uuid()
            doc_uuids["manuscript"] = manuscript_uuid

            # Capítulos
            chapter_items: list[dict[str, Any]] = []
            for chapter in data.chapters:
                ch_uuid = self._gen_uuid()
                ch_key = f"chapter_{chapter.number}"
                doc_uuids[ch_key] = ch_uuid
                chapter_items.append(
                    {
                        "uuid": ch_uuid,
                        "title": chapter.title or f"Capítulo {chapter.number}",
                        "content": chapter.content,
                        "synopsis": chapter.synopsis,
                        "word_count": chapter.word_count or len(chapter.content.split()),
                        "entities": chapter.entities,
                        "alerts": chapter.alerts,
                        "type": "Text",
                    }
                )

            # Personajes (carpeta de research)
            research_uuid = self._gen_uuid()
            doc_uuids["research"] = research_uuid
            characters_folder_uuid = self._gen_uuid()
            doc_uuids["characters_folder"] = characters_folder_uuid

            character_items: list[dict[str, Any]] = []
            if options.include_character_notes:
                for char in data.characters:
                    char_uuid = self._gen_uuid()
                    doc_uuids[f"char_{char.name}"] = char_uuid
                    character_items.append(
                        {
                            "uuid": char_uuid,
                            "title": char.name,
                            "content": self._build_character_content(char),
                            "type": "Text",
                        }
                    )

            # Construir ZIP
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                # version.txt
                zf.writestr(f"{scriv_name}/version.txt", self.SCRIV_VERSION)

                # .scrivx
                scrivx_content = self._build_scrivx(
                    project_name=data.project_name,
                    manuscript_uuid=manuscript_uuid,
                    chapter_items=chapter_items,
                    research_uuid=research_uuid,
                    characters_folder_uuid=characters_folder_uuid,
                    character_items=character_items,
                    options=options,
                )
                zf.writestr(f"{scriv_name}/{safe_name}.scrivx", scrivx_content)

                # Archivos RTF para capítulos
                for item in chapter_items:
                    rtf_content = self._text_to_rtf(item["content"])
                    zf.writestr(f"{scriv_name}/Files/Data/{item['uuid']}/content.rtf", rtf_content)

                    # Notas con alertas
                    if options.include_alerts_as_notes and item.get("alerts"):
                        notes = "\n\n".join(item["alerts"])
                        notes_rtf = self._text_to_rtf(f"ALERTAS:\n\n{notes}")
                        zf.writestr(f"{scriv_name}/Files/Data/{item['uuid']}/notes.rtf", notes_rtf)

                    # Synopsis
                    if options.include_synopsis and item.get("synopsis"):
                        self._text_to_rtf(item["synopsis"])
                        zf.writestr(
                            f"{scriv_name}/Files/Data/{item['uuid']}/synopsis.txt", item["synopsis"]
                        )

                # Archivos RTF para personajes
                for item in character_items:
                    rtf_content = self._text_to_rtf(item["content"])
                    zf.writestr(f"{scriv_name}/Files/Data/{item['uuid']}/content.rtf", rtf_content)

                # Settings vacíos
                zf.writestr(f"{scriv_name}/Settings/ui.plist", self._empty_plist())

            return Result.success(buffer.getvalue())

        except Exception as e:
            logger.error(f"Error exportando a Scrivener: {e}", exc_info=True)
            return Result.failure(
                NarrativeError(
                    message=f"Error exportando a Scrivener: {e}",
                    severity=ErrorSeverity.RECOVERABLE,
                )
            )

    def _build_scrivx(
        self,
        project_name: str,
        manuscript_uuid: str,
        chapter_items: list[dict],
        research_uuid: str,
        characters_folder_uuid: str,
        character_items: list[dict],
        options: ScrivenerExportOptions,
    ) -> str:
        """Construye el XML del archivo .scrivx."""
        root = ET.Element("ScrivenerProject")
        root.set("Version", self.SCRIVX_VERSION)
        root.set("Creator", "NarrativeAssistant")
        root.set("Modified", datetime.now().isoformat())

        # Binder
        binder = ET.SubElement(root, "Binder")

        # DraftFolder (Manuscrito)
        draft = ET.SubElement(binder, "BinderItem")
        draft.set("UUID", manuscript_uuid)
        draft.set("Type", "DraftFolder")
        draft.set("Created", datetime.now().isoformat())
        title_el = ET.SubElement(draft, "Title")
        title_el.text = "Manuscrito"

        children = ET.SubElement(draft, "Children")
        for item in chapter_items:
            child = ET.SubElement(children, "BinderItem")
            child.set("UUID", item["uuid"])
            child.set("Type", item["type"])
            child.set("Created", datetime.now().isoformat())
            child_title = ET.SubElement(child, "Title")
            child_title.text = item["title"]

            # Metadatos
            meta = ET.SubElement(child, "MetaData")
            if item.get("word_count"):
                target = ET.SubElement(meta, "TextSettings")
                wc = ET.SubElement(target, "WordCount")
                wc.text = str(item["word_count"])

            # Keywords (entidades)
            if options.include_entity_keywords and item.get("entities"):
                keywords = ET.SubElement(child, "Keywords")
                for entity_name in item["entities"]:
                    kw = ET.SubElement(keywords, "Keyword")
                    kw.text = entity_name

        # ResearchFolder
        research = ET.SubElement(binder, "BinderItem")
        research.set("UUID", research_uuid)
        research.set("Type", "ResearchFolder")
        research.set("Created", datetime.now().isoformat())
        research_title = ET.SubElement(research, "Title")
        research_title.text = "Investigación"

        research_children = ET.SubElement(research, "Children")

        # Carpeta de personajes
        if character_items:
            chars_folder = ET.SubElement(research_children, "BinderItem")
            chars_folder.set("UUID", characters_folder_uuid)
            chars_folder.set("Type", "Folder")
            chars_folder.set("Created", datetime.now().isoformat())
            chars_title = ET.SubElement(chars_folder, "Title")
            chars_title.text = "Personajes"

            chars_children = ET.SubElement(chars_folder, "Children")
            for item in character_items:
                char_item = ET.SubElement(chars_children, "BinderItem")
                char_item.set("UUID", item["uuid"])
                char_item.set("Type", item["type"])
                char_item.set("Created", datetime.now().isoformat())
                char_title = ET.SubElement(char_item, "Title")
                char_title.text = item["title"]

        # TrashFolder
        trash_uuid = self._gen_uuid()
        trash = ET.SubElement(binder, "BinderItem")
        trash.set("UUID", trash_uuid)
        trash.set("Type", "TrashFolder")
        trash.set("Created", datetime.now().isoformat())
        trash_title = ET.SubElement(trash, "Title")
        trash_title.text = "Papelera"

        # ProjectProperties
        props = ET.SubElement(root, "ProjectProperties")
        proj_title = ET.SubElement(props, "ProjectTitle")
        proj_title.text = project_name

        # Serializar
        tree = ET.ElementTree(root)
        output = io.StringIO()
        tree.write(output, encoding="unicode", xml_declaration=True)
        return output.getvalue()

    def _build_character_content(self, char: ScrivenerCharacter) -> str:
        """Construye el contenido de texto para una ficha de personaje."""
        lines = [f"FICHA DE PERSONAJE: {char.name}", "=" * 40, ""]

        if char.importance:
            lines.append(f"Importancia: {char.importance}")

        if char.aliases:
            lines.append(f"Aliases: {', '.join(char.aliases)}")

        if char.description:
            lines.append(f"\nDescripción: {char.description}")

        if char.attributes:
            lines.append("\n--- ATRIBUTOS ---\n")
            for key, value in char.attributes.items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)

    def _text_to_rtf(self, text: str) -> str:
        """Convierte texto plano a RTF básico."""
        # Escapar caracteres especiales RTF
        escaped = text.replace("\\", "\\\\")
        escaped = escaped.replace("{", "\\{")
        escaped = escaped.replace("}", "\\}")

        # Convertir caracteres Unicode a escapes RTF
        rtf_chars = []
        for ch in escaped:
            code = ord(ch)
            if code > 127:
                rtf_chars.append(f"\\u{code}?")
            elif ch == "\n":
                rtf_chars.append("\\par\n")
            else:
                rtf_chars.append(ch)

        body = "".join(rtf_chars)

        return (
            r"{\rtf1\ansi\ansicpg1252\cocoartf2639"
            r"{\fonttbl\f0\froman\fcharset0 TimesNewRomanPSMT;}"
            r"{\colortbl;\red255\green255\blue255;}"
            r"\margl1440\margr1440\margt1440\margb1440"
            r"\f0\fs24 "
            f"{body}"
            r"}"
        )

    def _gen_uuid(self) -> str:
        """Genera un UUID para identificar documentos en Scrivener."""
        return str(uuid.uuid4()).upper()

    def _sanitize_filename(self, name: str) -> str:
        """Sanitiza el nombre del archivo."""
        # Eliminar caracteres no permitidos
        safe = "".join(c for c in name if c.isalnum() or c in " -_.").strip()
        return safe or "Proyecto"

    def _empty_plist(self) -> str:
        """Genera un plist vacío para settings."""
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n'
            "<dict/>\n"
            "</plist>"
        )


# =============================================================================
# Funciones de conveniencia
# =============================================================================


def export_to_scrivener(
    project_id: int,
    options: ScrivenerExportOptions | None = None,
) -> Result[bytes]:
    """
    Exporta un proyecto a formato Scrivener .scriv (como ZIP).

    Args:
        project_id: ID del proyecto
        options: Opciones de exportación

    Returns:
        Result[bytes] con el contenido ZIP
    """
    try:
        from ..entities.repository import get_entity_repository
        from ..persistence.chapter import get_chapter_repository
        from ..persistence.project import ProjectManager

        # Cargar proyecto
        pm = ProjectManager()
        result = pm.get(project_id)
        if result.is_failure:
            return Result.failure(result.error)

        project = result.value
        assert project is not None

        # Cargar capítulos
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)

        # Cargar entidades
        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)

        # Preparar datos
        export_data = ScrivenerExportData(
            project_name=project.name,
            project_id=project_id,
        )

        # Capítulos
        for ch in chapters:
            # Entidades mencionadas en el capítulo
            ch_entities = []
            for entity in entities:
                if entity.id is None:
                    continue
                mentions = entity_repo.get_mentions_by_entity(entity.id)
                for m in mentions:
                    if hasattr(m, "chapter_id") and m.chapter_id == ch.chapter_number:
                        ch_entities.append(entity.canonical_name)
                        break

            export_data.chapters.append(
                ScrivenerChapter(
                    number=ch.chapter_number,
                    title=getattr(ch, "title", f"Capítulo {ch.chapter_number}"),
                    content=ch.content or "",
                    word_count=len((ch.content or "").split()),
                    entities=ch_entities,
                )
            )

        # Personajes
        for entity in entities:
            etype = str(getattr(entity, "entity_type", "")).upper()
            if etype in ("CHARACTER", "PERSON", "PER"):
                attrs = {}
                try:
                    from ..nlp.attributes import get_attribute_extractor

                    extractor = get_attribute_extractor()
                    entity_attrs = extractor.get_attributes_for_entity(entity.id)
                    for attr in entity_attrs:
                        key = getattr(attr, "key", "")
                        value = getattr(attr, "value", "")
                        if key and value:
                            attrs[key] = value
                except Exception:
                    pass

                export_data.characters.append(
                    ScrivenerCharacter(
                        name=entity.canonical_name,
                        importance=str(getattr(entity, "importance", "")),
                        aliases=list(entity.aliases) if entity.aliases else [],
                        attributes=attrs,
                        description=getattr(entity, "description", "") or "",
                    )
                )

        # Exportar
        exporter = ScrivenerExporter()
        return exporter.export(export_data, options)

    except Exception as e:
        logger.error(f"Error en export_to_scrivener: {e}", exc_info=True)
        return Result.failure(
            NarrativeError(
                message=f"Error exportando a Scrivener: {e}",
                severity=ErrorSeverity.RECOVERABLE,
            )
        )
