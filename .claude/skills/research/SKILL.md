---
name: research
description: "Investigación estructurada de documentación técnica, papers, o APIs externas usando mcp__fetch__fetch. Invocar cuando el usuario diga 'busca cómo hace X la librería Y', 'lee la doc de Z', 'investiga el paper sobre W', 'cómo funciona esto en spaCy/sentence-transformers/Ollama'."
---

# /research — Investigación de documentación externa

## Cuándo usar

- Antes de implementar una integración nueva (nueva versión de spaCy, nuevo modelo Ollama).
- Al evaluar una librería o técnica NLP desconocida.
- Para leer la documentación oficial de algo antes de usarlo.
- Al investigar papers o benchmarks relevantes para el proyecto.

## Argumentos

- `<URL>` — URL directa a leer
- `<librería> <concepto>` — buscar en la doc oficial de esa librería
- `--summarize` — devolver resumen ejecutivo (por defecto: extracción de lo relevante al proyecto)

## Flujo

### Paso 1 — Fetch del recurso

```
mcp__fetch__fetch(url: "<URL>", maxLength: 10000)
```

Para URLs de documentación que requieren navegación:
- spaCy: `https://spacy.io/api/<componente>`
- sentence-transformers: `https://www.sbert.net/docs/`
- Ollama: `https://github.com/ollama/ollama/blob/main/docs/`
- HuggingFace: `https://huggingface.co/docs/transformers/`

### Paso 2 — Filtrar lo relevante al proyecto

No copiar el contenido crudo — extraer lo que aplica directamente al proyecto:

- **APIs y firmas de función** que vamos a usar.
- **Parámetros de configuración** relevantes para el pipeline actual.
- **Limitaciones y gotchas** conocidos (especialmente para español, modelos locales).
- **Ejemplos de código** adaptables al stack (Python 3.11, spaCy es_core_news_lg, Ollama local).

### Paso 3 — Output

```
## Research: <tema>

### Fuente
<URL> — <fecha de consulta>

### Lo relevante para narrassist

#### API / Firma
```python
# Cómo se usa en nuestro contexto
```

#### Configuración importante
- parámetro X: ...
- parámetro Y: ...

#### Limitaciones / Gotchas
- ⚠️ [limitación importante]

#### Recomendación
¿Deberíamos adoptar esto? ¿Cómo afecta al pipeline actual?
```

### Paso 4 — Aplicar o proponer

Si la investigación lleva a un cambio concreto → proponer el cambio con justificación. No implementar directamente salvo que sea un fix trivial.

## Ejemplo de uso

```
/research spaCy entity_ruler

→ Fetch https://spacy.io/api/entityruler
→ Extraer: cómo añadir patrones de entidad personalizados para personajes
   que spaCy no detecta (nombres propios no convencionales, apodos, etc.)
→ Proponer: añadir EntityRuler pipeline al cargador de modelos para
   apodos/alias detectados por el corrector editorial.
```

## Fuentes de referencia del proyecto

| Área | URL base |
|------|----------|
| spaCy API | `https://spacy.io/api/` |
| spaCy Modelo ES | `https://spacy.io/models/es` |
| sentence-transformers | `https://www.sbert.net/docs/` |
| Ollama API | `https://github.com/ollama/ollama/blob/main/docs/api.md` |
| FastAPI | `https://fastapi.tiangolo.com/` |
| PrimeVue 4 | `https://primevue.org/` |
| Tauri v2 | `https://v2.tauri.app/` |
