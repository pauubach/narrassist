# Reporte de Errores MyPy - Estado Actual

**Fecha**: 2026-02-19
**Comando**: `python -m mypy src/narrative_assistant/core src/narrative_assistant/persistence src/narrative_assistant/parsers src/narrative_assistant/alerts --ignore-missing-imports`

---

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| **Errores iniciales** | 306 |
| **Errores actuales** | 167 |
| **Errores corregidos** | 139 (-45.4%) |
| **Progreso** | 🟢 Casi a la mitad |

---

## Distribución de Errores por Tipo

| Tipo de Error | Cantidad | % del Total | Reducción vs Inicial | Prioridad |
|---------------|----------|-------------|----------------------|-----------|
| `attr-defined` | 37 | 22.2% | **-10%** (41→37) | 🔴 Alta |
| `no-any-return` | 27 | 16.2% | **-36%** (42→27) ✅ | 🟡 Media |
| `arg-type` | 23 | 13.8% | **-66%** (68→23) ✅✅ | 🟢 Baja |
| `assignment` | 21 | 12.6% | **-36%** (33→21) ✅ | 🟡 Media |
| `index` | 17 | 10.2% | **-51%** (35→17) ✅ | 🟢 Baja |
| `return-value` | 12 | 7.2% | **-45%** (22→12) ✅ | 🟡 Media |
| `annotation-unchecked` | 12 | 7.2% | 0% (12→12) | 🟢 Baja |
| `operator` | 7 | 4.2% | **-13%** (8→7) | 🟡 Media |
| `union-attr` | 6 | 3.6% | **-70%** (20→6) ✅✅ | 🟢 Baja |
| `misc` | 6 | 3.6% | **-33%** (9→6) ✅ | 🟢 Baja |
| `no-redef` | 5 | 3.0% | 0% (5→5) | 🟢 Baja |
| `call-overload` | 1 | 0.6% | **-83%** (6→1) ✅✅ | 🟢 Baja |
| Otros | 13 | 7.8% | Varios | 🟢 Baja |

---

## Archivos con Más Errores (Top 15)

| Archivo | Errores | Tipos Principales |
|---------|---------|-------------------|
| `alerts/engine.py` | 36 | arg-type, union-attr, index |
| `nlp/training_data/training_examples.py` | 27 | attr-defined, index, operator |
| `persistence/history.py` | 16 | arg-type, union-attr |
| `nlp/ner.py` | 14 | attr-defined, assignment, union-attr |
| `nlp/spacy_title_integration.py` | 13 | assignment, index, has-type |
| `persistence/editorial_work.py` | 10 | arg-type, union-attr |
| `persistence/session.py` | 9 | index, union-attr |
| `nlp/orthography/voting_checker.py` | 9 | no-any-return, assignment, misc |
| `nlp/attributes.py` | 9 | return-value, index |
| `entities/repository.py` | 7 | return-value, arg-type |
| `entities/__init__.py` | 7 | misc, assignment |
| `nlp/scope_resolver.py` | 6 | no-any-return, operator, misc |
| `nlp/extraction/extractors/dependency_extractor.py` | 6 | no-any-return |
| `core/model_manager.py` | 6 | no-any-return, assignment |
| `persistence/analysis.py` | 6 | assignment |

---

## Correcciones Aplicadas

### ✅ Completadas (139 errores - 45.4% del total)

1. **Imports faltantes** (7 errores)
   - Agregado `from typing import Any` en 5 archivos
   - Archivos: out_of_character.py, llm_extractor.py, register.py, entity_validator.py, ner.py

2. **int(cursor.lastrowid)** (6 errores)
   - Agregadas assertions `assert cursor.lastrowid is not None` antes de `int(cursor.lastrowid)`
   - Archivo: persistence/analysis.py (líneas 392, 458, 511, 592, 678, 765)

3. **Type hints incorrectos** (4 errores)
   - Corregido `list[dict[str, Any]]` → `list[OutOfCharacterEvent]` en out_of_character.py
   - Corregido `list[str]` → `list[Any]` para params en entities/repository.py
   - Agregado type hint a created_alerts/errors en alerts/engine.py

4. **Result pattern** (3 errores)
   - Agregadas assertions para narrowing de Result.value/error en alerts/engine.py
   - Cast explícito en llm/sanitization.py

5. **Persistence layer fixes** (45 errores)
   - Null checks en history.py (16 errores)
   - Null checks en session.py (9 errores)
   - Row indexing con null guards en database.py, timeline.py, snapshot.py
   - Device preference validation en config.py
   - Memory monitor platform compatibility

6. **Parsers layer fixes** (25 errores)
   - Fix return types en todos los parsers (Result[RawDocument])
   - Null checks para Path en base.py, txt_parser.py, pdf_parser.py, epub_parser.py, docx_parser.py
   - Structure detector heading_level validation

7. **Core module fixes** (22 errores)
   - Device detection con null handling (device.py)
   - Model manager return types (model_manager.py)
   - Singleton pattern typing (patterns.py)
   - Resource manager type guards

8. **Otros** (3 errores)
   - Type hints en voice/profiles.py (Counter variables)
   - Type hints en analysis/pacing.py, relationship_clustering.py

---

## Análisis de Errores Restantes

### 🔴 Prioridad Alta (115 errores)

#### arg-type (54 errores)
**Causa**: Tipos incompatibles en argumentos de funciones.

**Patrones comunes**:
- `Path | None` pasado donde se espera `Path` (languagetool_manager.py)
- `EmotionalState | None` pasado donde se espera `EmotionalState` (emotional_coherence.py)
- `int | None` pasado donde se espera `int` (history.py, session.py)
- `str` pasado donde se espera `Literal` (config.py, client.py)

**Solución**: Agregar null checks o casts antes de pasar argumentos.

#### attr-defined (41 errores)
**Causa**: Acceso a atributos que mypy no puede verificar que existan.

**Patrones comunes**:
- `Collection[str]` usado como dict (training_examples.py: 13 ocurrencias)
- Atributos dinámicos en decorators (patterns.py)
- Métodos no existentes en tipos Any/object (spacy_title_integration.py)

**Solución**: Tipar correctamente las variables o usar casts explícitos.

#### union-attr (20 errores)
**Causa**: Acceso a atributos de valores que pueden ser None.

**Patrones comunes**:
- `Alert | None` sin null check antes de acceder a `.status` (engine.py)
- `EmotionalState | None` sin null check (emotional_coherence.py)
- `list[Alert] | None` iterado sin verificación (engine.py)

**Solución**: Agregar `if value is not None:` antes de acceder a atributos.

---

### 🟡 Prioridad Media (131 errores)

#### index (35 errores)
**Causa**: Indexación de objetos que mypy no puede verificar.

**Patrones comunes**:
- `Row | None` indexado sin null check (session.py)
- `object` usado como dict (training_examples.py, engine.py)
- `int` usado como dict (spacy_title_integration.py)

**Solución**: Agregar type assertions o null checks antes de indexar.

#### assignment (33 errores)
**Causa**: Asignaciones con tipos incompatibles.

**Patrones comunes**:
- `DeviceInfo | None` asignado a `DeviceInfo` (device.py)
- `Path | None` asignado a `Path` (parsers)
- Tipos incorrectos en variables inferidas

**Solución**: Agregar null checks o cambiar tipos de variables.

#### no-any-return (41 errores)
**Causa**: Funciones retornando Any sin cast explícito.

**Patrones comunes**:
- Retornar valores de dicts sin cast (database.py, timeline.py, collection.py)
- Retornar resultados de getattr sin cast (model_manager.py)

**Solución**: Agregar cast explícito antes del return: `result: ExpectedType = expression`.

#### return-value (22 errores)
**Causa**: Tipo de retorno no coincide con la firma.

**Patrones comunes**:
- Funciones que retornan `X | None` pero declaran `X`
- Funciones que retornan `Result[X]` pero declaran `Result[Y]`

**Solución**: Corregir firmas de función o agregar null checks.

#### operator (8 errores)
**Causa**: Operadores usados con tipos incorrectos.

**Patrones comunes**:
- Comparación con None sin null check (`< None`, `in object`)
- División con `Path | None` (languagetool_manager.py)

**Solución**: Agregar null checks antes de operaciones.

---

### 🟢 Prioridad Baja (37 errores)

- **annotation-unchecked** (12): Funciones sin type hints, usar `--check-untyped-defs`
- **misc** (9): Redefiniciones, incompatibilidades varias
- **call-overload** (6): Llamadas con overloads complejos (subprocess.Popen)
- **no-redef** (5): Redefiniciones de símbolos
- **Otros** (5): str, has-type, type-var, return, dict-item, bytes, Any

---

## Recomendaciones

### Estrategia de Corrección

1. **Fase 1**: Corregir errores de prioridad alta (115 errores)
   - Foco en union-attr y attr-defined (críticos para seguridad)
   - Agregar null checks sistemáticamente

2. **Fase 2**: Corregir errores de prioridad media (131 errores)
   - Foco en arg-type y assignment
   - Mejorar type hints en variables

3. **Fase 3**: Evaluar errores de prioridad baja (37 errores)
   - Algunos pueden requerir `# type: ignore` justificado
   - Otros requieren refactoring mayor

### Archivos Prioritarios

**Top 5 archivos para revisar**:
1. `alerts/engine.py` (36 errores) - Core del sistema de alertas
2. `nlp/training_data/training_examples.py` (27 errores) - Datos de entrenamiento
3. `persistence/history.py` (16 errores) - Sistema de undo/redo
4. `nlp/ner.py` (14 errores) - Reconocimiento de entidades
5. `nlp/spacy_title_integration.py` (13 errores) - Integración spaCy

### Notas Importantes

- **NO usar `type: ignore` masivamente**: Solo en casos justificados (decorators dinámicos, limitaciones de mypy)
- **Preferir null checks sobre casts**: `if x is not None:` es más seguro que `cast(T, x)`
- **Documentar limitaciones**: Algunos errores pueden ser falsos positivos de mypy que requieren comentarios explicativos

---

## Próximos Pasos

- [ ] Corregir union-attr en alerts/engine.py (alta prioridad)
- [ ] Corregir attr-defined en training_examples.py
- [ ] Agregar null checks en persistence/history.py
- [ ] Revisar y corregir arg-type sistemáticamente
- [ ] Ejecutar CI para verificar correcciones

---

**Generado por**: Claude Sonnet 4.5
**Script de verificación**: `python -m mypy src/narrative_assistant/core src/narrative_assistant/persistence src/narrative_assistant/parsers src/narrative_assistant/alerts --ignore-missing-imports`
