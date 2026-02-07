# Rediseño de la Pantalla de Descarga / Configuración Inicial

**Fecha**: 2026-02-07
**Estado**: Propuesta / Pendiente de revisión
**Plataformas**: Windows + macOS

---

## 1. Diagnóstico Técnico

### 1.1 Estado actual de las descargas

El sistema define **3 modelos** en `KNOWN_MODELS` (model_manager.py):

| Modelo | Tamaño | Se descarga al inicio | Monitoreo de progreso | Soporte paralelo |
|--------|--------|----------------------|----------------------|-----------------|
| spaCy `es_core_news_lg` | ~540 MB | Sí | **NO** (spaCy CLI no reporta bytes) | No (pip subprocess) |
| Embeddings MiniLM | ~470 MB | Sí | **SÍ** (monitor de cache HF cada 500ms) | Posible |
| Transformer NER RoBERTa | ~500 MB | **NO** (lazy en primer análisis) | **NO** (sin monitor) | Posible |

### 1.2 Problemas identificados que causan "parece colgado"

**A. spaCy no reporta progreso real**

`_download_spacy_model()` ejecuta `spacy.cli.download()` que internamente hace `pip install`. Durante esta operación (~540 MB, 2-5 min):
- La fase se pone en `"downloading"` pero `bytes_downloaded` queda en 0
- El frontend muestra barra indeterminada sin bytes ni velocidad
- No hay ningún indicador de que esté haciendo algo
- En conexiones lentas esto puede durar 10+ minutos sin cambio visible

**B. Transformer NER no tiene monitor de progreso**

`_download_transformer_ner_model()` llama a `AutoTokenizer.from_pretrained()` y `AutoModelForTokenClassification.from_pretrained()`. Estas llamadas bloquean el thread durante la descarga (~500 MB) sin actualizar `bytes_downloaded`. Solo se actualizan las fases:
- `"connecting"` → `"downloading"` → (silencio total durante 5-10 min) → `"installing"`

**C. Solo embeddings tiene monitor real**

Solo `_download_embeddings_model()` lanza `_monitor_hf_download()` en un thread separado que escanea `~/.cache/huggingface/hub` cada 500ms y calcula bytes reales + velocidad. **Los otros dos modelos no tienen equivalente.**

**D. La ruta del cache HF puede variar entre plataformas**

El monitor busca en:
- `~/.cache/huggingface/hub` (Linux/macOS estándar)
- `~/.cache/torch/sentence_transformers` (fallback)

En Windows, HuggingFace Hub usa `%USERPROFILE%\.cache\huggingface\hub` que es equivalente a `Path.home() / ".cache" / "huggingface" / "hub"`. Funciona porque `Path.home()` resuelve `C:\Users\<user>`. **No hay problema de compatibilidad Win/Mac aquí.**

### 1.3 Descargas secuenciales vs paralelas

**Estado actual**: Las descargas son **secuenciales** dentro de un solo `threading.Thread`:

```python
# system.py:457-466
def download_task():
    for model_name in request.models:  # Uno tras otro
        if model_name == "spacy":
            manager.ensure_model(ModelType.SPACY, ...)
        elif model_name == "embeddings":
            manager.ensure_model(ModelType.EMBEDDINGS, ...)
```

**¿Se pueden paralelizar?** Depende del cuello de botella:

| Modelo | Fuente | Servidor |
|--------|--------|----------|
| spaCy | github.com/explosion → pip | CDN de GitHub |
| Embeddings | huggingface.co | CDN de HuggingFace |
| Transformer NER | huggingface.co | CDN de HuggingFace |

- spaCy + Embeddings: **SÍ paralelizables** (servidores distintos)
- Embeddings + Transformer NER: **posiblemente**, ambos van a HuggingFace pero usan CDN distribuida, la velocidad individual rara vez satura el enlace del usuario
- Los 3 en paralelo: **posible pero arriesgado** — en conexiones < 20 Mbps, tres descargas simultáneas ralentizan cada una y el usuario ve menos progreso individual

---

## 2. Debate de Expertos

### USUARIO (escritor/editor profesional)

> "He instalado la aplicación y lleva un buen rato con una barra que se mueve pero no avanza. Dice 1530 MB pero solo veo un modelo. No sé si se ha colgado. ¿Puedo cerrar y volver a abrir? ¿Perderé lo que ya descargó?"

**Necesidades**:
- Certeza de que la aplicación está haciendo algo (no se ha colgado)
- Saber cuánto falta (tiempo o porcentaje, no bytes)
- No tener que tomar decisiones técnicas
- Saber que esto solo pasa una primera vez
- Poder cerrar y reabrir sin perder progreso

### PRODUCT OWNER

> "La primera impresión es crítica. Un usuario que instala una herramienta para correctores profesionales y ve que ni siquiera escribe correctamente los acentos (hemos corregido 29 errores de tildes) o que usa nombres técnicos incomprensibles, pierde la confianza. Si además la barra parece colgada, desinstala."

**Prioridades**:
1. **Corrección lingüística impecable** — somos una herramienta para correctores
2. **Confianza visual** — que el usuario sepa que todo funciona
3. **Descarga completa al inicio** — mejor 5 minutos una vez que sorpresas después
4. **Nombres funcionales** — el usuario no necesita saber qué es spaCy

**Sobre descargar todo al inicio**:
> "Sí, hay que descargar los 3 modelos al inicio. Prefiero que el usuario espere 5 minutos la primera vez a que, cuando lance su primer análisis después de configurar todo, tenga que esperar otros 5 minutos inesperados. Eso sería una experiencia terrible: 'ya lo configuré, ¿por qué tarda tanto?'"

### BACKEND ENGINEER

> "El problema real no es la descarga en sí, sino que **2 de 3 modelos no reportan progreso granular**. Los datos para actualizar la barra de progreso existen — HuggingFace descarga archivos al cache local — pero no los estamos leyendo."

**Análisis técnico**:

1. **spaCy** usa `spacy.cli.download()` que internamente ejecuta `pip install`. No hay API de progreso. **Solución**: monitorear el directorio destino igual que hacemos con embeddings, o usar `pip download` con `--progress-bar` y parsear stdout.

2. **Transformer NER** usa `AutoModelForTokenClassification.from_pretrained()` que descarga al cache de HuggingFace (`~/.cache/huggingface/hub/models--PlanTL-GOB-ES--roberta-base-bne-capitel-ner/`). **Solución**: reutilizar `_monitor_hf_download()` — es exactamente el mismo patrón que embeddings.

3. **Paralelismo**: Técnicamente viable con `ThreadPoolExecutor(max_workers=2)`. Recomiendo máximo 2 en paralelo:
   - spaCy + uno de HF en paralelo (servidores distintos)
   - Los 2 de HF en secuencial (mismo CDN, compartir ancho de banda no ayuda)
   - Beneficio estimado: reducir tiempo total de ~12 min a ~8 min en conexión de 20 Mbps

4. **Reiniciabilidad**: Si el usuario cierra la app a mitad de descarga:
   - spaCy: pip deja cache parcial, re-descarga desde 0 pero pip resume si hay cache HTTP
   - HuggingFace: el cache local retiene archivos completos, `from_pretrained()` no re-descarga archivos que ya están
   - **No se pierde progreso significativo** — esto hay que comunicarlo al usuario

5. **Logs**: Cada fase ya hace `logger.info()`. El problema es que el frontend no ve estos logs. Se podría exponer un endpoint `/api/logs/tail?n=5` o incluir el último log message en el objeto de progreso.

**Sobre compatibilidad Win/Mac**:
> "`Path.home() / '.cache' / 'huggingface'` funciona en ambos: `C:\Users\user\.cache\huggingface` en Windows y `~/.cache/huggingface` en macOS. El monitor de descarga ya usa `Path.home()`, así que es compatible. Lo que hay que vigilar es que `spacy.cli.download()` en macOS con venv puede requerir permisos diferentes que en Windows con Anaconda embebido."

### FRONTEND ENGINEER

> "El componente `ModelSetupDialog.vue` tiene toda la lógica de progreso real implementada: barras determinadas, velocidad, bytes, ETA. El problema es que el backend solo manda datos reales para embeddings. Si el backend mandara `bytes_downloaded` actualizados para los 3 modelos, la UI ya los mostraría sin cambios."

**Puntos clave FE**:
1. `isModelCompleted()` y `isModelDownloading()` están hardcodeados a `'spacy'` | `'embeddings'` — hay que hacerlos dinámicos
2. `currentModel` computed solo tiene textos para spaCy y embeddings — falta transformer_ner
3. `model_sizes` del endpoint progress solo devuelve spacy + embeddings
4. La lógica de `realProgress` ya combina todos los modelos activos, así que si el backend reporta 3, el frontend ya funciona

**Sobre mensajes rotativos**:
> "De acuerdo en que deben reflejar lo que realmente pasa. Propuesta: en vez de mensajes rotativos genéricos, mostrar el `phase` real del backend traducido a lenguaje humano. Si el backend dice `downloading`, mostrar 'Descargando...'. Si dice `installing`, mostrar 'Instalando...'. No decir 'Configurando...' si estamos descargando."

### UX DESIGNER

> "La clave es que **todo lo que se muestra sea verdad**. No mensajes rotativos inventados. Si estamos descargando, decir 'Descargando'. Si hay datos de progreso, mostrarlos. Si no los hay, mostrar la barra indeterminada pero con un mensaje claro que diga qué componente se está descargando."

**Propuesta de UI revisada**:

#### A. Nombres orientados a función

| Actual (técnico) | Propuesta (funcional) |
|------------------|----------------------|
| spaCy Español (es_core_news_lg) | Análisis gramatical y lingüístico |
| Sentence Transformers Multilingüe | Análisis de similitud y contexto |
| PlanTL RoBERTa NER (español) | Reconocimiento de personajes y lugares |

#### B. Mostrar todos los modelos, siempre

Incluso los ya instalados. Orden de instalación de arriba a abajo:

```
Configuración inicial

Descargando componentes de análisis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45%

Componente 2 de 3

  ✓  Análisis gramatical                ~540 MB   Instalado
  ›  Análisis de similitud              ~470 MB   Descargando... 234 MB  2.1 MB/s
     Reconocimiento de entidades         ~500 MB   Pendiente

  ℹ  Esta descarga solo se realiza una vez. Tamaño total: ~1.5 GB
```

Si un componente no tiene progreso granular (barra indeterminada):

```
  ›  Análisis gramatical                ~540 MB   Descargando...
```

Sin barra infinita adicional ni spinner — la barra global ya está animada. El texto "Descargando..." con puntos suspensivos basta.

#### C. Mensajes reales, no rotativos

| Fase backend | Mensaje en UI |
|-------------|---------------|
| `connecting` | Conectando... |
| `downloading` | Descargando... (+ bytes si hay datos) |
| `installing` | Instalando... |
| `completed` | Instalado |
| `error` | Error (con botón reintentar) |

No inventar fases. No decir "Configurando" si estamos descargando. No decir "Preparando componentes" si estamos esperando conexión.

#### D. Si no hay spinner, no hace falta barra infinita

Si la barra global tiene datos reales (al menos un modelo con bytes), mostrar barra determinada. Si ningún modelo tiene bytes todavía, mostrar barra indeterminada. No ambas a la vez. No spinner + barra infinita: redundante.

---

## 3. Decisiones

### 3.1 ¿Descargar todo al inicio?

**DECISIÓN: SÍ.** Los 3 modelos se descargan en la configuración inicial.

**Argumentos a favor** (consenso unánime):
- Evita sorpresas al usuario durante el primer análisis
- El tiempo total (~5-8 min con buena conexión) es aceptable para un proceso que solo ocurre una vez
- Muestra 1.5 GB como total honesto, no 1 GB que luego son 1.5 GB
- Mejor UX: "todo listo" significa realmente todo listo

### 3.2 ¿Descargas en paralelo?

**DECISIÓN: 2 en paralelo, máximo.**

- **spaCy + Embeddings en paralelo** (servidores distintos: GitHub vs HuggingFace)
- **Transformer NER después de Embeddings** (mismo servidor HuggingFace)
- Beneficio estimado: ~30% menos tiempo total
- En conexiones muy lentas (< 5 Mbps), el paralelismo no ayuda y puede perjudicar

### 3.3 ¿Mostrar modelos ya instalados?

**DECISIÓN: SÍ.** Mostrar todos con estado: ✓ Instalado / › Descargando / ○ Pendiente.

El usuario ve el progreso completo y sabe exactamente dónde está.

### 3.4 ¿Mensajes rotativos?

**DECISIÓN: NO.** Mostrar el estado real traducido a lenguaje humano. Si no hay datos de progreso, mostrar "Descargando..." y nada más. No inventar actividad ficticia.

---

## 4. Plan de Acción

### Fase 1: Backend — Datos correctos y completos

| # | Tarea | Archivo(s) | Detalle |
|---|-------|------------|---------|
| 1.1 | Incluir transformer_ner en descarga inicial | `system.py`, `deps.py` | Añadir caso `"transformer_ner"` en `download_task()`. Cambiar default a `["spacy", "embeddings", "transformer_ner"]` |
| 1.2 | Añadir monitor de progreso a transformer_ner | `model_manager.py` | Reutilizar patrón de `_monitor_hf_download()` para transformer_ner (mismo mecanismo: escanear cache HF) |
| 1.3 | Añadir monitor de progreso a spaCy | `model_manager.py` | Monitorear directorio destino durante `spacy.cli.download()`, o el cache pip, para tener algún dato de bytes |
| 1.4 | Incluir los 3 modelos en model_sizes del progress | `system.py` | Endpoint `/api/models/download/progress` debe devolver los 3 modelos en `model_sizes` |
| 1.5 | Renombrar display_name a nombres funcionales | `model_manager.py` | Cambiar en `KNOWN_MODELS` los 3 `display_name` |
| 1.6 | Verificar y fijar tamaños reales | `model_manager.py` | Consultar HuggingFace una vez, fijar `size_mb` con valores verificados |
| 1.7 | Paralelizar: spaCy + primer HF modelo | `system.py` | Usar `ThreadPoolExecutor(max_workers=2)` en `download_task()` |

### Fase 2: Frontend — UI que refleja la realidad

| # | Tarea | Archivo(s) | Detalle |
|---|-------|------------|---------|
| 2.1 | Hacer mapeo de modelos dinámico | `ModelSetupDialog.vue` | Eliminar hardcode en `isModelCompleted`/`isModelDownloading`. Usar `model.type` del backend |
| 2.2 | Añadir textos para transformer_ner | `ModelSetupDialog.vue` | En `currentModel` computed, añadir caso para `transformer_ner` |
| 2.3 | Mostrar todos los modelos (instalados y pendientes) | `ModelSetupDialog.vue` | Lista completa con estado ✓/›/○, no solo los `missingModels` |
| 2.4 | Añadir indicador "Componente X de N" | `ModelSetupDialog.vue` | Calcular desde la lista de modelos y el progreso actual |
| 2.5 | Mostrar ETA cuando hay datos de velocidad | `ModelSetupDialog.vue` | El backend ya calcula `eta_seconds`, solo falta mostrarlo |
| 2.6 | Mensajes de estado reales | `ModelSetupDialog.vue` | Traducir `phase` a texto humano. No mensajes rotativos inventados |

### Fase 3: Robustez

| # | Tarea | Detalle |
|---|-------|---------|
| 3.1 | Verificar compatibilidad macOS | Cache paths, permisos de pip, spaCy CLI con venv |
| 3.2 | Mejorar error con acción clara | Botón reintentar + texto amigable + mención de que no se pierde progreso |
| 3.3 | Test E2E del flujo completo | Los 3 modelos se descargan, progreso funciona, diálogo se cierra |
| 3.4 | Verificar reiniciabilidad | Cerrar app a mitad → reabrir → continúa sin re-descargar |

---

## 5. Resumen de Problemas por Prioridad

| Prioridad | Problema | Impacto | Fase |
|-----------|----------|---------|------|
| **CRÍTICO** | 2 de 3 modelos no reportan progreso real | La barra parece colgada; el usuario no sabe si funciona | 1.2, 1.3 |
| **CRÍTICO** | transformer_ner no se descarga al inicio | Sorpresa de 5 min durante el primer análisis | 1.1 |
| **ALTO** | Nombres técnicos en display_name | El usuario no entiende qué descarga | 1.5 |
| **ALTO** | Frontend hardcodeado a 2 modelos | El tercer modelo no se muestra correctamente | 2.1, 2.2 |
| **MEDIO** | Solo muestra modelos no instalados | No se ve progreso completo (qué ya se hizo, qué falta) | 2.3 |
| **MEDIO** | Sin indicador de paso (1/3, 2/3) | Desorientación sobre cuánto falta | 2.4 |
| **MEDIO** | Descargas secuenciales | Tiempo total innecesariamente largo | 1.7 |
| **BAJO** | ETA no visible en UI | Los datos existen en el backend pero no se muestran | 2.5 |
