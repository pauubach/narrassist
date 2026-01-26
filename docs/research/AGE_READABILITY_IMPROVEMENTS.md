# Mejoras Futuras - Legibilidad por Edad (INF)

> Documento de análisis de posibles mejoras para el sistema de legibilidad por edad para literatura infantil/juvenil.

---

## Estado Actual

El sistema `age_readability` está implementado en:
- **Backend**: `src/narrative_assistant/nlp/style/readability.py` → `analyze_for_age()`
- **Frontend**: `frontend/src/components/workspace/AgeReadabilityTab.vue`
- **API**: `/api/projects/{id}/age-readability`
- **Feature Profile**: Solo habilitado para documentos tipo `CHILDREN` (INF)

### Funcionalidades Actuales

1. **Estimación de grupo de edad**: Board book → Young Adult
2. **Métricas de complejidad**:
   - Promedio de palabras por oración
   - Promedio de sílabas por palabra
   - Ratio de palabras de alta frecuencia (sight words)
   - Índice Flesch-Szigriszt adaptado
3. **Análisis por capítulo**: Desglose capítulo a capítulo
4. **Comparación con umbrales**: Por grupo de edad objetivo

---

## ⚠️ Integración con Sistema de Alertas

**Estado actual**: NO conectado al sistema de alertas.

### Propuesta de Integración

Crear método `create_from_age_readability_issue()` en `AlertEngine`:

```python
# Posibles tipos de alerta
AlertCategory.AGE_READABILITY = "age_readability"  # Nueva categoría

# Alertas propuestas:
- age_complexity_high: "Texto demasiado complejo para grupo de edad objetivo"
- age_vocabulary_advanced: "Vocabulario avanzado para la edad objetivo"
- age_sentence_length: "Oraciones demasiado largas para lectores tempranos"
- age_sight_words_low: "Porcentaje bajo de palabras de alta frecuencia"
```

**Severidad**:
- `WARNING`: Si el texto está claramente fuera del rango objetivo
- `INFO`: Si está en el límite del rango
- `HINT`: Sugerencias de mejora opcionales

**Prioridad**: Media - Depende de demanda de usuarios

---

## 📋 Mejoras Propuestas por Expertos

### 1. Detección de Rimas y Ritmo

**Descripción**: Análisis de patrones rítmicos y rimas, crucial para picture books y poesía infantil.

**Implementación propuesta**:
```python
class RhymeDetector:
    def detect_rhyme_scheme(self, text: str) -> RhymeReport
    def analyze_rhythm(self, text: str) -> RhythmReport
    def check_consistency(self, verses: list[str]) -> ConsistencyReport
```

**Métricas**:
- Esquema de rima (ABAB, AABB, etc.)
- Consistencia rítmica
- Sílabas por verso (métrica)
- Rimas consonantes vs asonantes

**⚠️ NOTA IMPORTANTE**: Si se implementa detección de rimas, se debe desarrollar también para documentos tipo **POETRY (POE)** para aprovechar el módulo. Ver sección "Sinergia con Poesía".

**Prioridad**: Baja (no prioritario según usuario)

---

### 2. Vocabulario Controlado por Edad

**Descripción**: Diccionarios de vocabulario apropiado por grupo de edad, basados en currículos educativos españoles.

**Implementación propuesta**:
- Diccionario de palabras por nivel (basado en currículum escolar español)
- Detección de palabras fuera de vocabulario esperado
- Sugerencias de sinónimos más simples

**Fuentes de datos**:
- Vocabulario básico escolar (REAL ACADEMIA ESPAÑOLA)
- Listas de frecuencia del español (CREA/CORPES)
- Currículum de Lengua Castellana por nivel

**Métricas**:
- % de palabras dentro del vocabulario controlado
- Palabras fuera de rango con sugerencias
- Complejidad morfológica (prefijos, sufijos)

**Prioridad**: Media

---

### 3. Análisis de Diálogos Infantiles

**Descripción**: Verificar que los diálogos de personajes infantiles sean naturales y apropiados.

**Casos de uso**:
- Niños que hablan como adultos (antinatural)
- Expresiones demasiado formales para la edad del personaje
- Vocabulario inconsistente con la edad del personaje

**Integración**: Con sistema de Voice Profiles existente (`voice_profiles.py`)

**Prioridad**: Media

---

### 4. Advertencias de Contenido/Temas

**Descripción**: Detección de temas potencialmente inapropiados para la edad objetivo.

**Categorías**:
- Violencia (niveles: ninguna, leve, moderada)
- Miedo/terror (apropiado por edad)
- Temas familiares complejos (divorcio, muerte)
- Contenido sexual (inapropiado para menores)

**Implementación**:
- Listas de palabras clave por categoría
- Análisis de contexto para reducir falsos positivos
- Configuración de sensibilidad por usuario

**Integración con alertas**: Sí, `AlertCategory.CONTENT_WARNING`

**Prioridad**: Media-Alta para editoriales infantiles

---

### 5. Ratio Texto/Ilustración

**Descripción**: Sugerencias sobre densidad de texto apropiada para el formato.

| Formato | Palabras/página | Ratio texto/ilustración |
|---------|-----------------|-------------------------|
| Board book | 5-20 | 20/80 |
| Picture book | 20-50 | 30/70 |
| Early reader | 50-100 | 50/50 |
| Chapter book | 100-200 | 70/30 |

**Implementación**:
- Cálculo de palabras por "página lógica"
- Comparación con estándares del mercado
- Sugerencias de corte/división

**Limitación**: Requiere información de maquetación (no disponible en DOCX sin estilos)

**Prioridad**: Baja

---

### 6. Análisis de Repetición Pedagógica

**Descripción**: En libros para lectores tempranos, la repetición es positiva (refuerzo).

**Diferencia con EchoReport**:
- EchoReport detecta repeticiones como problema de estilo
- Esta feature detecta repeticiones como técnica pedagógica

**Patrones a detectar**:
- Estructuras repetitivas ("Primero... Luego... Después...")
- Estribillos y patrones recurrentes
- Vocabulario repetido intencionalmente

**Prioridad**: Baja

---

## 🔗 Sinergia con Poesía (POE)

Si se implementa el módulo de detección de rimas para literatura infantil, se debería extender para documentos de tipo **POETRY (POE)** con funcionalidades adicionales:

### Features compartidas (INF + POE):
- Detección de esquemas de rima
- Análisis de métrica (sílabas por verso)
- Consistencia rítmica

### Features exclusivas de POE:
- Tipos de estrofa (soneto, romance, verso libre, etc.)
- Licencias poéticas (sinalefa, hiato, diéresis, sinéresis)
- Figuras retóricas (aliteración, anáfora, etc.)
- Rima perfecta vs imperfecta
- Análisis de cesura y hemistiquios

### Implementación sugerida:
```
src/narrative_assistant/nlp/style/
├── rhyme_detector.py      # Compartido INF + POE
├── rhythm_analyzer.py     # Compartido INF + POE
└── poetry_analyzer.py     # Exclusivo POE (estrofas, figuras)
```

### Feature Profile:
```python
# En models.py
rhyme_analysis: FeatureAvailability  # Habilitado para INF y POE
poetry_metrics: FeatureAvailability  # Solo POE
```

---

## 📊 Matriz de Prioridades

| Mejora | Complejidad | Impacto | Prioridad | Dependencias |
|--------|-------------|---------|-----------|--------------|
| Integración alertas | Baja | Alto | **Alta** | - |
| Vocabulario controlado | Media | Alto | **Media** | Diccionarios |
| Diálogos infantiles | Media | Medio | **Media** | Voice Profiles |
| Advertencias contenido | Media | Alto | **Media-Alta** | - |
| Detección rimas | Alta | Medio | **Baja** | POE features |
| Ratio texto/ilustración | Baja | Bajo | **Baja** | Maquetación |
| Repetición pedagógica | Media | Bajo | **Baja** | - |

---

## 🎯 Recomendación de Implementación

### Fase 1 (Corto plazo):
1. Integrar con sistema de alertas (crear `AlertCategory.AGE_READABILITY`)
2. Añadir advertencias cuando texto excede umbrales

### Fase 2 (Medio plazo):
1. Vocabulario controlado por edad (diccionarios educativos)
2. Advertencias de contenido básicas

### Fase 3 (Largo plazo, si hay demanda):
1. Detección de rimas → desarrollar junto con POE
2. Análisis de diálogos infantiles
3. Repetición pedagógica

---

*Documento creado: 26 Enero 2026*
*Última actualización: 26 Enero 2026*
