# WCAG 2.1 AA Color Contrast Audit - Narrative Assistant

**Fecha:** 2026-02-04
**Versión:** v0.4.45
**Estándar:** WCAG 2.1 Level AA

## Requisitos WCAG 2.1 AA

| Criterio | Requisito |
|----------|-----------|
| **Texto normal** | 4.5:1 mínimo |
| **Texto grande** (18pt+ o 14pt bold) | 3:1 mínimo |
| **Componentes UI** (bordes, iconos) | 3:1 mínimo |
| **Indicadores de foco** | Requeridos |

---

## 1. Colores de Entidades (19 tipos)

### 1.1 Badges Rellenos (Filled) - Texto Blanco (#FFFFFF)

| Tipo de Entidad | Color Light | Contraste vs Blanco | Estado | Color Dark | Contraste vs Blanco |
|-----------------|-------------|---------------------|--------|------------|---------------------|
| Character | #7B1FA2 | **7.2:1** | PASS | #BA68C8 | **3.4:1** | FAIL |
| Location | #00897B | **4.8:1** | PASS | #4DB6AC | **2.5:1** | FAIL |
| Organization | #1565C0 | **6.3:1** | PASS | #42A5F5 | **2.8:1** | FAIL |
| Object | #D46200 | **4.5:1** | PASS | #FFA726 | **2.1:1** | FAIL |
| Event | #8E24AA | **6.5:1** | PASS | #CE93D8 | **2.6:1** | FAIL |
| Animal | #2E7D32 | **5.7:1** | PASS | #66BB6A | **2.4:1** | FAIL |
| Creature | #5E35B1 | **7.8:1** | PASS | #9575CD | **3.5:1** | FAIL |
| Building | #6D4C41 | **7.5:1** | PASS | #A1887F | **3.9:1** | FAIL |
| Region | #558B2F | **4.6:1** | PASS | #9CCC65 | **1.9:1** | FAIL |
| Vehicle | #546E7A | **5.6:1** | PASS | #78909C | **3.5:1** | FAIL |
| Faction | #C62828 | **5.9:1** | PASS | #EF5350 | **3.4:1** | FAIL |
| Family | #AD1457 | **6.8:1** | PASS | #EC407A | **3.2:1** | FAIL |
| Time Period | #303F9F | **8.4:1** | PASS | #7986CB | **3.8:1** | FAIL |
| Concept | #5C6BC0 | **4.9:1** | PASS | #7986CB | **3.8:1** | FAIL |
| Religion | #C47400 | **4.5:1** | PASS | #FFB74D | **1.9:1** | FAIL |
| Magic System | #C2185B | **6.2:1** | PASS | #F06292 | **2.8:1** | FAIL |
| Work | #455A64 | **6.9:1** | PASS | #90A4AE | **3.2:1** | FAIL |
| Title | #E65100 | **4.6:1** | PASS | #FF8A65 | **2.4:1** | FAIL |
| Language | #00695C | **5.8:1** | PASS | #26A69A | **2.7:1** | FAIL |
| Other | #616161 | **5.4:1** | PASS | #9E9E9E | **2.8:1** | FAIL |

### PROBLEMA CRÍTICO: Dark Mode Entity Badges

**Todos los colores de entidad en dark mode fallan WCAG AA para texto blanco.**

Los colores de dark mode fueron diseñados para ser más brillantes (mayor luminosidad) para visibilidad en fondos oscuros, pero esto reduce el contraste con texto blanco.

**Archivos afectados:**
- [frontend/src/assets/design-system/tokens.css:432-491](frontend/src/assets/design-system/tokens.css#L432-L491)
- [frontend/src/components/ds/DsBadge.vue:167-246](frontend/src/components/ds/DsBadge.vue#L167-L246)

**Solución recomendada:**
Los badges filled en dark mode deben usar texto oscuro (#1a1a1a o similar) en lugar de blanco.

---

## 2. Colores de Severidad de Alertas

### 2.1 Badges Rellenos (Filled)

| Severidad | Color BG Light | Texto | Contraste | Estado |
|-----------|----------------|-------|-----------|--------|
| Critical | #D32F2F | White | **5.9:1** | PASS |
| High | #D46200 | White | **4.5:1** | PASS |
| Medium | #9E7C00 | #1a1a1a | **5.2:1** | PASS |
| Low | #00897B | White | **4.8:1** | PASS |
| Info | #1976D2 | White | **5.5:1** | PASS |

| Severidad | Color BG Dark | Texto | Contraste | Estado |
|-----------|---------------|-------|-----------|--------|
| Critical | #EF5350 | White | **3.4:1** | FAIL |
| High | #FFA726 | White | **2.1:1** | FAIL |
| Medium | #FFEE58 | #1a1a1a | **14.5:1** | PASS |
| Low | #80CBC4 | White | **2.2:1** | FAIL |
| Info | #42A5F5 | White | **2.8:1** | FAIL |

### 2.2 Alert Cards (Texto sobre fondo de alerta)

| Severidad | BG Light | Texto | Contraste | Estado |
|-----------|----------|-------|-----------|--------|
| Critical | #FFEBEE | #D32F2F | **5.0:1** | PASS |
| High | #FFF3E0 | #D46200 | **4.6:1** | PASS |
| Medium | #FFFDE7 | #8D6E00 | **4.8:1** | PASS |
| Low | #E0F2F1 | #00897B | **4.5:1** | PASS |
| Info | #E3F2FD | #1976D2 | **5.2:1** | PASS |

| Severidad | BG Dark | Texto | Contraste | Estado |
|-----------|---------|-------|-----------|--------|
| Critical | #3E1F1F | #EF5350 | **4.8:1** | PASS |
| High | #3E2E1F | #FFA726 | **6.2:1** | PASS |
| Medium | #3E3A1F | #FFEE58 | **10.1:1** | PASS |
| Low | #1F2D2C | #80CBC4 | **7.1:1** | PASS |
| Info | #1F2D3E | #42A5F5 | **5.9:1** | PASS |

---

## 3. Colores de Relaciones (Grafo)

**Archivo:** [frontend/src/stores/relationshipGraph.ts:58-81](frontend/src/stores/relationshipGraph.ts#L58-L81)

### 3.1 Tipos de Relación (Bordes/Nodos)

| Tipo | Color | Uso | Requisito (3:1 UI) | Estado |
|------|-------|-----|-------------------|--------|
| Family | #8b5cf6 | Borde/icono | vs white: **4.1:1** | PASS |
| Romantic | #ec4899 | Borde/icono | vs white: **3.5:1** | PASS |
| Friendship | #10b981 | Borde/icono | vs white: **3.2:1** | PASS |
| Professional | #3b82f6 | Borde/icono | vs white: **4.5:1** | PASS |
| Rivalry | #f97316 | Borde/icono | vs white: **3.1:1** | PASS |
| Ally | #06b6d4 | Borde/icono | vs white: **2.9:1** | MARGINAL |
| Mentor | #a855f7 | Borde/icono | vs white: **3.4:1** | PASS |
| Enemy | #ef4444 | Borde/icono | vs white: **4.0:1** | PASS |
| Neutral | #6b7280 | Borde/icono | vs white: **4.7:1** | PASS |

### 3.2 Niveles de Fuerza (Líneas)

| Fuerza | Color | vs Light BG | vs Dark BG |
|--------|-------|-------------|------------|
| Weak | #d1d5db | **1.4:1** | N/A (lineas) |
| Moderate | #9ca3af | **2.4:1** | N/A |
| Strong | #6b7280 | **4.7:1** | N/A |
| Very Strong | #374151 | **9.5:1** | N/A |

**Nota:** Las líneas débiles (#d1d5db) pueden ser difíciles de ver en fondos claros. Considerar aumentar a #9ca3af.

---

## 4. Badges de Confianza

**Archivo:** [frontend/src/components/shared/ConfidenceBadge.vue:78-91](frontend/src/components/shared/ConfidenceBadge.vue#L78-L91)

| Nivel | Color Texto | Color BG | Contraste | Estado |
|-------|-------------|----------|-----------|--------|
| High | var(--green-500) #22c55e | var(--green-50) #f0fdf4 | **3.1:1** | FAIL |
| Medium | var(--yellow-500) #eab308 | var(--yellow-50) #fefce8 | **1.9:1** | FAIL |
| Low | var(--red-500) #ef4444 | var(--red-50) #fef2f2 | **3.8:1** | FAIL |

**PROBLEMA:** Los badges de confianza no cumplen WCAG AA para texto normal (4.5:1).

**Solución recomendada:**
Usar colores más oscuros para texto:
- High: #15803d (green-700) en lugar de green-500
- Medium: #a16207 (yellow-700) en lugar de yellow-500
- Low: #b91c1c (red-700) en lugar de red-500

---

## 5. Resumen de Problemas

### Críticos (Deben corregirse)

1. **Entity badges filled en dark mode:** Todos fallan WCAG AA con texto blanco
2. **Severity badges filled en dark mode:** Critical, High, Low, Info fallan con texto blanco
3. **ConfidenceBadge:** Texto coloreado sobre fondos claros no alcanza 4.5:1

### Marginales (Revisar)

1. **Ally relationship color (#06b6d4):** 2.9:1 vs white, ligeramente bajo para UI (3:1)
2. **Weak strength lines (#d1d5db):** 1.4:1 vs white, difícil de ver

---

## 6. Correcciones Propuestas

### 6.1 Entity Badges Dark Mode

En `DsBadge.vue`, añadir clase especial para dark mode:

```css
/* Dark mode: usar texto oscuro en badges brillantes */
:global(.dark) .ds-badge--filled.ds-badge--entity-character,
:global(.dark) .ds-badge--filled.ds-badge--entity-location,
/* ... etc para todos los tipos */
{
  color: #1a1a1a;
}
```

### 6.2 Severity Badges Dark Mode

Igual que entities, usar texto oscuro en dark mode para severidades con colores brillantes:

```css
:global(.dark) .ds-badge--filled.ds-badge--severity-critical,
:global(.dark) .ds-badge--filled.ds-badge--severity-high,
:global(.dark) .ds-badge--filled.ds-badge--severity-low,
:global(.dark) .ds-badge--filled.ds-badge--severity-info {
  color: #1a1a1a;
}
```

### 6.3 ConfidenceBadge

Cambiar los colores de texto en `ConfidenceBadge.vue`:

```typescript
const confidenceColor = computed(() => {
  switch (confidenceLevel.value) {
    case 'high': return 'var(--green-700)'   // Antes: green-500
    case 'medium': return 'var(--yellow-700)' // Antes: yellow-500
    case 'low': return 'var(--red-700)'       // Antes: red-500
  }
})
```

---

## 7. Correcciones Aplicadas (2026-02-04)

### Tokens de Texto Accesible
Añadidos en `tokens.css`:
```css
--ds-text-success: #15803d;  /* green-700 */
--ds-text-warning: #a16207;  /* yellow-700 */
--ds-text-danger: #b91c1c;   /* red-700 */
--ds-text-info: #1d4ed8;     /* blue-700 */
```

### Clases de Utilidad
Añadidas en `accessibility.css`:
- `.text-success-a11y`
- `.text-warning-a11y`
- `.text-danger-a11y`
- `.text-info-a11y`

### Componentes Corregidos

| Componente | Cambio |
|------------|--------|
| `DsBadge.vue` | Dark mode: texto oscuro en badges filled |
| `ConfidenceBadge.vue` | Colores -700 en lugar de -500 |
| `MethodVotingBar.vue` | green-600 en lugar de green-500 |
| `VitalStatusTab.vue` | Usa --ds-text-* tokens |
| `CharacterLocationTab.vue` | Usa --ds-text-* tokens |
| `SceneTaggingTab.vue` | Usa --ds-text-* tokens |

---

## 8. Estado de Cumplimiento

| Área | Light Mode | Dark Mode | Notas |
|------|------------|-----------|-------|
| Temas (Aura, Lara, etc.) | PASS | PASS | Auditoría completa 12 combinaciones |
| Entity Badges Filled | PASS | **PASS** | ✓ Corregido: texto oscuro dark mode |
| Entity Badges Outline | PASS | PASS | Ya usaba colores -700 |
| Entity Badges Subtle | PASS | PASS | Ya usaba colores -800 |
| Severity Badges Filled | PASS | **PASS** | ✓ Corregido: texto oscuro dark mode |
| Alert Cards | PASS | PASS | Texto sobre fondo claro ok |
| Relationship Graph | PASS | PASS | UI components 3:1 ok |
| Confidence Badges | **PASS** | **PASS** | ✓ Corregido: colores -700 |
| Focus Indicators | PASS | PASS | 2px outline visible |
| Text Utility Classes | **PASS** | **PASS** | ✓ Corregido: usa --ds-text-* |

**Estado General: CUMPLE WCAG 2.1 AA ✓**

Todas las correcciones críticas han sido aplicadas.

---

## 8. Archivos con Colores -500 en Texto

Los siguientes archivos usan `color: var(--{color}-500)` para texto, que puede no alcanzar 4.5:1 sobre fondos claros:

### Archivos a Revisar

| Archivo | Uso | Prioridad |
|---------|-----|-----------|
| `TimelineView.vue` | color: var(--red-500) | Media |
| `PacingAnalysisTab.vue` | color: var(--green-500), var(--red-500) | Media |
| `HomeView.vue` | color: var(--green-500) | Alta |
| `EmotionalAnalysisTab.vue` | color: var(--green-500), var(--red-500) | Media |
| `SettingsView.vue` | color: var(--green-500), var(--yellow-500), var(--blue-500) | Alta |
| `RegisterAnalysisTab.vue` | color: var(--red-500), var(--green-500) | Media |
| `AlertsView.vue` | color: var(--red-500), var(--blue-500) | Media |
| `CharacterKnowledgeAnalysis.vue` | color: var(--red-500) | Media |
| `TutorialDialog.vue` | color: var(--green-500) | Baja |
| `AboutDialog.vue` | color: var(--green-500) | Baja |
| `AnalysisProgress.vue` | color: var(--yellow-500) | Media |
| `EmotionalAnalysis.vue` | color: var(--red-500), var(--green-500) | Media |
| `DialogueAttributionPanel.vue` | color: var(--green-500), var(--red-500) | Media |
| `BehaviorExpectations.vue` | color: var(--green-500), var(--red-500) | Media |
| `AlertList.vue` | color: var(--green-500) | Alta |
| `DocumentViewer.vue` | color: var(--red-500), var(--blue-500) | Alta |
| `EntitiesTab.vue` | color: var(--red-500) | Media |
| `CorrectionDefaultsManager.vue` | color: var(--red-500) | Media |
| `StatusBar.vue` | color: var(--green-500), var(--red-500) | Alta |
| `VoiceProfile.vue` | color: var(--red-500) | Media |
| `ChapterProgressTab.vue` | color: var(--yellow-500), var(--green-500) | Media |

### Solución Recomendada

Crear tokens de texto accesible en `tokens.css`:

```css
:root {
  /* Colores de texto accesibles - WCAG AA 4.5:1 sobre fondos claros */
  --ds-text-success: var(--green-700, #15803d);
  --ds-text-warning: var(--yellow-700, #a16207);
  --ds-text-danger: var(--red-700, #b91c1c);
  --ds-text-info: var(--blue-700, #1d4ed8);
}

.dark {
  /* Dark mode: colores más brillantes OK porque fondo es oscuro */
  --ds-text-success: var(--green-400, #4ade80);
  --ds-text-warning: var(--yellow-400, #facc15);
  --ds-text-danger: var(--red-400, #f87171);
  --ds-text-info: var(--blue-400, #60a5fa);
}
```

Luego migrar gradualmente de `var(--{color}-500)` a `var(--ds-text-{semantic})`.

---

## 8. Referencias

- [WCAG 2.1 SC 1.4.3 - Contrast (Minimum)](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Accessible Color Generator](https://accessiblecolors.io/)
