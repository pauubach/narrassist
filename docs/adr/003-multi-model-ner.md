# ADR-003: NER Multi-Modelo con Votación

## Estado

**Aceptada** — 2026-01-15 (Sprint S1)

## Contexto

La extracción de entidades (NER - Named Entity Recognition) es crítica para el análisis narrativo:
- Identificar personajes, lugares, objetos
- Asociar menciones con entidades
- Construir grafos de relaciones
- Detectar inconsistencias de atributos

**Problema**: NER para español narrativo es difícil:
1. **Ambigüedad**: "María" puede ser nombre o ciudad
2. **Correferencias**: "ella", "la mujer", "María", "la detective" → misma persona
3. **Registro literario**: Descripciones complejas, juegos de palabras, seudónimos
4. **Nombres ficticios**: spaCy entrenado en noticias, no reconoce "Frodo" o "Westeros"

**Precisión de métodos individuales** (evaluado en corpus de novelas españolas):

| Método | Precision | Recall | F1 | Notas |
|--------|-----------|--------|-----|-------|
| **spaCy (es_core_news_lg)** | 0.78 | 0.71 | 0.74 | Falsos positivos con nombres ficticios |
| **PlanTL RoBERTa** | 0.82 | 0.68 | 0.74 | Mejor precision, menor recall |
| **Gazetteer (heurísticas)** | 0.65 | 0.85 | 0.73 | Alto recall, muchos falsos positivos |
| **LLM (qwen2.5)** | 0.75 | 0.80 | 0.77 | Lento, costoso computacionalmente |

Ningún método individual supera **F1 = 0.77**.

Alternativas consideradas:
- **Solo spaCy**: Rápido pero pierde nombres ficticios y contexto narrativo
- **Solo LLM**: Mejor calidad pero 50x más lento y requiere Ollama
- **spaCy + Gazetteer**: Mejora recall pero no precision
- **Votación multi-modelo**: Combinar fortalezas de todos los métodos

## Decisión

Implementar sistema de **votación ponderada entre 4 métodos**:

```python
┌──────────────────────────────────────────────────────┐
│              Text Chunking (5000 chars)              │
└──────────────────┬───────────────────────────────────┘
                   │
        ┌──────────┼──────────┬──────────┐
        │          │          │          │
        ▼          ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │ spaCy  │ │RoBERTa │ │ Gaz.   │ │  LLM   │
   │  30%   │ │  25%   │ │  20%   │ │  25%   │
   └────┬───┘ └───┬────┘ └───┬────┘ └───┬────┘
        │         │          │          │
        └─────────┴──────────┴──────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  Entity Merger  │
         │  (Fuzzy Match)  │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Gazetteer Feed │
         │  (Auto-Update)  │
         └─────────────────┘
```

**Pesos de votación**:
- **spaCy**: 30% (baseline confiable)
- **PlanTL RoBERTa**: 25% (alta precision)
- **Gazetteer**: 20% (contexto histórico)
- **LLM**: 25% (razonamiento semántico)

**Proceso**:
1. Cada método extrae entidades independientemente
2. Fuzzy matching (Levenshtein distance < 2) para identificar menciones de la misma entidad
3. Votación ponderada → confianza agregada
4. Threshold: confianza > 0.5 para aceptar entidad
5. Auto-alimentación de gazetteer con entidades de alta confianza (>0.8)

**Configuración**:
```python
# En Settings UI
- Métodos habilitados: [spaCy, RoBERTa, Gazetteer, LLM]  # selección múltiple
- Umbral de confianza: 0.5  # slider
- Auto-feed gazetteer: true
```

## Consecuencias

### Positivas ✅

1. **Mayor F1**: 0.84 (mejora de +7 puntos vs mejor método individual)
2. **Precision**: 0.86 (+4 puntos vs spaCy solo)
3. **Recall**: 0.82 (+11 puntos vs RoBERTa solo)
4. **Adaptabilidad**: Gazetteer aprende nombres ficticios del manuscrito
5. **Robustez**: Si un método falla o no está disponible (e.g., Ollama), los demás compensan
6. **Configurabilidad**: Usuario puede deshabilitar métodos lentos (LLM) si prefiere velocidad
7. **Confianza calibrada**: Scoring ponderado refleja acuerdo entre métodos

### Negativas ⚠️

1. **Complejidad**: 4 pipelines de NER en paralelo
2. **Latencia**: ~2-3x más lento que spaCy solo (mitigado con paralelización)
3. **Memoria**: Cargar múltiples modelos (spaCy 500 MB + RoBERTa 400 MB + LLM variable)
4. **Dependencias**: Requiere transformers, sentence-transformers, Ollama (opcional)
5. **Tuning**: Pesos de votación requieren calibración en corpus de prueba

### Mitigaciones

- **Paralelización**: Métodos corren en paralelo con `ThreadPoolExecutor`
- **Lazy loading**: Modelos se cargan bajo demanda
- **Fallback**: Si LLM no disponible, repesado automático de métodos disponibles
- **Caching**: Embeddings y predicciones se cachean por chunk de texto
- **Progresión**: Métodos rápidos (spaCy, Gazetteer) primero → feedback temprano al usuario

## Notas de Implementación

Ver:
- `src/narrative_assistant/nlp/ner.py` — `NERExtractor` con multi-model voting
- `src/narrative_assistant/nlp/ner_roberta.py` — PlanTL RoBERTa integration
- `src/narrative_assistant/analysis/gazetteer.py` — Auto-feeding gazetteer
- `tests/unit/test_ner_voting.py` — Tests de votación

**Modelos**:
- spaCy: `es_core_news_lg` (500 MB) — pre-instalado
- RoBERTa: `PlanTL-GOB-ES/roberta-base-bne-ner` (400 MB) — descarga bajo demanda
- Gazetteer: JSON local con nombres, actualizado dinámicamente
- LLM: Ollama con qwen2.5/llama3.2 — opcional

**Evaluación**:
- Corpus de prueba: 5 novelas españolas contemporáneas (~300k palabras)
- Gold standard: anotación manual de 2 correctores profesionales
- Métricas: Precision, Recall, F1 por tipo de entidad (PERSON, LOCATION, OBJECT)

## Referencias

- [PlanTL RoBERTa NER](https://huggingface.co/PlanTL-GOB-ES/roberta-base-bne-ner)
- [spaCy Spanish Models](https://spacy.io/models/es)
- [Ensemble Methods for NER](https://arxiv.org/abs/1909.02915)
- Implementado en Sprint S1, gazetteer auto-feeding añadido en mismo sprint
