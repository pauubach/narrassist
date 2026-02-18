# ADR-002: LLM Local con Ollama para Análisis Semántico

## Estado

**Aceptada** — 2026-01-15 (Sprint S1)

## Contexto

El análisis NLP tradicional (spaCy, reglas heurísticas) tiene limitaciones para:
- Detección de comportamiento fuera de personaje (OOC)
- Análisis de tono emocional y registro de habla
- Inferencia de intenciones y motivaciones
- Detección de contradicciones narrativas sutiles
- Validación de correferencias ambiguas

Los LLMs pueden mejorar significativamente la precisión, pero:
1. **Privacidad**: APIs externas (OpenAI, Anthropic) requieren enviar texto del manuscrito → **INACEPTABLE**
2. **Costo**: Procesar novelas de 100k palabras con APIs de pago → miles de USD por análisis
3. **Latencia**: APIs remotas añaden latencia de red
4. **Disponibilidad**: Requieren conexión a internet constante

Alternativas consideradas:

| Opción | Privacidad | Costo | Performance | Disponibilidad |
|--------|------------|-------|-------------|----------------|
| **OpenAI API** | ❌ Envía datos | 💰💰💰 Alto | ⚡ Rápido | ☁️ Online |
| **Anthropic API** | ❌ Envía datos | 💰💰💰 Alto | ⚡ Rápido | ☁️ Online |
| **Transformers local** | ✅ Privado | ✅ Gratis | 🐌 Lento | 📴 Offline |
| **Ollama** | ✅ Privado | ✅ Gratis | ⚡ Rápido | 📴 Offline |

## Decisión

Usar **Ollama** como runtime local de LLMs con los siguientes modelos:

| Modelo | Tamaño | Uso | Notas |
|--------|--------|-----|-------|
| **llama3.2** | 3B | Default | Rápido, funciona en CPU |
| **qwen2.5** | 7B | Español | Mejor para español |
| **mistral** | 7B | Razonamiento | Mayor calidad de análisis |
| **gemma2** | 9B | Alta precisión | Requiere GPU |

**Arquitectura**:
```
┌─────────────────┐
│ Narrative Asst. │
│    (FastAPI)    │
└────────┬────────┘
         │ HTTP localhost:11434
         ▼
┌─────────────────┐
│     Ollama      │
│   (Servidor)    │
└────────┬────────┘
         │ Carga modelos .gguf
         ▼
┌─────────────────┐
│  ~/.ollama/     │
│   models/       │
└─────────────────┘
```

**Votación multi-modelo**:
- Correferencias: embeddings (30%) + LLM (35%) + morpho (20%) + heuristics (15%)
- Análisis de comportamiento: rule_based + LLM (llama3.2, qwen2.5, mistral)
- Consenso mínimo configurable en Settings

**Configuración**:
```bash
# Variables de entorno
NA_LLM_BACKEND=ollama  # ollama, transformers, none
NA_OLLAMA_HOST=http://localhost:11434
NA_OLLAMA_MODEL=llama3.2  # modelo por defecto

# Fallback
# Si Ollama no disponible → sistema funciona sin LLM (solo heurísticas)
```

## Consecuencias

### Positivas ✅

1. **Privacidad absoluta**: Modelos corren 100% localmente, texto nunca sale del PC
2. **Costo cero**: Sin cargos por tokens ni límites de uso
3. **Offline-first**: Funciona sin internet después de descargar modelos
4. **Flexibilidad**: Múltiples modelos disponibles, usuario elige según hardware
5. **Comunidad activa**: Ollama tiene 100k+ estrellas en GitHub, modelos constantemente actualizados
6. **Fácil instalación**: Instalador one-click para Windows/macOS/Linux
7. **GGUF quantization**: Modelos optimizados para correr en hardware modesto

### Negativas ⚠️

1. **Requisitos de hardware**:
   - Mínimo 8 GB RAM para llama3.2 (3B)
   - Recomendado 16 GB RAM para qwen2.5/mistral (7B)
   - GPU con 4+ GB VRAM mejora velocidad
2. **Descarga inicial**: Modelos ocupan 2-4 GB cada uno
3. **Velocidad variable**:
   - CPU: 5-10 tokens/s (lento pero funcional)
   - GPU: 30-50 tokens/s (rápido)
4. **Calidad menor que GPT-4**: Modelos locales son menos capaces que modelos cloud de última generación
5. **Setup adicional**: Requiere instalar y configurar Ollama (mitigado con `setup_ollama.py`)

### Mitigaciones

- **Fallback graceful**: Si Ollama no disponible, sistema funciona con métodos no-LLM
- **Instalación automática**: `python scripts/setup_ollama.py` automatiza la instalación
- **CPU fallback**: Script `start_ollama_cpu.bat` para hardware limitado
- **Selección de modelo**: Usuario elige entre calidad (gemma2) y velocidad (llama3.2)
- **Chunking**: Textos largos se dividen en chunks para no saturar contexto

## Notas de Implementación

Ver:
- `src/narrative_assistant/llm/ollama_client.py` — cliente HTTP para Ollama
- `src/narrative_assistant/llm/prompts.py` — prompts con CoT y anti-injection
- `src/narrative_assistant/llm/sanitization.py` — sanitización de inputs
- `src/narrative_assistant/nlp/coreference_resolver.py` — votación multi-método
- `scripts/setup_ollama.py` — instalación automatizada

**Prompting**:
- Chain-of-Thought (CoT) para razonamiento explícito
- Self-reflection en detección de contradicciones
- Anti-injection sanitization (protección contra texto malicioso en manuscritos)

## Referencias

- [Ollama](https://ollama.com/) — Runtime local de LLMs
- [GGUF Format](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md) — Quantización eficiente
- [Qwen 2.5](https://huggingface.co/Qwen/Qwen2.5-7B) — Mejor modelo para español
- Implementado en Sprint S1, mejorado en S5 (prompting avanzado)
