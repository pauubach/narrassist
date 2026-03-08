"""Subfases de gramática y correcciones editoriales extraídas de `_analysis_phases`."""

from __future__ import annotations

from typing import Any, Callable


def run_grammar_phase(
    ctx: dict[str, Any],
    tracker: Any,
    *,
    logger: Any,
    to_optional_int: Callable[[Any], int | None],
    find_chapter_number_for_position: Callable[[list[dict[str, Any]], int | None], int | None],
) -> None:
    """Ejecuta la fase de gramática/ortografía y persiste resultados en `ctx`."""
    project = ctx["project"]
    full_text = ctx["full_text"]
    chapters_data = ctx.get("chapters_data", [])
    entities = ctx.get("entities", [])
    analysis_config = ctx.get("analysis_config")
    selected_nlp_methods = ctx.get("selected_nlp_methods", {})

    grammar_methods: list[str] | None = None
    spelling_methods: list[str] | None = None
    if isinstance(selected_nlp_methods, dict):
        raw_grammar_methods = selected_nlp_methods.get("grammar")
        raw_spelling_methods = selected_nlp_methods.get("spelling")
        if isinstance(raw_grammar_methods, list):
            grammar_methods = [m for m in raw_grammar_methods if isinstance(m, str)]
        if isinstance(raw_spelling_methods, list):
            spelling_methods = [m for m in raw_spelling_methods if isinstance(m, str)]

    run_grammar_checks = not analysis_config or bool(getattr(analysis_config, "run_grammar", True))
    run_spelling_checks = not analysis_config or bool(getattr(analysis_config, "run_spelling", True))
    if grammar_methods is not None and len(grammar_methods) == 0:
        run_grammar_checks = False
    if spelling_methods is not None and len(spelling_methods) == 0:
        run_spelling_checks = False

    tracker.start_phase("grammar", "Revisando la redacción...")

    grammar_issues = []
    spelling_issues = []
    if run_grammar_checks:
        try:
            from narrative_assistant.nlp.grammar import (
                ensure_languagetool_running,
                get_grammar_checker,
                is_languagetool_installed,
            )

            use_languagetool = True
            use_llm = None
            if grammar_methods is not None:
                method_set = {m.strip() for m in grammar_methods}
                use_languagetool = "languagetool" in method_set
                use_llm = "llm" in method_set
                logger.info(
                    "Grammar methods requested from settings: %s (languagetool=%s, llm=%s)",
                    sorted(method_set),
                    use_languagetool,
                    use_llm,
                )

            if use_languagetool and is_languagetool_installed():
                lt_started = ensure_languagetool_running()
                if lt_started:
                    logger.info("LanguageTool server started successfully")

            grammar_checker = get_grammar_checker()

            if use_languagetool and not grammar_checker.languagetool_available:
                grammar_checker.reload_languagetool()
                if grammar_checker.languagetool_available:
                    logger.info("LanguageTool now available after reload")

            grammar_result = grammar_checker.check(
                full_text,
                use_languagetool=use_languagetool,
                use_llm=use_llm,
            )

            if grammar_result.is_success:
                grammar_report = grammar_result.value
                grammar_issues = grammar_report.issues  # type: ignore[union-attr]
                logger.info(f"Grammar check found {len(grammar_issues)} issues")
            else:
                logger.warning(f"Grammar check failed: {grammar_result.error}")

        except ImportError as e:
            logger.warning(f"Grammar module not available: {e}")
        except Exception as e:
            logger.warning(f"Error in grammar analysis: {e}")
    else:
        logger.info("Grammar checks omitted by project settings")

    class _SkipSpellingChecks(Exception):
        pass

    correction_issues = []
    try:
        if not run_spelling_checks:
            raise _SkipSpellingChecks()

        from narrative_assistant.corrections import CorrectionConfig
        from narrative_assistant.corrections.base import CorrectionIssue
        from narrative_assistant.corrections.orchestrator import CorrectionOrchestrator
        from narrative_assistant.nlp.orthography.voting_checker import VotingSpellingChecker

        if spelling_methods is not None:
            logger.info(
                "Spelling methods requested from settings: %s",
                sorted({m.strip() for m in spelling_methods}),
            )

        spelling_correction_issues: list[CorrectionIssue] = []
        try:
            selected_spelling = {m.strip() for m in (spelling_methods or []) if m.strip()}
            use_all_spelling_methods = len(selected_spelling) == 0

            base_voters = {"patterns", "symspell", "hunspell", "pyspellchecker", "languagetool", "beto"}
            if not use_all_spelling_methods and not (selected_spelling & base_voters):
                logger.warning(
                    "Spelling methods selected without base voter (%s): omitiendo corrector ortográfico",
                    sorted(selected_spelling),
                )
            else:
                spelling_checker = VotingSpellingChecker(
                    use_patterns=use_all_spelling_methods or "patterns" in selected_spelling,
                    use_hunspell=use_all_spelling_methods or "hunspell" in selected_spelling,
                    use_symspell=use_all_spelling_methods or "symspell" in selected_spelling,
                    use_pyspellchecker=use_all_spelling_methods or "pyspellchecker" in selected_spelling,
                    use_beto=use_all_spelling_methods or "beto" in selected_spelling,
                    use_languagetool=use_all_spelling_methods or "languagetool" in selected_spelling,
                    use_llm_arbitration=(
                        use_all_spelling_methods or "llm_arbitrator" in selected_spelling
                    ),
                )

                known_entities: list[str] = []
                if isinstance(entities, list):
                    for entity in entities:
                        canonical_name = getattr(entity, "canonical_name", None)
                        if isinstance(canonical_name, str) and canonical_name.strip():
                            known_entities.append(canonical_name.strip())
                        aliases = getattr(entity, "aliases", None)
                        if isinstance(aliases, list):
                            for alias in aliases:
                                if isinstance(alias, str) and alias.strip():
                                    known_entities.append(alias.strip())

                spelling_result = spelling_checker.check(
                    full_text,
                    known_entities=known_entities,
                )
                if spelling_result.is_success:
                    spelling_report = spelling_result.value
                    spelling_issues = spelling_report.issues  # type: ignore[union-attr]

                    for issue in spelling_issues:
                        start_char = to_optional_int(getattr(issue, "start_char", None))
                        end_char = to_optional_int(getattr(issue, "end_char", None))
                        if start_char is None or end_char is None:
                            continue

                        suggestion = getattr(issue, "best_suggestion", None)
                        if not suggestion:
                            issue_suggestions = getattr(issue, "suggestions", None)
                            if isinstance(issue_suggestions, list) and issue_suggestions:
                                suggestion = issue_suggestions[0]

                        chapter_index = to_optional_int(getattr(issue, "chapter", None))
                        if chapter_index is None:
                            chapter_index = find_chapter_number_for_position(
                                chapters_data,
                                start_char,
                            )

                        spelling_correction_issues.append(
                            CorrectionIssue(
                                category="orthography",
                                issue_type=f"spelling_{getattr(getattr(issue, 'error_type', None), 'value', 'misspelling')}",
                                start_char=start_char,
                                end_char=end_char,
                                text=str(getattr(issue, "word", "")),
                                explanation=str(
                                    getattr(issue, "explanation", "")
                                    or "Posible error ortográfico detectado por consenso."
                                ),
                                suggestion=str(suggestion) if suggestion else None,
                                confidence=float(getattr(issue, "confidence", 0.5)),
                                context=str(getattr(issue, "sentence", "")),
                                chapter_index=chapter_index,
                                rule_id="spelling_voting",
                                extra_data={
                                    "source": "spelling_voting",
                                    "severity": getattr(getattr(issue, "severity", None), "value", "warning"),
                                },
                            )
                        )
                else:
                    logger.warning("Spelling voting check failed: %s", spelling_result.error)
        except ImportError as spelling_import_err:
            logger.warning("Spelling voting checker unavailable: %s", spelling_import_err)
        except Exception as spelling_err:
            logger.warning("Error in spelling voting check: %s", spelling_err)

        correction_config = CorrectionConfig.default()
        try:
            project_settings = project.settings or {}
            cc = project_settings.get("correction_customizations") or project_settings.get(
                "correction_config", {}
            )
            dialog_cfg = cc.get("dialog", {})
            dash_val = dialog_cfg.get("spoken_dialogue_dash", "")
            dash_map = {"em_dash": "em", "en_dash": "en", "hyphen": "hyphen"}
            if dash_val in dash_map:
                correction_config.typography.dialogue_dash = dash_map[dash_val]  # type: ignore[assignment]
            quote_val = dialog_cfg.get("nested_dialogue_quote", "")
            quote_map = {"angular": "angular", "double": "curly", "single": "straight"}
            if quote_val in quote_map:
                correction_config.typography.quote_style = quote_map[quote_val]  # type: ignore[assignment]
            logger.info(
                "Correction config loaded: dialogue_dash=%s, quote_style=%s",
                correction_config.typography.dialogue_dash,
                correction_config.typography.quote_style,
            )
        except Exception as cfg_err:
            logger.debug(f"Could not load project correction config: {cfg_err}")

        style_profiles = {
            "TEC": ("strict", True),
            "ENS": ("formal", True),
            "DIV": ("strict", True),
            "MEM": ("moderate", True),
            "AUT": ("moderate", True),
            "BIO": ("moderate", True),
            "CEL": ("moderate", True),
            "PRA": ("moderate", True),
            "FIC": ("free", False),
            "DRA": ("free", False),
            "INF": ("free", False),
            "GRA": ("free", False),
        }
        doc_type_code = ctx.get("document_type", "FIC")
        profile, enabled = style_profiles.get(doc_type_code, ("moderate", False))
        from narrative_assistant.corrections.config import (
            AcronymConfig,
            CoherenceConfig,
            ReferencesConfig,
            StructureConfig,
            StyleRegisterConfig,
        )

        correction_config.style_register = StyleRegisterConfig(enabled=enabled, profile=profile)

        scientific_detectors: dict[str, tuple[str, bool]] = {
            "TEC": ("scientific", True),
            "ENS": ("essay", True),
            "DIV": ("essay", False),
        }
        sci_config = scientific_detectors.get(doc_type_code)
        if sci_config:
            structure_profile, coherence_use_llm = sci_config
            correction_config.references = ReferencesConfig(enabled=True)
            correction_config.acronyms = AcronymConfig(enabled=True)
            correction_config.structure = StructureConfig(enabled=True, profile=structure_profile)
            correction_config.coherence = CoherenceConfig(enabled=True, use_llm=coherence_use_llm)

        orchestrator = CorrectionOrchestrator(config=correction_config)
        total_chapters = len(chapters_data)

        def corrections_progress_callback(message: str, current: int, total: int):
            tracker.update_storage(
                current_action=f"Revisando capítulo {current}/{total} (tipografía y repeticiones)..."
            )
            tracker.update_time_remaining()

        if total_chapters > 0:
            chapters_list = []
            for i, ch_dict in enumerate(chapters_data):
                chapters_list.append({
                    "index": ch_dict.get("chapter_number", i + 1),
                    "title": ch_dict.get("title", f"Capítulo {i + 1}"),
                    "content": ch_dict.get("content", ""),
                })

            correction_issues_by_chapter = orchestrator.analyze_by_chapters(
                chapters=chapters_list,
                spacy_docs=None,
                project_id=ctx["project_id"],
                progress_callback=corrections_progress_callback,
            )

            correction_issues = []
            for ch_issues in correction_issues_by_chapter.values():
                correction_issues.extend(ch_issues)
        else:
            tracker.update_storage(current_action="Buscando repeticiones y errores tipográficos...")
            correction_issues = orchestrator.analyze(
                text=full_text,
                chapter_index=None,
                spacy_doc=ctx.get("spacy_doc"),
            )

        if spelling_correction_issues:
            existing_keys = {
                (
                    issue.start_char,
                    issue.end_char,
                    str(issue.text).strip().lower(),
                    str(issue.suggestion or "").strip().lower(),
                )
                for issue in correction_issues
            }
            added_spelling_issues = 0
            for issue in spelling_correction_issues:
                issue_key = (
                    issue.start_char,
                    issue.end_char,
                    str(issue.text).strip().lower(),
                    str(issue.suggestion or "").strip().lower(),
                )
                if issue_key in existing_keys:
                    continue
                correction_issues.append(issue)
                existing_keys.add(issue_key)
                added_spelling_issues += 1
            if added_spelling_issues:
                logger.info("Added %s spelling issues from voting checker", added_spelling_issues)

        logger.info(f"Corrections analysis found {len(correction_issues)} suggestions")

    except _SkipSpellingChecks:
        logger.info("Spelling/editorial checks omitted by project settings")
    except ImportError as e:
        logger.warning(f"Corrections module not available: {e}")
    except Exception as e:
        logger.warning(f"Error in corrections analysis: {e}")

    tracker.end_phase("grammar")
    tracker.update_storage(
        metrics_update={
            "grammar_issues_found": len(grammar_issues),
            "correction_suggestions": len(correction_issues),
        },
    )
    logger.info(
        f"Grammar analysis complete: {len(grammar_issues)} grammar issues, "
        f"{len(correction_issues)} correction suggestions"
    )

    ctx["grammar_issues"] = grammar_issues
    ctx["spelling_issues"] = spelling_issues
    ctx["correction_issues"] = correction_issues
