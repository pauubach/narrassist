# Matriz de Tipos de Documento y Features

> Documento de diseño para el sistema de perfiles de features según tipo de manuscrito.
>
> **Fecha**: Enero 2026
> **Estado**: Revisado tras debate con expertos

---

## 1. Clasificación de Tipos de Documento

### 1.1 Categorías Principales (13 tipos)

| ID | Categoría | Descripción | Ejemplos |
|----|-----------|-------------|----------|
| `FIC` | **Ficción Narrativa** | Obras de ficción con trama, personajes y estructura narrativa | Novela, Cuento, Thriller, Romance, Fantasía, Sci-Fi |
| `MEM` | **Memorias y Autobiográfico** | Narrativa personal basada en hechos reales | Memorias, Autobiografía, Diario personal |
| `BIO` | **Biografía** | Narrativa sobre personas/eventos reales | Biografía novelada, Biografía documental, Periodismo narrativo |
| `CEL` | **Celebridad/Influencer** | Libros de famosos, YouTubers, TikTokers | Libros de ElRubius, TheGrefg, deportistas, famosos |
| `DIV` | **Divulgación** | Conocimiento accesible al público general | Divulgación científica, histórica, social (Harari, Sagan) |
| `ENS` | **Ensayo y Pensamiento** | Exposición argumentativa de ideas | Ensayo narrativo, académico, filosófico, político |
| `AUT` | **Autoayuda y Desarrollo** | Orientado a transformación personal | Práctico (pasos), Narrativo (historias), Espiritual |
| `TEC` | **Técnico y Referencia** | Información estructurada y sistemática | Manual técnico, Documentación, Libro de texto |
| `PRA` | **Práctico y Guías** | Instrucciones paso a paso | Cocina, Manualidades, Fitness, DIY, Guías de viaje |
| `GRA` | **Gráfico** | Obras con componente visual predominante | Cómic, Novela gráfica, Manga |
| `INF` | **Infantil y Juvenil** | Adaptado a lectores jóvenes (ver subtipos por edad) | Board book, Álbum ilustrado, Middle grade, YA |
| `POE` | **Poesía** | Obras en verso o prosa poética | Poemario, Antología (baja prioridad) |
| `DRA` | **Dramático y Guión** | Obras para representación | Teatro, Guión de cine/TV |

### 1.2 Subtipos por Categoría

```
FIC (Ficción Narrativa)
├── FIC_NOV    Novela general
├── FIC_COR    Cuento/Relato corto
├── FIC_THR    Thriller/Suspense
├── FIC_ROM    Romance
├── FIC_FAN    Fantasía
├── FIC_SCI    Ciencia ficción
├── FIC_HIS    Ficción histórica
└── FIC_LIT    Ficción literaria

MEM (Memorias)
├── MEM_AUT    Autobiografía completa
├── MEM_DIA    Diario/Journal
├── MEM_CAR    Epistolario/Cartas
└── MEM_CRO    Crónica personal

BIO (Biografía)
├── BIO_NOV    Biografía novelada (features narrativas completas)
├── BIO_DOC    Biografía documental (features limitadas)
├── BIO_PER    Periodismo narrativo
└── BIO_HIS    Crónica histórica

CEL (Celebridad/Influencer) - NUEVO
├── CEL_YTB    YouTuber/Streamer
├── CEL_TIK    TikToker/Influencer social
├── CEL_FAM    Famoso/Celebridad tradicional
├── CEL_DEP    Deportista
└── CEL_MUS    Músico/Artista

DIV (Divulgación) - NUEVO
├── DIV_CIE    Divulgación científica
├── DIV_HIS    Divulgación histórica
├── DIV_SOC    Divulgación social/política
└── DIV_TEC    Divulgación tecnológica

ENS (Ensayo)
├── ENS_NAR    Ensayo narrativo (puede tener escenas)
├── ENS_ACA    Ensayo académico
├── ENS_FIL    Ensayo filosófico
└── ENS_POL    Ensayo político/Opinión

AUT (Autoayuda)
├── AUT_PRA    Práctico/Manual (pasos, ejercicios)
├── AUT_NAR    Narrativo (historias de superación)
├── AUT_ESP    Espiritual/Mindfulness
└── AUT_PRO    Productividad/Negocio

TEC (Técnico)
├── TEC_MAN    Manual técnico
├── TEC_DOC    Documentación
├── TEC_TXT    Libro de texto
└── TEC_REF    Referencia/Enciclopedia

PRA (Práctico)
├── PRA_COC    Cocina/Recetas
├── PRA_MAN    Manualidades/Crafts
├── PRA_FIT    Fitness/Bienestar
├── PRA_JAR    Jardinería
├── PRA_DIY    Bricolaje
└── PRA_VIA    Guías de viaje

GRA (Gráfico) - NUEVO
├── GRA_COM    Cómic
├── GRA_NOV    Novela gráfica
├── GRA_MAN    Manga
└── GRA_ALB    Álbum ilustrado adulto

INF (Infantil/Juvenil) - Por rango de edad
├── INF_BB     Board book (0-3 años)
├── INF_PB     Picture book / Álbum ilustrado (3-5 años)
├── INF_ER     Early reader (5-8 años)
├── INF_CB     Chapter book (6-10 años)
├── INF_MG     Middle grade (8-12 años)
└── INF_YA     Young Adult (12+ años)

DRA (Dramático)
├── DRA_TEA    Teatro
├── DRA_CIN    Guión de cine
├── DRA_TV     Guión de TV/Serie
└── DRA_POD    Podcast narrativo/Audio drama
```

### 1.3 Infantil: Especificaciones por Rango de Edad

| Subtipo | Edad | Palabras | Páginas | Características | Métricas especiales |
|---------|------|----------|---------|-----------------|---------------------|
| `INF_BB` | 0-3 | <300 | 12-20 | Board book, conceptos simples, alto contraste | Vocabulario básico, repetición |
| `INF_PB` | 3-5 | 500-1000 | 32 | Álbum ilustrado, rimas, texto-imagen | Sílabas por palabra, rimas |
| `INF_ER` | 5-8 | 1000-5000 | 32-64 | Early reader, vocabulario controlado, niveles | Sight words, longitud oracional |
| `INF_CB` | 6-10 | 5000-15000 | 60-100 | Chapter book, capítulos cortos, series | Complejidad sintáctica básica |
| `INF_MG` | 8-12 | 20000-50000 | 150-300 | Middle grade, subtramas, desarrollo personajes | Flesch-Kincaid adaptado |
| `INF_YA` | 12+ | 40000-80000 | 200-400 | Young adult, temas maduros, complejidad | Métricas estándar de ficción |

---

## 2. Features del Sistema

### 2.1 Catálogo de Features

| ID | Feature | Descripción | Módulo Backend |
|----|---------|-------------|----------------|
| `ENT` | **Entidades (NER)** | Extracción de personajes, lugares, objetos | `nlp/ner.py` |
| `REL` | **Relaciones** | Relaciones entre entidades | `analysis/relationships.py` |
| `TIM` | **Timeline** | Línea temporal de eventos | `temporal/timeline.py` |
| `SCE` | **Escenas** | Detección y etiquetado de escenas | `scenes/service.py` |
| `FOC` | **Focalización** | Punto de vista y violaciones | `focalization/` |
| `DIA` | **Diálogos** | Atribución y análisis de diálogos | `voice/speaker_attribution.py` |
| `PAC` | **Pacing** | Ritmo narrativo | `analysis/pacing.py` |
| `EMO` | **Emociones** | Arcos emocionales y coherencia | `analysis/emotional_coherence.py` |
| `REG` | **Registro** | Análisis de registro narrativo | `nlp/register_analyzer.py` |
| `REP` | **Repeticiones** | Detección de ecos léxicos | `nlp/style/repetition_detector.py` |
| `STK` | **Sticky Sentences** | Oraciones pesadas | `nlp/style/sticky_sentences.py` |
| `VAR` | **Variación** | Longitud de oraciones | `nlp/style/readability.py` |
| `VOZ` | **Perfiles de Voz** | Voz distintiva por personaje | `voice/voice_profiles.py` |
| `CON` | **Consistencia** | Atributos de personajes | `analysis/attribute_consistency.py` |
| `GLO` | **Glosario** | Términos y definiciones | `glossary/` |
| `STY` | **Guía de Estilo** | Normas editoriales | `style_guide/` |
| `COR` | **Correctores** | Detectores de errores | `corrections/` |
| `LEG` | **Legibilidad por Edad** | Métricas específicas infantil | `nlp/style/readability.py` |

---

## 3. Matriz de Features por Tipo de Documento

### 3.1 Matriz Principal

| Feature | FIC | MEM | BIO | CEL | DIV | ENS | AUT | TEC | PRA | GRA | INF | DRA |
|---------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| `ENT` Entidades | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ✅ | ✅ | ✅ |
| `REL` Relaciones | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| `TIM` Timeline | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ | ✅ |
| `SCE` Escenas | ✅ | ✅ | ⚠️° | ⚠️ | ❌ | ⚠️° | ❌ | ❌ | ❌ | ✅ | ⚠️ | ✅ |
| `FOC` Focalización | ✅ | ✅ | ⚠️° | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ | ⚠️ |
| `DIA` Diálogos | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ❌ | ⚠️ | ❌ | ❌ | ✅ | ✅ | ✅ |
| `PAC` Pacing | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ✅ | ✅ | ✅ |
| `EMO` Emociones | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| `REG` Registro | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ |
| `REP` Repeticiones | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ |
| `STK` Sticky | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ |
| `VAR` Variación | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ |
| `VOZ` Perfiles voz | ✅ | ⚠️ | ⚠️ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| `CON` Consistencia | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| `GLO` Glosario | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `STY` Guía estilo | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `COR` Correctores | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `LEG` Legibilidad edad | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |

**Leyenda**:
- ✅ = Siempre disponible y relevante
- ⚠️ = Disponible pero uso limitado/opcional
- ⚠️° = Depende del subtipo (ej: BIO_NOV sí, BIO_DOC no)
- ❌ = No relevante, ocultar por defecto

### 3.2 Variaciones por Subtipo

#### Biografía (BIO)
| Feature | BIO_NOV (novelada) | BIO_DOC (documental) | BIO_PER (periodismo) |
|---------|-------------------|---------------------|---------------------|
| Escenas | ✅ | ❌ | ⚠️ |
| Focalización | ✅ | ❌ | ⚠️ |
| Timeline | ✅ | ✅ | ✅ |
| Diálogos | ✅ (reconstruidos) | ⚠️ (citados) | ✅ |

#### Ensayo (ENS)
| Feature | ENS_NAR (narrativo) | ENS_ACA (académico) | ENS_POL (político) |
|---------|--------------------|--------------------|-------------------|
| Escenas | ⚠️ (anécdotas) | ❌ | ⚠️ |
| Timeline | ⚠️ | ❌ | ⚠️ |
| Emociones | ✅ | ⚠️ | ✅ |

#### Autoayuda (AUT)
| Feature | AUT_PRA (práctico) | AUT_NAR (narrativo) | AUT_ESP (espiritual) |
|---------|-------------------|--------------------|--------------------|
| Escenas | ❌ | ✅ | ⚠️ |
| Diálogos | ⚠️ (ejemplos) | ✅ | ⚠️ |
| Emociones | ⚠️ | ✅ | ✅ |

#### Infantil (INF) - Por edad
| Feature | INF_BB/PB (0-5) | INF_ER/CB (5-10) | INF_MG (8-12) | INF_YA (12+) |
|---------|-----------------|------------------|---------------|--------------|
| Entidades | ⚠️ (simples) | ✅ | ✅ | ✅ |
| Escenas | ❌ | ⚠️ | ✅ | ✅ |
| Focalización | ❌ | ⚠️ | ✅ | ✅ |
| Complejidad | Muy baja | Baja | Media | Alta |
| Métricas edad | ✅ Crítico | ✅ Crítico | ✅ | ⚠️ |

---

## 4. Debate de Expertos (Resumen)

### Participantes
- **Elena** - Editora senior (20 años en editorial tradicional)
- **Carlos** - Corrector profesional (ficción y no-ficción)
- **Marta** - Escritora (novela, autoayuda, libros infantiles)
- **Jorge** - Editor de contenido digital (libros de influencers)

### Conclusiones del debate

1. **Libros de influencers (CEL)** son categoría propia - híbridos con anécdotas, consejos, contenido interactivo. Necesitan consistencia de voz pero no timeline narrativo.

2. **Divulgación (DIV)** es diferente de ensayo y de técnico - tiene narrativa basada en datos (Harari, Sagan).

3. **Cómic/Novela gráfica (GRA)** requiere análisis diferente - visual, diálogos en bocadillos, ritmo por viñetas.

4. **Biografías** deben distinguir:
   - Novelada → features narrativas completas
   - Documental → features limitadas

5. **Ensayos** varían:
   - Narrativo (Montaigne) → puede tener escenas
   - Académico → sin elementos narrativos

6. **Autoayuda** tiene dos tipos:
   - Práctico (ejercicios, pasos)
   - Narrativo (historias de superación)

7. **Infantil** requiere métricas por edad obligatorias, no opcionales.

---

## 5. Implementación en el Sistema

### 5.1 Almacenamiento del Tipo de Documento

```sql
-- Modificar tabla projects (migración)
ALTER TABLE projects ADD COLUMN document_type TEXT DEFAULT 'FIC';
ALTER TABLE projects ADD COLUMN document_subtype TEXT;
ALTER TABLE projects ADD COLUMN document_type_confirmed INTEGER DEFAULT 0;
-- document_type_confirmed: 0 = sugerido por sistema, 1 = confirmado por usuario
```

### 5.2 Modelo de Datos

```python
from enum import Enum
from dataclasses import dataclass

class DocumentType(str, Enum):
    FICTION = "FIC"
    MEMOIR = "MEM"
    BIOGRAPHY = "BIO"
    CELEBRITY = "CEL"
    DIVULGATION = "DIV"
    ESSAY = "ENS"
    SELFHELP = "AUT"
    TECHNICAL = "TEC"
    PRACTICAL = "PRA"
    GRAPHIC = "GRA"
    CHILDREN = "INF"
    POETRY = "POE"
    DRAMATIC = "DRA"

class FeatureAvailability(str, Enum):
    ENABLED = "enabled"      # ✅ Siempre visible y activo
    OPTIONAL = "optional"    # ⚠️ Disponible pero secundario
    DISABLED = "disabled"    # ❌ Oculto por defecto

@dataclass
class FeatureProfile:
    """Perfil de features para un tipo de documento."""
    document_type: DocumentType
    document_subtype: str | None
    features: dict[str, FeatureAvailability]

    # Métricas específicas
    target_age_range: tuple[int, int] | None = None  # Para infantil
    max_word_count: int | None = None
    recommended_sentence_length: tuple[int, int] | None = None
```

### 5.3 API Endpoints

```
# Obtener perfil de features
GET /api/projects/{id}/feature-profile

# Cambiar tipo de documento
PUT /api/projects/{id}/document-type
Body: { "document_type": "FIC", "document_subtype": "FIC_THR" }

# Obtener tipos disponibles
GET /api/document-types
```

**Respuesta de `/api/projects/{id}/feature-profile`:**
```json
{
  "project_id": 123,
  "document_type": "FIC",
  "document_subtype": "FIC_THR",
  "document_type_confirmed": true,
  "features": {
    "entities": "enabled",
    "relations": "enabled",
    "timeline": "enabled",
    "scenes": "enabled",
    "focalization": "enabled",
    "dialogues": "enabled",
    "pacing": "enabled",
    "emotions": "enabled",
    "register": "enabled",
    "repetitions": "enabled",
    "sticky": "enabled",
    "variation": "enabled",
    "voices": "enabled",
    "consistency": "enabled",
    "glossary": "enabled",
    "style_guide": "enabled",
    "corrections": "enabled",
    "age_readability": "disabled"
  },
  "metrics": {
    "target_age_range": null,
    "max_word_count": null,
    "recommended_sentence_length": [15, 25]
  }
}
```

### 5.4 Frontend - Selector de Tipo

El usuario podrá cambiar el tipo de documento desde:
1. **Configuración del proyecto** (Settings)
2. **Banner informativo** si el sistema detecta discrepancia

```vue
<!-- Ejemplo de selector -->
<Dropdown
  v-model="documentType"
  :options="documentTypes"
  optionLabel="label"
  optionValue="value"
  placeholder="Tipo de documento"
/>
<Dropdown
  v-if="subtypesAvailable"
  v-model="documentSubtype"
  :options="availableSubtypes"
  optionLabel="label"
  optionValue="value"
  placeholder="Subtipo (opcional)"
/>
```

### 5.5 Frontend - Tabs Condicionales

```vue
<template>
  <!-- Tabs que dependen del perfil -->
  <TabPanel v-if="profile.features.scenes !== 'disabled'" value="scenes">
    <SceneTaggingTab v-if="profile.features.scenes === 'enabled'" />
    <OptionalFeatureHint
      v-else
      feature="Escenas"
      @enable="enableFeature('scenes')"
    />
  </TabPanel>

  <!-- Tab de legibilidad por edad (solo infantil) -->
  <TabPanel v-if="profile.features.age_readability === 'enabled'" value="readability">
    <AgeReadabilityTab :target-age="profile.metrics.target_age_range" />
  </TabPanel>
</template>
```

---

## 6. Próximos Pasos de Implementación

1. **Inmediato**: ✅ COMPLETADO
   - [x] Añadir campos `document_type`, `document_subtype`, `document_type_confirmed` a tabla `projects`
   - [x] Crear endpoint `GET /api/document-types` con catálogo
   - [x] Crear endpoint `PUT /api/projects/{id}/document-type`

2. **Corto plazo**: ✅ COMPLETADO
   - [x] Crear `FeatureProfile` y `FeatureProfileService` en backend
   - [x] Crear endpoint `GET /api/projects/{id}/feature-profile`
   - [x] Añadir selector de tipo en configuración de proyecto (frontend) → `DocumentTypeChip.vue`

3. **Medio plazo**: ✅ COMPLETADO
   - [x] Adaptar todos los tabs del workspace para usar perfil → `useFeatureProfile.ts` + `StyleTab.vue`
   - [x] Implementar métricas de legibilidad por edad para infantil → `AgeReadabilityTab.vue` + endpoint `/api/projects/{id}/age-readability`
   - [x] Crear sugerencia automática de tipo basada en análisis → `detect_document_type()` básico

4. **Largo plazo**: ⚠️ PARCIAL
   - [x] Detección automática de tipo de documento (heurísticas básicas implementadas)
   - [ ] Métricas específicas para cada subtipo (PENDIENTE)

---

## 7. Referencias

- [Géneros Literarios - EditaTuLibro](https://editatulibro.net/generos-literarios/)
- [WMagazín - Mejores libros 2025](https://wmagazin.com/relatos/los-50-mejores-libros-del-ano-2025-de-wmagazin-por-generos-literarios/)
- [Libros de YouTubers - Esquire](https://www.esquire.com/es/actualidad/libros/g38505779/mejores-libros-youtubers/)
- [Children's Book Age Groups - Mary Kole](https://www.marykole.com/childrens-book-age-groups)
- [Book Riot - Children's Categories](https://bookriot.com/childrens-book-categories/)
- [Complete Statistics on Biographies - Meminto](https://meminto.com/blog/complete-statistics-on-biographies-and-personal-stories-for-2025/)

---

*Documento actualizado: 26 Enero 2026*
*Revisado tras debate con expertos editoriales*
