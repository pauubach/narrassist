"""
Router: editorial
"""

from fastapi import APIRouter
import deps
from deps import logger
from deps import ApiResponse
from fastapi import HTTPException
from fastapi import Body
from fastapi import Request
from fastapi import Query
from typing import Optional, Any
from datetime import datetime
from deps import DefaultOverrideRequest, EditorialRulesRequest, CorrectionConfigUpdate, _field_label

router = APIRouter()

@router.get("/api/projects/{project_id}/editorial-rules", response_model=ApiResponse)
async def get_editorial_rules(project_id: int):
    """
    Obtiene las reglas editoriales de un proyecto.

    Las reglas son texto libre que el corrector define para el manuscrito.
    Ejemplos:
    - "nuestros corazones" -> "nuestro corazon" (organos unicos en singular)
    - "quizas" -> "quiza" (preferencia editorial)
    - edades con numeros, anos con letra

    Returns:
        ApiResponse con las reglas del proyecto
    """
    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Verificar que el proyecto existe
        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Obtener reglas de la base de datos
        db = deps.project_manager.db
        with db.connection() as conn:
            cursor = conn.execute(
                "SELECT rules_text, enabled, created_at, updated_at FROM editorial_rules WHERE project_id = ?",
                (project_id,)
            )
            row = cursor.fetchone()

            if row:
                return ApiResponse(
                    success=True,
                    data={
                        "project_id": project_id,
                        "rules_text": row["rules_text"],
                        "enabled": bool(row["enabled"]),
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                )
            else:
                # No hay reglas definidas - devolver defaults vacios
                return ApiResponse(
                    success=True,
                    data={
                        "project_id": project_id,
                        "rules_text": "",
                        "enabled": True,
                        "created_at": None,
                        "updated_at": None,
                    }
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting editorial rules: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.post("/api/projects/{project_id}/editorial-rules", response_model=ApiResponse)
async def save_editorial_rules(project_id: int, request: EditorialRulesRequest):
    """
    Guarda las reglas editoriales de un proyecto.

    Las reglas se interpretan durante el analisis de estilo para detectar
    problemas especificos de la editorial o corrector.

    Args:
        project_id: ID del proyecto
        request: Texto de reglas y estado de habilitacion

    Returns:
        ApiResponse confirmando el guardado
    """
    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Verificar que el proyecto existe
        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Guardar o actualizar reglas
        db = deps.project_manager.db
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO editorial_rules (project_id, rules_text, enabled, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(project_id) DO UPDATE SET
                    rules_text = excluded.rules_text,
                    enabled = excluded.enabled,
                    updated_at = datetime('now')
                """,
                (project_id, request.rules_text, int(request.enabled))
            )
            conn.commit()

        logger.info(f"Editorial rules saved for project {project_id}")

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "rules_text": request.rules_text,
                "enabled": request.enabled,
                "message": "Reglas editoriales guardadas correctamente"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving editorial rules: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.post("/api/projects/{project_id}/editorial-rules/check", response_model=ApiResponse)
async def check_editorial_rules(project_id: int, text: str = Body(..., embed=True)):
    """
    Aplica las reglas editoriales a un texto y devuelve los problemas encontrados.

    Este endpoint permite verificar un fragmento de texto contra las reglas
    definidas para el proyecto.

    Args:
        project_id: ID del proyecto
        text: Texto a verificar

    Returns:
        ApiResponse con los problemas encontrados
    """
    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Verificar proyecto
        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Obtener reglas del proyecto
        db = deps.project_manager.db
        with db.connection() as conn:
            cursor = conn.execute(
                "SELECT rules_text, enabled FROM editorial_rules WHERE project_id = ?",
                (project_id,)
            )
            row = cursor.fetchone()

        # Aplicar verificador de reglas editoriales
        from narrative_assistant.nlp.style.editorial_rules import check_with_user_rules

        # Obtener reglas del usuario (si existen)
        user_rules_text = ""
        if row and row["enabled"] and row["rules_text"]:
            user_rules_text = row["rules_text"]

        # Verificar texto con reglas predefinidas + reglas del usuario
        report = check_with_user_rules(
            text=text,
            user_rules_text=user_rules_text,
            include_predefined=True  # Siempre incluir reglas base
        )

        return ApiResponse(
            success=True,
            data={
                "issues": report.to_dict()["issues"],
                "rules_applied": report.rules_applied,
                "issue_count": report.issue_count,
                "has_user_rules": bool(user_rules_text),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking editorial rules: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.put("/api/projects/{project_id}/correction-config", response_model=ApiResponse)
async def update_project_correction_config(
    project_id: str,
    update: CorrectionConfigUpdate,
) -> ApiResponse:
    """
    Actualiza la configuración de corrección de un proyecto.

    El nuevo sistema guarda solo las personalizaciones (customizations),
    no la configuración completa. La configuración base se hereda del tipo/subtipo.
    """
    try:
        result = deps.project_manager.get(int(project_id))
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        # Nuevo sistema: guardar solo customizations
        if update.customizations is not None:
            project.settings["correction_customizations"] = update.customizations
            logger.info(f"Saving correction customizations for project {project_id}: {len(update.customizations)} categories")
        # Legacy compat: guardar config completa
        elif update.config is not None:
            from narrative_assistant.corrections.config import CorrectionConfig
            try:
                config = CorrectionConfig.from_dict(update.config)
                project.settings["correction_config"] = config.to_dict()
            except Exception as e:
                return ApiResponse(success=False, error=f"Configuración inválida: {str(e)}")

        if update.selectedPreset:
            project.settings["correction_preset"] = update.selectedPreset

        update_result = deps.project_manager.update(project)
        if update_result.is_failure:
            logger.error(f"Failed to update project {project_id}: {update_result.errors}")
            return ApiResponse(success=False, error="Error al guardar configuración")

        logger.info(f"Successfully updated correction config for project {project_id}")

        # Obtener configuración efectiva para retornar
        from narrative_assistant.correction_config import get_config_for_project
        type_code = getattr(project, 'document_type', 'FIC') or 'FIC'
        subtype_code = getattr(project, 'document_subtype', None)
        effective_config = get_config_for_project(type_code, subtype_code, update.customizations)

        return ApiResponse(
            success=True,
            data={
                "config": effective_config,
                "message": "Configuración guardada correctamente",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating correction config: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.post("/api/projects/{project_id}/correction-config/apply-preset", response_model=ApiResponse)
async def apply_correction_preset(
    project_id: str,
    preset_id: str = Query(..., description="ID del preset a aplicar"),
) -> ApiResponse:
    """
    Aplica un preset de configuración a un proyecto.
    """
    try:
        result = deps.project_manager.get(int(project_id))
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.corrections.config import CorrectionConfig

        # Obtener el preset
        presets = {
            "default": CorrectionConfig.default,
            "novel": CorrectionConfig.for_novel,
            "technical": CorrectionConfig.for_technical,
            "legal": CorrectionConfig.for_legal,
            "medical": CorrectionConfig.for_medical,
            "journalism": CorrectionConfig.for_journalism,
            "selfhelp": CorrectionConfig.for_selfhelp,
        }

        if preset_id not in presets:
            return ApiResponse(
                success=False,
                error=f"Preset '{preset_id}' no encontrado"
            )

        config = presets[preset_id]()

        # Guardar configuración en settings del proyecto
        project.settings["correction_config"] = config.to_dict()
        project.settings["correction_preset"] = preset_id
        update_result = deps.project_manager.update(project)
        if update_result.is_failure:
            return ApiResponse(success=False, error="Error al guardar configuración")

        logger.info(f"Applied preset '{preset_id}' to project {project_id}")

        return ApiResponse(
            success=True,
            data={
                "config": config.to_dict(),
                "preset": preset_id,
                "message": f"Preset '{preset_id}' aplicado correctamente",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying preset: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.delete("/api/projects/{project_id}/correction-config", response_model=ApiResponse)
async def reset_project_correction_config(project_id: str) -> ApiResponse:
    """
    Elimina la configuración personalizada y vuelve a la por defecto.
    """
    try:
        result = deps.project_manager.get(int(project_id))
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.corrections.config import CorrectionConfig

        # Eliminar configuración de settings del proyecto
        needs_update = False
        if "correction_config" in project.settings:
            del project.settings["correction_config"]
            needs_update = True
        if "correction_preset" in project.settings:
            del project.settings["correction_preset"]
            needs_update = True

        if needs_update:
            update_result = deps.project_manager.update(project)
            if update_result.is_failure:
                return ApiResponse(success=False, error="Error al guardar configuración")
            logger.info(f"Deleted custom correction config for project {project_id}")

        return ApiResponse(
            success=True,
            data={
                "config": CorrectionConfig.default().to_dict(),
                "message": "Configuración restaurada a valores por defecto",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting correction config: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.post("/api/projects/{project_id}/correction-config/detect", response_model=ApiResponse)
async def detect_document_profile(project_id: str) -> ApiResponse:
    """
    Analiza el documento y sugiere un perfil de configuración.

    Detecta automáticamente:
    - Tipo de documento (literario, técnico, jurídico, etc.)
    - Nivel de registro (formal, coloquial)
    - Variante regional predominante
    - Presencia de diálogos
    """
    try:
        result = deps.project_manager.get(int(project_id))
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Project not found")
        project = result.value

        from narrative_assistant.corrections.config import (
            CorrectionConfig,
            DocumentField,
            RegisterLevel,
            AudienceType,
        )
        from narrative_assistant.corrections.detectors.regional import RegionalDetector
        from narrative_assistant.corrections.detectors.field_terminology import BUILTIN_FIELD_TERMS

        # Obtener texto del documento (primeros capítulos)
        chapters = deps.chapter_repository.get_by_project(int(project_id)) if deps.chapter_repository else []
        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "detected": False,
                    "reason": "No hay capítulos analizados",
                    "suggested_preset": "default",
                }
            )

        # Tomar muestra de texto (primeros 3 capítulos o 50000 chars)
        sample_text = ""
        for chapter in chapters[:3]:
            sample_text += (chapter.content or "") + "\n\n"
            if len(sample_text) > 50000:
                break
        sample_text = sample_text[:50000].lower()

        # === Detección de características ===

        # 1. Detectar diálogos (rayas, comillas con verbos de habla)
        dialogue_indicators = [
            "—", "–",  # Rayas de diálogo
            "dijo", "preguntó", "respondió", "exclamó", "susurró",
            "murmuró", "gritó", "contestó", "añadió", "explicó",
        ]
        dialogue_count = sum(sample_text.count(ind) for ind in dialogue_indicators)
        has_dialogues = dialogue_count > 10

        # 2. Detectar registro (formal vs coloquial)
        formal_indicators = [
            "asimismo", "no obstante", "cabe destacar", "en consecuencia",
            "por consiguiente", "dicho lo cual", "en virtud de", "habida cuenta",
        ]
        colloquial_indicators = [
            "vale", "tío", "mola", "guay", "flipar", "curro", "pasta",
            "joder", "hostia", "coño", "gilipollas", "mierda",
        ]
        formal_count = sum(sample_text.count(ind) for ind in formal_indicators)
        colloquial_count = sum(sample_text.count(ind) for ind in colloquial_indicators)

        if formal_count > colloquial_count * 2:
            detected_register = "formal"
        elif colloquial_count > formal_count * 2:
            detected_register = "colloquial"
        else:
            detected_register = "neutral"

        # 3. Detectar campo/dominio por terminología
        field_scores = {field: 0 for field in DocumentField}

        for term, info in BUILTIN_FIELD_TERMS.items():
            if term in sample_text:
                field = info["field"]
                field_scores[field] += sample_text.count(term)

        # Detectar términos jurídicos específicos
        legal_terms = ["demandante", "demandado", "sentencia", "recurso", "tribunal",
                      "jurisprudencia", "ley", "artículo", "código", "contrato"]
        for term in legal_terms:
            if term in sample_text:
                field_scores[DocumentField.LEGAL] += sample_text.count(term) * 2

        # Detectar términos médicos específicos
        medical_terms = ["paciente", "diagnóstico", "tratamiento", "síntoma",
                        "enfermedad", "medicamento", "dosis", "clínico"]
        for term in medical_terms:
            if term in sample_text:
                field_scores[DocumentField.MEDICAL] += sample_text.count(term) * 2

        # Detectar términos técnicos/informáticos
        tech_terms = ["código", "programa", "sistema", "datos", "servidor",
                     "aplicación", "usuario", "interfaz", "algoritmo"]
        for term in tech_terms:
            if term in sample_text:
                field_scores[DocumentField.TECHNICAL] += sample_text.count(term)

        # El campo con mayor puntuación
        max_field = max(field_scores.keys(), key=lambda f: field_scores[f])
        max_score = field_scores[max_field]

        # Si tiene diálogos y no hay campo técnico dominante, es literario
        if has_dialogues and max_score < 20:
            detected_field = DocumentField.LITERARY
        elif max_score > 15:
            detected_field = max_field
        else:
            detected_field = DocumentField.GENERAL

        # 4. Detectar variante regional
        region_scores = {"es_ES": 0, "es_MX": 0, "es_AR": 0}

        for term, info in RegionalDetector.BUILTIN_REGIONAL_TERMS.items():
            if term in sample_text:
                region = info["region"]
                if region in region_scores:
                    region_scores[region] += sample_text.count(term)

        detected_region = max(region_scores.keys(), key=lambda r: region_scores[r])
        if region_scores[detected_region] < 3:
            detected_region = "es_ES"  # Default si no hay suficiente evidencia

        # === Seleccionar preset recomendado ===
        preset_map = {
            DocumentField.LITERARY: "novel",
            DocumentField.TECHNICAL: "technical",
            DocumentField.LEGAL: "legal",
            DocumentField.MEDICAL: "medical",
            DocumentField.JOURNALISTIC: "journalism",
            DocumentField.SELFHELP: "selfhelp",
            DocumentField.ACADEMIC: "technical",  # Similar a técnico
            DocumentField.BUSINESS: "technical",
            DocumentField.GENERAL: "default",
            DocumentField.CULINARY: "default",
        }
        suggested_preset = preset_map.get(detected_field, "default")

        # Obtener la config del preset
        preset_configs = {
            "default": CorrectionConfig.default,
            "novel": CorrectionConfig.for_novel,
            "technical": CorrectionConfig.for_technical,
            "legal": CorrectionConfig.for_legal,
            "medical": CorrectionConfig.for_medical,
            "journalism": CorrectionConfig.for_journalism,
            "selfhelp": CorrectionConfig.for_selfhelp,
        }
        suggested_config = preset_configs[suggested_preset]()

        # Ajustar la config según detección
        config_dict = suggested_config.to_dict()
        config_dict["profile"]["region"] = detected_region
        config_dict["profile"]["register"] = detected_register
        config_dict["regional"]["target_region"] = detected_region

        # Construir explicación
        detection_reasons = []
        if has_dialogues:
            detection_reasons.append(f"Diálogos detectados ({dialogue_count} indicadores)")
        if detected_field != DocumentField.GENERAL:
            detection_reasons.append(f"Terminología de {_field_label(detected_field).lower()}")
        if detected_register != "neutral":
            reg_label = "formal" if detected_register == "formal" else "coloquial"
            detection_reasons.append(f"Registro {reg_label}")
        if region_scores[detected_region] >= 3:
            detection_reasons.append(f"Variante regional: {detected_region}")

        return ApiResponse(
            success=True,
            data={
                "detected": True,
                "suggested_preset": suggested_preset,
                "suggested_config": config_dict,
                "detection": {
                    "field": detected_field.value,
                    "field_label": _field_label(detected_field),
                    "register": detected_register,
                    "region": detected_region,
                    "has_dialogues": has_dialogues,
                    "dialogue_count": dialogue_count,
                    "field_scores": {f.value: s for f, s in field_scores.items() if s > 0},
                    "region_scores": region_scores,
                },
                "reasons": detection_reasons,
                "confidence": min(0.9, 0.5 + (max_score / 50) + (0.2 if has_dialogues else 0)),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting document profile: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/scenes", response_model=ApiResponse)
async def get_project_scenes(project_id: int):
    """
    Obtiene todas las escenas de un proyecto con sus etiquetas.

    Incluye metadata para determinar si mostrar la UI de escenas.
    """
    try:
        from narrative_assistant.scenes import SceneService

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        service = SceneService()
        scenes = service.get_scenes(project_id)
        stats = service.get_stats(project_id)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "has_scenes": stats.has_scenes,
                "total_scenes": stats.total_scenes,
                "stats": {
                    "chapters_with_scenes": stats.chapters_with_scenes,
                    "tagged_scenes": stats.tagged_scenes,
                    "untagged_scenes": stats.untagged_scenes,
                    "scenes_by_type": stats.scenes_by_type,
                    "scenes_by_tone": stats.scenes_by_tone,
                    "custom_tags_used": stats.custom_tags_used,
                },
                "scenes": [
                    {
                        "id": s.scene.id,
                        "chapter_id": s.scene.chapter_id,
                        "chapter_number": s.chapter_number,
                        "chapter_title": s.chapter_title,
                        "scene_number": s.scene.scene_number,
                        "start_char": s.scene.start_char,
                        "end_char": s.scene.end_char,
                        "word_count": s.scene.word_count,
                        "separator_type": s.scene.separator_type,
                        "excerpt": s.excerpt,
                        "tags": {
                            "scene_type": s.tags.scene_type.value if s.tags and s.tags.scene_type else None,
                            "tone": s.tags.tone.value if s.tags and s.tags.tone else None,
                            "location_entity_id": s.tags.location_entity_id if s.tags else None,
                            "location_name": s.location_name,
                            "participant_ids": s.tags.participant_ids if s.tags else [],
                            "participant_names": s.participant_names,
                            "summary": s.tags.summary if s.tags else None,
                            "notes": s.tags.notes if s.tags else None,
                        } if s.tags else None,
                        "custom_tags": [
                            {"name": ct.tag_name, "color": ct.tag_color}
                            for ct in s.custom_tags
                        ],
                    }
                    for s in scenes
                ],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scenes: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/scenes/stats", response_model=ApiResponse)
async def get_scenes_stats(project_id: int):
    """
    Obtiene solo las estadísticas de escenas (lightweight).

    Útil para determinar si mostrar el tab de escenas en la UI.
    """
    try:
        from narrative_assistant.scenes import SceneService

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        service = SceneService()
        stats = service.get_stats(project_id)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "has_scenes": stats.has_scenes,
                "total_scenes": stats.total_scenes,
                "chapters_with_scenes": stats.chapters_with_scenes,
                "tagged_scenes": stats.tagged_scenes,
                "untagged_scenes": stats.untagged_scenes,
                "scenes_by_type": stats.scenes_by_type,
                "scenes_by_tone": stats.scenes_by_tone,
                "custom_tags_used": stats.custom_tags_used,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scene stats: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.put("/api/projects/{project_id}/scenes/{scene_id}/tags", response_model=ApiResponse)
async def tag_scene(project_id: int, scene_id: int, data: dict):
    """
    Asigna etiquetas predefinidas a una escena.

    Body:
        - scene_type: tipo de escena (action, dialogue, exposition, etc.)
        - tone: tono emocional (tense, calm, happy, etc.)
        - location_entity_id: ID de la entidad de ubicación
        - participant_ids: lista de IDs de entidades participantes
        - summary: resumen breve
        - notes: notas del usuario
    """
    try:
        from narrative_assistant.scenes import SceneService, SceneType, SceneTone

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        service = SceneService()

        # Parse scene_type
        scene_type = None
        if data.get("scene_type"):
            try:
                scene_type = SceneType(data["scene_type"])
            except ValueError:
                return ApiResponse(success=False, error=f"Tipo de escena inválido: {data['scene_type']}")

        # Parse tone
        tone = None
        if data.get("tone"):
            try:
                tone = SceneTone(data["tone"])
            except ValueError:
                return ApiResponse(success=False, error=f"Tono inválido: {data['tone']}")

        success = service.tag_scene(
            scene_id=scene_id,
            scene_type=scene_type,
            tone=tone,
            location_entity_id=data.get("location_entity_id"),
            participant_ids=data.get("participant_ids", []),
            summary=data.get("summary"),
            notes=data.get("notes"),
        )

        if success:
            return ApiResponse(success=True, message="Escena etiquetada correctamente")
        return ApiResponse(success=False, error="Escena no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tagging scene: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.post("/api/projects/{project_id}/scenes/{scene_id}/custom-tags", response_model=ApiResponse)
async def add_custom_tag(project_id: int, scene_id: int, data: dict):
    """
    Añade una etiqueta personalizada a una escena.

    Body:
        - tag_name: nombre de la etiqueta
        - tag_color: color hex opcional (#FF5733)
    """
    try:
        from narrative_assistant.scenes import SceneService

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        tag_name = data.get("tag_name", "").strip()
        if not tag_name:
            return ApiResponse(success=False, error="Se requiere nombre de etiqueta")

        service = SceneService()
        success = service.add_custom_tag(
            scene_id=scene_id,
            tag_name=tag_name,
            tag_color=data.get("tag_color"),
        )

        if success:
            return ApiResponse(success=True, message=f"Etiqueta '{tag_name}' añadida")
        return ApiResponse(success=False, error="Escena no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding custom tag: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.delete("/api/projects/{project_id}/scenes/{scene_id}/custom-tags/{tag_name}", response_model=ApiResponse)
async def remove_custom_tag(project_id: int, scene_id: int, tag_name: str):
    """Elimina una etiqueta personalizada de una escena."""
    try:
        from narrative_assistant.scenes import SceneService

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        service = SceneService()
        success = service.remove_custom_tag(scene_id, tag_name)

        if success:
            return ApiResponse(success=True, message=f"Etiqueta '{tag_name}' eliminada")
        return ApiResponse(success=False, error="Etiqueta no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing custom tag: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/scenes/tag-catalog", response_model=ApiResponse)
async def get_tag_catalog(project_id: int):
    """Obtiene el catálogo de etiquetas personalizadas disponibles en el proyecto."""
    try:
        from narrative_assistant.scenes import SceneService

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        service = SceneService()
        catalog = service.get_tag_catalog(project_id)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "tags": catalog,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tag catalog: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/scenes/filter", response_model=ApiResponse)
async def filter_scenes(
    project_id: int,
    scene_type: Optional[str] = None,
    tone: Optional[str] = None,
    custom_tag: Optional[str] = None,
    location_id: Optional[int] = None,
    participant_id: Optional[int] = None,
):
    """
    Filtra escenas por criterios.

    Query params:
        - scene_type: filtrar por tipo (action, dialogue, etc.)
        - tone: filtrar por tono (tense, calm, etc.)
        - custom_tag: filtrar por etiqueta personalizada
        - location_id: filtrar por ubicación
        - participant_id: filtrar por participante
    """
    try:
        from narrative_assistant.scenes import SceneService, SceneType, SceneTone

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        # Parse filters
        parsed_type = None
        if scene_type:
            try:
                parsed_type = SceneType(scene_type)
            except ValueError:
                return ApiResponse(success=False, error=f"Tipo de escena inválido: {scene_type}")

        parsed_tone = None
        if tone:
            try:
                parsed_tone = SceneTone(tone)
            except ValueError:
                return ApiResponse(success=False, error=f"Tono inválido: {tone}")

        service = SceneService()
        scenes = service.filter_scenes(
            project_id=project_id,
            scene_type=parsed_type,
            tone=parsed_tone,
            custom_tag=custom_tag,
            location_id=location_id,
            participant_id=participant_id,
        )

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "filters": {
                    "scene_type": scene_type,
                    "tone": tone,
                    "custom_tag": custom_tag,
                    "location_id": location_id,
                    "participant_id": participant_id,
                },
                "count": len(scenes),
                "scenes": [
                    {
                        "id": s.scene.id,
                        "chapter_number": s.chapter_number,
                        "scene_number": s.scene.scene_number,
                        "excerpt": s.excerpt,
                        "tags": {
                            "scene_type": s.tags.scene_type.value if s.tags and s.tags.scene_type else None,
                            "tone": s.tags.tone.value if s.tags and s.tags.tone else None,
                        } if s.tags else None,
                    }
                    for s in scenes
                ],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error filtering scenes: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/document-types", response_model=ApiResponse)
async def get_document_types():
    """
    Lista todos los tipos de documento disponibles.

    Returns:
        ApiResponse con lista de tipos y sus subtipos
    """
    try:
        from narrative_assistant.feature_profile import FeatureProfileService

        service = FeatureProfileService()
        types = service.get_document_types()

        return ApiResponse(success=True, data=types)
    except Exception as e:
        logger.error(f"Error getting document types: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/document-type", response_model=ApiResponse)
async def get_project_document_type(project_id: int):
    """
    Obtiene el tipo de documento actual de un proyecto.

    Returns:
        ApiResponse con tipo, subtipo, confirmación y detección
    """
    try:
        from narrative_assistant.feature_profile import FeatureProfileService

        service = FeatureProfileService()
        doc_type = service.get_project_document_type(project_id)

        if not doc_type:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        return ApiResponse(success=True, data=doc_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document type for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.put("/api/projects/{project_id}/document-type", response_model=ApiResponse)
async def set_project_document_type(
    project_id: int,
    document_type: str = Body(..., embed=True),
    document_subtype: Optional[str] = Body(None, embed=True),
):
    """
    Establece el tipo de documento de un proyecto.

    Args:
        project_id: ID del proyecto
        document_type: Código del tipo (FIC, MEM, etc.)
        document_subtype: Código del subtipo (opcional)

    Returns:
        ApiResponse con el perfil actualizado
    """
    try:
        from narrative_assistant.feature_profile import FeatureProfileService

        service = FeatureProfileService()
        success = service.set_project_document_type(
            project_id=project_id,
            document_type=document_type,
            document_subtype=document_subtype,
            confirmed=True,
        )

        if not success:
            return ApiResponse(
                success=False,
                error=f"Tipo de documento inválido: {document_type}"
            )

        # Retornar el perfil actualizado
        doc_type = service.get_project_document_type(project_id)
        profile = service.get_project_profile(project_id)

        return ApiResponse(
            success=True,
            data={
                "document_type": doc_type,
                "feature_profile": profile.to_dict() if profile else None,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting document type for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/feature-profile", response_model=ApiResponse)
async def get_project_feature_profile(project_id: int):
    """
    Obtiene el perfil de features para un proyecto.

    Retorna qué features están habilitadas, opcionales o deshabilitadas
    según el tipo de documento del proyecto.

    Returns:
        ApiResponse con el perfil de features
    """
    try:
        from narrative_assistant.feature_profile import FeatureProfileService

        service = FeatureProfileService()
        profile = service.get_project_profile(project_id)

        if not profile:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        return ApiResponse(success=True, data=profile.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feature profile for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/feature-availability/{feature}", response_model=ApiResponse)
async def get_feature_availability(project_id: int, feature: str):
    """
    Comprueba la disponibilidad de una feature específica.

    Args:
        project_id: ID del proyecto
        feature: Nombre de la feature (characters, timeline, scenes, etc.)

    Returns:
        ApiResponse con el nivel de disponibilidad (enabled, optional, disabled)
    """
    try:
        from narrative_assistant.feature_profile import FeatureProfileService

        service = FeatureProfileService()
        availability = service.get_feature_availability(project_id, feature)

        return ApiResponse(
            success=True,
            data={
                "feature": feature,
                "availability": availability,
                "is_enabled": availability == "enabled",
                "is_available": availability in ("enabled", "optional"),
            }
        )
    except Exception as e:
        logger.error(f"Error checking feature availability: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.post("/api/projects/{project_id}/detect-document-type", response_model=ApiResponse)
async def detect_document_type(project_id: int):
    """
    Detecta automáticamente el tipo de documento basándose en el contenido.

    No cambia el tipo actual, solo registra la sugerencia.

    Returns:
        ApiResponse con el tipo detectado y si hay discrepancia
    """
    try:
        from narrative_assistant.feature_profile import FeatureProfileService

        service = FeatureProfileService()

        # Detectar tipo
        detected = service.detect_document_type(project_id)
        if not detected:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Guardar detección
        service.set_detected_document_type(project_id, detected)

        # Obtener información actual para comparar
        current = service.get_project_document_type(project_id)

        return ApiResponse(
            success=True,
            data={
                "detected_type": detected,
                "detected_type_info": service.get_document_type_info(detected),
                "current_type": current["type"] if current else None,
                "has_mismatch": current and current["type"] != detected,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting document type: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/correction-config/types", response_model=ApiResponse)
async def get_correction_types():
    """
    Lista todos los tipos de documento con sus subtipos.

    Formato optimizado para el selector de dos columnas del frontend.

    Returns:
        ApiResponse con lista de tipos, cada uno con sus subtipos anidados
    """
    try:
        from narrative_assistant.correction_config import get_types_with_subtypes

        types = get_types_with_subtypes()
        return ApiResponse(success=True, data=types)
    except Exception as e:
        logger.error(f"Error getting correction types: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/correction-config/{type_code}", response_model=ApiResponse)
async def get_correction_config_for_type(
    type_code: str,
    subtype_code: Optional[str] = Query(None, description="Código del subtipo")
):
    """
    Obtiene la configuración de corrección para un tipo/subtipo.

    Aplica herencia: tipo → subtipo.

    Args:
        type_code: Código del tipo (FIC, MEM, INF, etc.)
        subtype_code: Código del subtipo opcional (INF_MID, FIC_LIT, etc.)

    Returns:
        ApiResponse con la configuración completa con información de herencia
    """
    try:
        from narrative_assistant.correction_config import get_config_for_project

        config = get_config_for_project(type_code, subtype_code)
        return ApiResponse(success=True, data=config)
    except Exception as e:
        logger.error(f"Error getting correction config: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/correction-config", response_model=ApiResponse)
async def get_project_correction_config(project_id: int):
    """
    Obtiene la configuración de corrección para un proyecto.

    Usa el tipo y subtipo del proyecto para calcular la configuración
    con herencia aplicada.

    Returns:
        ApiResponse con la configuración efectiva del proyecto
    """
    try:
        from narrative_assistant.correction_config import get_config_for_project

        # Usar el deps.project_manager global en lugar de crear nueva instancia
        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        project = result.value

        # Obtener tipo y subtipo del proyecto
        type_code = getattr(project, 'document_type', 'FIC') or 'FIC'
        subtype_code = getattr(project, 'document_subtype', None)

        # Cargar customizations del proyecto si existen
        customizations = project.settings.get("correction_customizations")

        # Obtener configuración con herencia aplicada + customizations
        config = get_config_for_project(type_code, subtype_code, customizations)

        return ApiResponse(success=True, data=config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project correction config: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/correction-config/{type_code}/diff", response_model=ApiResponse)
async def get_correction_config_diff(
    type_code: str,
    subtype_code: Optional[str] = Query(None, description="Código del subtipo")
):
    """
    Obtiene las diferencias entre la configuración del tipo y subtipo.

    Útil para mostrar en la UI qué parámetros han sido sobrescritos.

    Returns:
        ApiResponse con parámetros sobrescritos y sus valores
    """
    try:
        from narrative_assistant.correction_config import get_config_diff

        diff = get_config_diff(type_code, subtype_code)
        return ApiResponse(success=True, data=diff)
    except Exception as e:
        logger.error(f"Error getting config diff: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/correction-config/defaults", response_model=ApiResponse)
async def get_all_default_overrides():
    """
    Lista todos los overrides de configuración definidos por el usuario.

    Estos son los cambios que el usuario ha hecho a los defaults de tipos/subtipos.
    """
    try:
        from narrative_assistant.correction_config.defaults_repository import get_defaults_repository

        repo = get_defaults_repository()
        overrides = repo.get_all_overrides()

        return ApiResponse(success=True, data={
            "overrides": overrides,
            "count": len(overrides)
        })
    except Exception as e:
        logger.error(f"Error getting default overrides: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/correction-config/defaults/{type_code}", response_model=ApiResponse)
async def get_type_default_override(
    type_code: str,
    subtype_code: Optional[str] = Query(None, description="Código del subtipo")
):
    """
    Obtiene el override de configuración para un tipo o subtipo específico.

    Args:
        type_code: Código del tipo (FIC, MEM, INF, etc.)
        subtype_code: Código del subtipo (opcional)

    Returns:
        ApiResponse con el override y la configuración efectiva
    """
    try:
        from narrative_assistant.correction_config.defaults_repository import get_defaults_repository
        from narrative_assistant.correction_config import get_correction_config, TYPES_REGISTRY, SUBTYPES_REGISTRY

        repo = get_defaults_repository()
        override = repo.get_override(type_code, subtype_code)

        # Obtener nombres del tipo y subtipo
        type_info = TYPES_REGISTRY.get(type_code.upper(), {})
        type_name = type_info.get("name", type_code)
        subtype_name = None
        if subtype_code:
            subtype_info = SUBTYPES_REGISTRY.get(subtype_code.upper(), {})
            subtype_name = subtype_info.get("name", subtype_code)

        # Obtener también la configuración efectiva para preview
        config = get_correction_config(type_code, subtype_code)

        return ApiResponse(success=True, data={
            "type_code": type_code,
            "type_name": type_name,
            "subtype_code": subtype_code,
            "subtype_name": subtype_name,
            "override": override,
            "effective_config": config.to_dict()
        })
    except Exception as e:
        logger.error(f"Error getting default override: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.put("/api/correction-config/defaults/{type_code}", response_model=ApiResponse)
async def set_type_default_override(
    type_code: str,
    request: DefaultOverrideRequest,
    subtype_code: Optional[str] = Query(None, description="Código del subtipo")
):
    """
    Crea o actualiza el override de configuración para un tipo o subtipo.

    Args:
        type_code: Código del tipo
        subtype_code: Código del subtipo (opcional, query param)
        request: Body con los overrides a aplicar

    Returns:
        ApiResponse con el resultado y la configuración efectiva actualizada
    """
    try:
        from narrative_assistant.correction_config.defaults_repository import get_defaults_repository
        from narrative_assistant.correction_config import get_correction_config

        repo = get_defaults_repository()
        success = repo.set_override(type_code, subtype_code, request.overrides)

        if success:
            # Obtener configuración actualizada
            config = get_correction_config(type_code, subtype_code)
            return ApiResponse(success=True, data={
                "type_code": type_code,
                "subtype_code": subtype_code,
                "overrides": request.overrides,
                "effective_config": config.to_dict()
            })
        else:
            return ApiResponse(success=False, error="Error al guardar override")
    except Exception as e:
        logger.error(f"Error setting default override: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.delete("/api/correction-config/defaults/{type_code}", response_model=ApiResponse)
async def delete_type_default_override(
    type_code: str,
    subtype_code: Optional[str] = Query(None, description="Código del subtipo")
):
    """
    Elimina el override de un tipo/subtipo (reset a hardcoded defaults).

    Args:
        type_code: Código del tipo
        subtype_code: Código del subtipo (opcional)
    """
    try:
        from narrative_assistant.correction_config.defaults_repository import get_defaults_repository
        from narrative_assistant.correction_config import get_correction_config

        repo = get_defaults_repository()
        deleted = repo.delete_override(type_code, subtype_code)

        # Obtener configuración después del reset
        config = get_correction_config(type_code, subtype_code)

        return ApiResponse(success=True, data={
            "deleted": deleted,
            "type_code": type_code,
            "subtype_code": subtype_code,
            "effective_config": config.to_dict()
        })
    except Exception as e:
        logger.error(f"Error deleting default override: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.delete("/api/correction-config/defaults", response_model=ApiResponse)
async def delete_all_default_overrides():
    """
    Elimina TODOS los overrides de configuración (full reset).

    Restaura todos los tipos y subtipos a sus valores hardcoded originales.
    """
    try:
        from narrative_assistant.correction_config.defaults_repository import get_defaults_repository

        repo = get_defaults_repository()
        count = repo.delete_all_overrides()

        return ApiResponse(success=True, data={
            "deleted_count": count,
            "message": f"Se eliminaron {count} overrides. Configuración restaurada."
        })
    except Exception as e:
        logger.error(f"Error deleting all default overrides: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/correction-config/defaults/status", response_model=ApiResponse)
async def get_defaults_status():
    """
    Obtiene el estado de customización de todos los tipos.

    Útil para mostrar badges en la UI indicando qué tipos tienen modificaciones.
    """
    try:
        from narrative_assistant.correction_config.defaults_repository import get_defaults_repository
        from narrative_assistant.correction_config import TYPES_REGISTRY

        repo = get_defaults_repository()
        all_overrides = repo.get_all_overrides()

        # Agrupar por tipo
        status = {}
        for type_code in TYPES_REGISTRY.keys():
            type_overrides = [o for o in all_overrides if o["type_code"] == type_code]
            has_type_override = any(o["subtype_code"] is None for o in type_overrides)
            subtype_overrides = [o["subtype_code"] for o in type_overrides if o["subtype_code"]]

            status[type_code] = {
                "has_type_override": has_type_override,
                "subtype_overrides": subtype_overrides,
                "total_overrides": len(type_overrides)
            }

        return ApiResponse(success=True, data={
            "status": status,
            "total_overrides": len(all_overrides)
        })
    except Exception as e:
        logger.error(f"Error getting defaults status: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


