# Revisión UX: Selector de Tipo de Documento

**Fecha**: 2026-01-28
**Estado**: En revisión

---

## Resumen de Preguntas del Usuario

| # | Pregunta | Respuesta corta |
|---|----------|-----------------|
| 1 | ¿Por qué hay cuadrados de colores? | Son iconos PrimeVue con color por tipo |
| 2 | Dice "Sin confirmar". ¿Cómo confirmo? | Al seleccionar cualquier tipo |
| 3 | ¿Se puede detectar el subtipo automáticamente? | No implementado actualmente |
| 4 | Inconsistencia perfiles corrección vs tipos | Sistemas diferentes que deberían alinearse |
| 5 | "Por defecto" vs "General" | Son conceptos distintos pero confusos |
| 6 | ¿Dónde se cambian los defaults? | Ver sección específica |

---

## 1. ¿Por qué hay cuadrados de colores delante de cada tipo?

**Respuesta**: Son **iconos PrimeVue** (`pi-book`, `pi-heart`, etc.) con colores distintivos para cada tipo de documento.

### Ubicación del código

**Archivo**: [frontend/src/components/DocumentTypeChip.vue:49](frontend/src/components/DocumentTypeChip.vue#L49)
```vue
<i :class="type.icon" :style="{ color: type.color }"></i>
```

**Definición de iconos y colores**: [src/narrative_assistant/feature_profile/models.py:34-107](src/narrative_assistant/feature_profile/models.py#L34-L107)
```python
DOCUMENT_TYPES = {
    DocumentType.FICTION: {
        "icon": "pi-book",
        "color": "#6366f1",  # Indigo
    },
    DocumentType.MEMOIR: {
        "icon": "pi-heart",
        "color": "#ec4899",  # Pink
    },
    # ... etc
}
```

### Problema UX identificado

Los iconos aparecen como pequeños cuadrados si:
1. La fuente de iconos de PrimeVue no carga
2. El CSS no tiene los estilos correctos

**Recomendación**: Verificar que los iconos se renderizan correctamente en todos los navegadores.

---

## 2. Dice "Sin confirmar". ¿Cómo confirmo el tipo de documento?

**Respuesta**: El tipo se **confirma automáticamente** cuando el usuario **selecciona cualquier tipo** del menú desplegable.

### Flujo de confirmación

1. El sistema detecta un tipo automáticamente (ej: "Ficción narrativa")
2. Aparece "Sin confirmar" porque es detección automática
3. El usuario hace clic en el chip y selecciona un tipo
4. Se hace PUT a `/api/projects/{id}/document-type` con `confirmed=True`
5. Desaparece "Sin confirmar"

### Código relevante

**Archivo**: [frontend/src/components/DocumentTypeChip.vue:20-22](frontend/src/components/DocumentTypeChip.vue#L20-L22)
```vue
<small v-if="!documentType.confirmed" class="not-confirmed">
  Sin confirmar
</small>
```

**Endpoint**: [api-server/main.py:12956-12982](api-server/main.py#L12956-L12982)
```python
success = service.set_project_document_type(
    project_id=project_id,
    document_type=document_type,
    document_subtype=document_subtype,
    confirmed=True,  # <-- Siempre se confirma al seleccionar
)
```

### Problema UX identificado

No hay un botón explícito de "Confirmar" ni feedback claro de que al seleccionar se confirma.

**Recomendación**:
1. Añadir texto explicativo: "Selecciona un tipo para confirmar"
2. O añadir un botón "Confirmar" explícito si el tipo detectado es correcto

---

## 3. ¿Se podría detectar el subtipo automáticamente?

**Respuesta**: Actualmente **NO** está implementado. Solo se detecta el tipo principal.

### Estado actual

- **Detección de tipo**: ✅ Implementado en `DocumentClassifier`
- **Detección de subtipo**: ❌ No implementado

### Viabilidad técnica

| Subtipo | Dificultad | Indicadores posibles |
|---------|------------|---------------------|
| Novela histórica vs género | Media | Fechas, términos de época |
| Infantil por edad | Alta | Legibilidad, vocabulario |
| Divulgación científica vs histórica | Media | Terminología, fechas |
| Manga vs cómic occidental | Baja | Onomatopeyas específicas |

### Plan de implementación propuesto

1. **Fase 1**: Añadir indicadores de subtipo al `DocumentClassifier`
2. **Fase 2**: Usar métricas de legibilidad para infantil (Fernández-Huerta)
3. **Fase 3**: Entrenar clasificador con corpus etiquetado

**Prioridad recomendada**: Media - El usuario puede seleccionar manualmente

---

## 4. Inconsistencia entre perfiles de corrección y tipos de documento

**Problema**: Son **dos sistemas diferentes** que deberían estar alineados pero no lo están.

### Sistema 1: Tipos de Documento (FeatureProfile)

**12 tipos** definidos en `feature_profile/models.py`:

| Código | Nombre |
|--------|--------|
| FIC | Ficción narrativa |
| MEM | Memorias |
| BIO | Biografía |
| CEL | Famosos/Influencers |
| DIV | Divulgación |
| ENS | Ensayo |
| AUT | Autoayuda |
| TEC | Manual técnico |
| PRA | Libro práctico |
| GRA | Novela gráfica |
| INF | Infantil/Juvenil |
| DRA | Teatro/Guion |

### Sistema 2: Presets de Corrección

**7 presets** definidos en `api-server/main.py:10442-10485`:

| ID | Nombre |
|----|--------|
| default | Por defecto |
| novel | Novela literaria |
| technical | Manual técnico |
| legal | Texto jurídico |
| medical | Texto médico |
| journalism | Periodismo |
| selfhelp | Autoayuda |

### Análisis de desalineación

| Tipo documento | Preset correspondiente | Estado |
|----------------|----------------------|--------|
| FICTION | novel | ✅ Alineado |
| MEMOIR | (ninguno) | ❌ Falta |
| BIOGRAPHY | (ninguno) | ❌ Falta |
| CELEBRITY | (ninguno) | ❌ Falta |
| DIVULGATION | (ninguno) | ❌ Falta |
| ESSAY | (ninguno) | ❌ Falta |
| SELF_HELP | selfhelp | ✅ Alineado |
| TECHNICAL | technical | ✅ Alineado |
| PRACTICAL | (ninguno) | ❌ Falta |
| GRAPHIC | (ninguno) | ❌ Falta |
| CHILDREN | (ninguno) | ❌ Falta |
| DRAMA | (ninguno) | ❌ Falta |
| (legal) | legal | ⚠️ Sin tipo |
| (medical) | medical | ⚠️ Sin tipo |
| (journalism) | journalism | ⚠️ Sin tipo |

### Recomendación

**Opción A**: Unificar sistemas
- Los presets de corrección deberían generarse automáticamente a partir del tipo de documento
- Al seleccionar tipo "Memorias", se aplica preset apropiado

**Opción B**: Mantener separados pero sincronizados
- Añadir presets para todos los tipos de documento
- Añadir tipos de documento para legal, médico, periodismo

---

## 5. "Por defecto" vs "General" - Inconsistencia

**Problema**: Hay dos conceptos que parecen iguales pero son diferentes.

### "Por defecto" (Preset de corrección)

**Ubicación**: [api-server/main.py:10443-10448](api-server/main.py#L10443-L10448)
```python
{
    "id": "default",
    "name": "Por defecto",
    "description": "Configuración estándar para documentos generales",
    "config": CorrectionConfig.default().to_dict(),
}
```

**Significado**: Es el preset que se aplica antes de elegir uno específico.

### "General" (Campo de documento)

**Ubicación**: [api-server/main.py:10540](api-server/main.py#L10540)
```python
DocumentField.GENERAL: "General",
```

**Significado**: Indica que el documento no pertenece a un campo especializado.

### Por qué aparecen juntos

En el panel de correcciones:
1. El preset seleccionado es "Por defecto"
2. El campo de documento dice "General"

Esto genera confusión porque:
- Ambos términos sugieren "sin especialización"
- Pero "Por defecto" es temporal (hasta que elijas)
- Y "General" es una categoría activa

### Recomendación

Renombrar para mayor claridad:
- "Por defecto" → "Configuración inicial" o "Estándar"
- O bien: unificar con el tipo de documento seleccionado

---

## 6. ¿Dónde se cambian los defaults para cada tipo?

### Defaults de Tipos de Documento

| Archivo | Contenido |
|---------|-----------|
| `src/narrative_assistant/feature_profile/models.py` | Definición de tipos, colores, iconos |
| Líneas 34-107 | `DOCUMENT_TYPES` dict |
| Líneas 110-181 | `DOCUMENT_SUBTYPES` dict |
| Líneas 273-448 | Funciones `_create_*_profile()` |

### Defaults de Corrección

| Archivo | Contenido |
|---------|-----------|
| `src/narrative_assistant/corrections/config.py` | Clase `CorrectionConfig` |
| Método `default()` | Configuración por defecto |
| Métodos `for_novel()`, `for_technical()`, etc. | Presets específicos |

### Defaults de UI

| Archivo | Contenido |
|---------|-----------|
| `api-server/main.py:10442-10485` | Lista de presets para el frontend |
| `frontend/src/composables/useDocumentTypeConfig.ts` | Configuración UI por tipo |

---

## Próximos Pasos

1. [ ] Decidir si unificar tipos de documento y presets de corrección
2. [ ] Implementar detección automática de subtipo (si se prioriza)
3. [ ] Mejorar UX de confirmación de tipo (botón explícito o texto)
4. [ ] Renombrar "Por defecto" para evitar confusión con "General"
5. [ ] Añadir presets de corrección faltantes

---

**Revisado por**: Sistema automatizado
**Próxima revisión**: Sesión de deliberación UX
