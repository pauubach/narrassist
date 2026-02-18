# Dead Code Scan — 18 Feb 2026

## Backend (vulture, min-confidence 80%)

**Total**: 26 líneas de código muerto detectadas

### Variables no usadas (100% confidence)
- `attribute_consistency.py:1017`: `normalized_key`
- `story_bible.py:130-131`: `include_emotions`, `include_knowledge`
- `coref_voting.py:218`: `antecedents`
- `history.py:887`: `keep_days`
- `register.py:1019`: `changes_count`

### Imports no usados (90% confidence)
**Exporters** (PDFexport utilities, probablemente preparados para futuro):
- `document_exporter.py`: `gray`, `TA_JUSTIFY`, `TA_LEFT`, `ListFlowable`, `ListItem`
- `review_report_exporter.py`: `gray`, `TA_JUSTIFY`, `TA_LEFT`, `TA_RIGHT`, `ListFlowable`, `ListItem`

**NLP/LLM** (modelos opcionales no usados actualmente):
- `llm/client.py:406`: `AutoModelForCausalLM`
- `orthography/voting_checker.py:1293`: `AutoModelForMaskedLM`
- `sentiment.py:214`: `pysentimiento`
- `epub_parser.py:118`: `ebooklib`

**Análisis**:
- `narrative_structure.py:25`: `Token`
- `relationship_clustering.py:343`: `dendrogram`
- `coref_voting.py:12`: `CorefCandidate`
- `dialogue_style_checker.py:13`: `get_dialogue_repository`

### Syntax error
- `dictionaries/manager.py:193`: expected 'except' or 'finally' block ⚠️ **Revisar**

---

## Frontend (TypeScript/Vue)

**Método**: Script bash para detectar exports sin referencias.

**Limitación**: Grep-based, puede tener false positives (dynamic imports, router, stores).

**Exports totales**: 159

**Script disponible**: `scripts/find_unused_exports.sh`

**Próximos pasos**:
1. Ejecutar script bash (requiere ajuste de paths en Windows)
2. Validar manualmente cada candidato
3. Considerar herramientas especializadas: `ts-prune`, `unimported`

---

## Recomendaciones

### Alta prioridad
1. **Fix syntax error**: `dictionaries/manager.py:193`
2. Eliminar variables no usadas (5 casos, 100% confidence)

### Media prioridad
3. Revisar imports de exporters — probablemente obsoletos tras eliminar features PDF
4. Revisar imports de modelos LLM alternativos — si no se usan, eliminar

### Baja prioridad
5. Imports NLP/análisis — pueden ser para extensiones futuras
6. Frontend exports — requiere herramienta especializada (ts-prune)

---

## Estado

- ✅ Backend scan completado (vulture)
- 📋 Frontend scan preparado (requiere ejecución manual)
- 26 líneas detectadas en backend
- 1 syntax error detectado (CRITICO)
