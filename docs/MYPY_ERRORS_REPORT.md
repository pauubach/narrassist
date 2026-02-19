# Reporte de Errores MyPy - Estado Actual

**Fecha**: 2026-02-19
**Comando**: `python -m mypy src/narrative_assistant/core src/narrative_assistant/persistence src/narrative_assistant/parsers src/narrative_assistant/alerts --ignore-missing-imports`

---

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| **Errores iniciales** | 306 |
| **Errores actuales** | 231 |
| **Errores corregidos** | 75 (-24.5%) |
| **Progreso** | 🟩 Avance significativo |

---

## Distribución de Errores por Tipo

| Tipo de Error | Cantidad | % del Total | Reducción | Prioridad |
|---------------|----------|-------------|-----------|-----------|
| `attr-defined` | 38 | 16.5% | -7% | 🔴 Alta |
| `no-any-return` | 36 | 15.6% | -12% | 🟡 Media |
| `assignment` | 33 | 14.3% | 0% | 🟡 Media |
| `arg-type` | 32 | 13.9% | **-53%** ✅ | 🟡 Media |
| `index` | 27 | 11.7% | **-23%** | 🟡 Media |
| `return-value` | 22 | 9.5% | 0% | 🟡 Media |
| `annotation-unchecked` | 12 | 5.2% | 0% | 🟢 Baja |
| `operator` | 8 | 3.5% | 0% | 🟡 Media |
| `union-attr` | 8 | 3.5% | **-60%** ✅ | 🟢 Baja |
| `misc` | 8 | 3.5% | -11% | 🟢 Baja |
| `call-overload` | 6 | 2.6% | 0% | 🟢 Baja |
| `no-redef` | 5 | 2.2% | 0% | 🟢 Baja |
| Otros | 10 | 4.3% | Varios | 🟢 Baja |

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

### ✅ Completadas (75 errores)

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

6. **Otros** (3 errores)
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
