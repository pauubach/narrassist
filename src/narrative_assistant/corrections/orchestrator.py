"""
Orquestador de detectores de correcciones.

Coordina la ejecución de todos los detectores habilitados y
agrupa los resultados para presentar al corrector.
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import CorrectionIssue
from .config import CorrectionConfig
from .detectors import (
    AcronymDetector,
    AgreementDetector,
    AnacolutoDetector,
    AnglicismsDetector,
    ClarityDetector,
    CoherenceDetector,
    CrutchWordsDetector,
    GlossaryDetector,
    GrammarDetector,
    OrthographicVariantsDetector,
    POVDetector,
    ReferencesDetector,
    RegionalDetector,
    RepetitionDetector,
    ScientificStructureDetector,
    StyleRegisterDetector,
    TerminologyDetector,
    TypographyDetector,
)
from .detectors.field_terminology import FieldTerminologyDetector
from .types import CorrectionCategory

logger = logging.getLogger(__name__)


class CorrectionOrchestrator:
    """
    Orquesta la ejecución de detectores de correcciones.

    Ejecuta detectores en paralelo cuando es posible y agrupa
    los resultados por categoría.
    """

    def __init__(
        self,
        config: CorrectionConfig | None = None,
        max_workers: int = 3,
        embeddings_model=None,
    ):
        """
        Inicializa el orquestador.

        Args:
            config: Configuración de correcciones
            max_workers: Número máximo de workers paralelos
            embeddings_model: Modelo de embeddings para detección semántica
        """
        self.config = config or CorrectionConfig.default()
        self.max_workers = max_workers
        self._embeddings_model = embeddings_model

        # Inicializar detectores básicos
        self._detectors = {
            CorrectionCategory.TYPOGRAPHY: TypographyDetector(self.config.typography),
            CorrectionCategory.REPETITION: RepetitionDetector(self.config.repetition),
            CorrectionCategory.AGREEMENT: AgreementDetector(self.config.agreement),
            CorrectionCategory.REGIONAL: RegionalDetector(self.config.regional),
            CorrectionCategory.CLARITY: ClarityDetector(self.config.clarity),
            CorrectionCategory.GRAMMAR: GrammarDetector(self.config.grammar),
            CorrectionCategory.ANGLICISMS: AnglicismsDetector(self.config.anglicisms),
            CorrectionCategory.CRUTCH_WORDS: CrutchWordsDetector(self.config.crutch_words),
            CorrectionCategory.ANACOLUTO: AnacolutoDetector(self.config.anacoluto),
            CorrectionCategory.POV: POVDetector(self.config.pov),
            CorrectionCategory.STYLE_REGISTER: StyleRegisterDetector(self.config.style_register),
            CorrectionCategory.ORTHOGRAPHY: OrthographicVariantsDetector(
                self.config.orthographic_variants
            ),
            CorrectionCategory.REFERENCES: ReferencesDetector(self.config.references),
            CorrectionCategory.ACRONYMS: AcronymDetector(self.config.acronyms),
            CorrectionCategory.STRUCTURE: ScientificStructureDetector(self.config.structure),
            CorrectionCategory.COHERENCE: CoherenceDetector(self.config.coherence),
        }

        # Detectores que usan embeddings (inicializados bajo demanda)
        self._terminology_detector = None
        self._field_detector = None
        self._glossary_detector = None

    def analyze(
        self,
        text: str,
        chapter_index: int | None = None,
        spacy_doc=None,
        project_id: int | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> list[CorrectionIssue]:
        """
        Ejecuta todos los detectores habilitados.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo (opcional)
            spacy_doc: Documento spaCy preprocesado (opcional)
            project_id: ID del proyecto (necesario para glosario)
            progress_callback: Callback para reportar progreso

        Returns:
            Lista de CorrectionIssue encontrados
        """
        all_issues: list[CorrectionIssue] = []
        failed_detectors: list[str] = []

        # Separar detectores en 3 buckets: regex (parallel), LLM (sequential), spaCy (sequential)
        parallel_detectors = []
        llm_detectors = []
        sequential_detectors = []

        for category, detector in self._detectors.items():
            if not self._is_enabled(category):
                continue

            if detector.requires_spacy and spacy_doc is None:
                logger.debug(f"Saltando {category.value}: requiere spaCy")
                continue

            if detector.requires_llm:
                llm_detectors.append((category, detector))
            elif detector.requires_spacy:
                sequential_detectors.append((category, detector))
            else:
                parallel_detectors.append((category, detector))

        # Ejecutar detectores paralelos (tipografía, regional)
        if parallel_detectors:
            if progress_callback:
                progress_callback("Analizando tipografía y vocabulario...")

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        self._run_detector,
                        detector,
                        text,
                        chapter_index,
                        None,  # Sin spaCy
                    ): category
                    for category, detector in parallel_detectors
                }

                for future in as_completed(futures):
                    category = futures[future]
                    try:
                        issues = future.result()
                        all_issues.extend(self._limit_issues(issues, category))
                    except Exception as e:
                        logger.error(f"Error en detector {category.value}: {e}")
                        failed_detectors.append(category.value)

        # Ejecutar detectores LLM (secuenciales, skip si LLM no disponible)
        for category, detector in llm_detectors:
            if progress_callback:
                progress_callback(f"Analizando {self._category_name(category)} con LLM...")

            try:
                issues = self._run_detector(detector, text, chapter_index, None)
                all_issues.extend(self._limit_issues(issues, category))
            except Exception as e:
                logger.error(f"Error en detector LLM {category.value}: {e}")
                failed_detectors.append(category.value)

        # Ejecutar detectores secuenciales (requieren spaCy)
        for category, detector in sequential_detectors:
            if progress_callback:
                progress_callback(f"Analizando {self._category_name(category)}...")

            try:
                issues = self._run_detector(detector, text, chapter_index, spacy_doc)
                all_issues.extend(self._limit_issues(issues, category))
            except Exception as e:
                logger.error(f"Error en detector {category.value}: {e}")
                failed_detectors.append(category.value)

        # Ejecutar detector de terminología (usa embeddings opcionalmente)
        if self.config.terminology.enabled:
            if progress_callback:
                progress_callback("Analizando terminología...")

            try:
                terminology_issues = self._run_terminology_detector(text, chapter_index, spacy_doc)
                all_issues.extend(
                    self._limit_issues(terminology_issues, CorrectionCategory.TERMINOLOGY)
                )
            except Exception as e:
                logger.error(f"Error en detector de terminología: {e}")
                failed_detectors.append("terminology")

        # Ejecutar detector de campo especializado
        if self.config.field_dictionary.enabled:
            if progress_callback:
                progress_callback("Analizando terminología especializada...")

            try:
                field_issues = self._run_field_detector(text, chapter_index, spacy_doc)
                all_issues.extend(self._limit_issues(field_issues, CorrectionCategory.TERMINOLOGY))
            except Exception as e:
                logger.error(f"Error en detector de campo: {e}")
                failed_detectors.append("field_dictionary")

        # Ejecutar detector de glosario (requiere project_id)
        if self.config.glossary.enabled and project_id is not None:
            if progress_callback:
                progress_callback("Verificando glosario del proyecto...")

            try:
                glossary_issues = self._run_glossary_detector(text, chapter_index, project_id)
                all_issues.extend(self._limit_issues(glossary_issues, CorrectionCategory.GLOSSARY))
            except Exception as e:
                logger.error(f"Error en detector de glosario: {e}")
                failed_detectors.append("glossary")

        # Ordenar por posición en el texto
        all_issues.sort(key=lambda x: x.start_char)

        if failed_detectors:
            logger.warning(f"Detectores con error: {', '.join(failed_detectors)}")

        logger.info(f"Análisis de correcciones completado: {len(all_issues)} sugerencias")

        return all_issues

    def _run_terminology_detector(
        self,
        text: str,
        chapter_index: int | None,
        spacy_doc,
    ) -> list[CorrectionIssue]:
        """Ejecuta el detector de terminología."""
        if self._terminology_detector is None:
            self._terminology_detector = TerminologyDetector(config=self.config.terminology)  # type: ignore[assignment]

        return self._terminology_detector.detect(  # type: ignore[no-any-return, attr-defined]
            text,
            chapter_index,
            spacy_doc=spacy_doc,
            embeddings_model=self._embeddings_model,
        )

    def _run_field_detector(
        self,
        text: str,
        chapter_index: int | None,
        spacy_doc,
    ) -> list[CorrectionIssue]:
        """Ejecuta el detector de terminología de campo."""
        if self._field_detector is None:
            self._field_detector = FieldTerminologyDetector(  # type: ignore[assignment]
                config=self.config.field_dictionary,
                profile=self.config.profile,
            )

        return self._field_detector.detect(  # type: ignore[no-any-return, attr-defined]
            text,
            chapter_index,
            spacy_doc=spacy_doc,
        )

    def _run_glossary_detector(
        self,
        text: str,
        chapter_index: int | None,
        project_id: int,
    ) -> list[CorrectionIssue]:
        """Ejecuta el detector de glosario."""
        if self._glossary_detector is None:
            self._glossary_detector = GlossaryDetector(  # type: ignore[assignment]
                config=self.config.glossary,
            )

        return self._glossary_detector.detect(  # type: ignore[no-any-return, attr-defined]
            text,
            chapter_index,
            project_id=project_id,
        )

    def clear_glossary_cache(self, project_id: int | None = None) -> None:
        """Limpia el caché del glosario (llamar tras modificar entradas)."""
        if self._glossary_detector:
            self._glossary_detector.clear_cache(project_id)

    def analyze_by_chapters(
        self,
        chapters: list[dict],
        spacy_docs: list | None = None,
        project_id: int | None = None,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> dict[int, list[CorrectionIssue]]:
        """
        Analiza correcciones por capítulo.

        Args:
            chapters: Lista de capítulos con {index, title, content}
            spacy_docs: Documentos spaCy preprocesados por capítulo
            project_id: ID del proyecto (necesario para glosario)
            progress_callback: Callback(mensaje, capítulo_actual, total)

        Returns:
            Diccionario {chapter_index: [issues]}
        """
        results = {}

        for i, chapter in enumerate(chapters):
            if progress_callback:
                progress_callback(
                    f"Buscando correcciones en {chapter.get('title', f'Capítulo {i}')}",
                    i + 1,
                    len(chapters),
                )

            spacy_doc = spacy_docs[i] if spacy_docs and i < len(spacy_docs) else None

            issues = self.analyze(
                text=chapter.get("content", ""),
                chapter_index=chapter.get("index", i),
                spacy_doc=spacy_doc,
                project_id=project_id,
            )

            results[chapter.get("index", i)] = issues

        return results

    def _run_detector(
        self,
        detector,
        text: str,
        chapter_index: int | None,
        spacy_doc,
    ) -> list[CorrectionIssue]:
        """Ejecuta un detector individual."""
        if detector.requires_spacy:
            return detector.detect(text, chapter_index, spacy_doc=spacy_doc)  # type: ignore[no-any-return]
        else:
            return detector.detect(text, chapter_index)  # type: ignore[no-any-return]

    def _is_enabled(self, category: CorrectionCategory) -> bool:
        """Verifica si una categoría está habilitada."""
        if category == CorrectionCategory.TYPOGRAPHY:
            return self.config.typography.enabled
        elif category == CorrectionCategory.REPETITION:
            return self.config.repetition.enabled
        elif category == CorrectionCategory.AGREEMENT:
            return self.config.agreement.enabled
        elif category == CorrectionCategory.REGIONAL:
            return self.config.regional.enabled
        elif category == CorrectionCategory.TERMINOLOGY:
            return self.config.terminology.enabled
        elif category == CorrectionCategory.CLARITY:
            return self.config.clarity.enabled
        elif category == CorrectionCategory.GRAMMAR:
            return self.config.grammar.enabled
        elif category == CorrectionCategory.ANGLICISMS:
            return self.config.anglicisms.enabled
        elif category == CorrectionCategory.CRUTCH_WORDS:
            return self.config.crutch_words.enabled
        elif category == CorrectionCategory.GLOSSARY:
            return self.config.glossary.enabled
        elif category == CorrectionCategory.ANACOLUTO:
            return self.config.anacoluto.enabled
        elif category == CorrectionCategory.POV:
            return self.config.pov.enabled
        elif category == CorrectionCategory.ORTHOGRAPHY:
            return self.config.orthographic_variants.enabled
        elif category == CorrectionCategory.STYLE_REGISTER:
            return self.config.style_register.enabled
        elif category == CorrectionCategory.REFERENCES:
            return self.config.references.enabled
        elif category == CorrectionCategory.ACRONYMS:
            return self.config.acronyms.enabled
        elif category == CorrectionCategory.STRUCTURE:
            return self.config.structure.enabled
        elif category == CorrectionCategory.COHERENCE:
            return self.config.coherence.enabled
        return False

    def _limit_issues(
        self, issues: list[CorrectionIssue], category: CorrectionCategory
    ) -> list[CorrectionIssue]:
        """Limita el número de issues por categoría."""
        max_issues = self.config.max_issues_per_category
        if len(issues) > max_issues:
            logger.warning(
                f"Demasiadas sugerencias en {category.value}: "
                f"{len(issues)} -> limitando a {max_issues}"
            )
            return issues[:max_issues]
        return issues

    def _category_name(self, category: CorrectionCategory) -> str:
        """Nombre legible de la categoría."""
        return {
            CorrectionCategory.TYPOGRAPHY: "tipografía",
            CorrectionCategory.REPETITION: "repeticiones",
            CorrectionCategory.AGREEMENT: "concordancia",
            CorrectionCategory.REGIONAL: "vocabulario regional",
            CorrectionCategory.TERMINOLOGY: "terminología",
            CorrectionCategory.CLARITY: "claridad",
            CorrectionCategory.GRAMMAR: "gramática",
            CorrectionCategory.ANGLICISMS: "anglicismos",
            CorrectionCategory.CRUTCH_WORDS: "muletillas",
            CorrectionCategory.GLOSSARY: "glosario",
            CorrectionCategory.ANACOLUTO: "anacolutos",
            CorrectionCategory.POV: "punto de vista",
            CorrectionCategory.ORTHOGRAPHY: "variantes ortográficas",
            CorrectionCategory.STYLE_REGISTER: "estilo de registro",
            CorrectionCategory.REFERENCES: "referencias bibliográficas",
            CorrectionCategory.ACRONYMS: "siglas y abreviaturas",
            CorrectionCategory.STRUCTURE: "estructura del documento",
            CorrectionCategory.COHERENCE: "coherencia editorial",
        }.get(category, category.value)

    def get_summary(self, issues: list[CorrectionIssue]) -> dict:
        """
        Genera resumen de issues por categoría.

        Args:
            issues: Lista de issues

        Returns:
            Diccionario con conteos por categoría y tipo
        """
        summary = {
            "total": len(issues),
            "by_category": {},
            "by_type": {},
            "by_confidence": {
                "high": 0,  # >= 0.8
                "medium": 0,  # >= 0.6
                "low": 0,  # < 0.6
            },
        }

        for issue in issues:
            # Por categoría
            cat = issue.category
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1  # type: ignore[index, attr-defined]

            # Por tipo
            itype = issue.issue_type
            summary["by_type"][itype] = summary["by_type"].get(itype, 0) + 1  # type: ignore[index, attr-defined]

            # Por confianza
            if issue.confidence >= 0.8:
                summary["by_confidence"]["high"] += 1  # type: ignore[index]
            elif issue.confidence >= 0.6:
                summary["by_confidence"]["medium"] += 1  # type: ignore[index]
            else:
                summary["by_confidence"]["low"] += 1  # type: ignore[index]

        return summary
