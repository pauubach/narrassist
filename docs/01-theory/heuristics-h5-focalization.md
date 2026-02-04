# H5: Focalización y Perspectiva

[← Volver a Heurísticas](./README.md) | [← Índice principal](../../README.md)

---

## Visión General

Esta familia verifica la consistencia de la focalización narrativa: quién ve, quién sabe, y si se respetan los límites de acceso a información.

**Viabilidad técnica**: BAJA (pro-drop y complejidad semántica)

---

## Conceptos Fundamentales (Genette)

### Tipos de focalización

| Tipo | Descripción | Acceso a información |
|------|-------------|---------------------|
| **Focalización cero** | Narrador omnisciente | Sabe más que cualquier personaje |
| **Focalización interna** | Narrador limitado a un personaje | Solo sabe lo que el personaje sabe |
| **Focalización externa** | Narrador observador | Sabe menos que los personajes |

### Subtipos de focalización interna

- **Fija**: Un solo personaje focal en todo el texto
- **Variable**: Cambia entre personajes por capítulo/sección
- **Múltiple**: Mismo evento desde varios personajes

### Confusión común
**Focalización ≠ Voz**

- **Voz**: ¿Quién narra? (primera/tercera persona)
- **Focalización**: ¿Quién percibe? (desde qué perspectiva)

Ejemplo: Tercera persona con focalización interna estricta en María.

---

## H5.1 — Consistencia Focal

### Descripción
Dentro de una unidad focal, el narrador no accede a información fuera del alcance del foco.

### Señal
**Alta** - Las violaciones son identificables.

### Contexto de aplicación
Narraciones con focalización definida.

### Cuándo NO aplicar
- Omnisciencia declarada
- Cambios de foco marcados
- Acceso momentáneo justificado (telepatía, etc.)

### Cómo puede fallar
- **Falso positivo**: Información inferible por el personaje focal
- **Dificultad**: Delimitar exactamente qué "podría" saber el foco

### Reglas implícitas a respetar
1. Los cambios de focalización dentro de una escena deben ser intencionales
2. En focalización interna, el narrador NO puede saber lo que el personaje no sabe
3. La "violación" de focalización puede ser recurso, pero debe ser rastreable

### Ejemplo de alerta
```
⚠️ VIOLACIÓN DE POV

María NO puede saber esto (focalización interna en María):

Cap.7, pág.145:
"María sabía que Pedro, en ese momento, estaba pensando en
traicionarla..."

Problema: Con focalización interna, María no puede acceder a los
pensamientos de Pedro.

Posibles soluciones:
[Cambiar a "María sospechaba que..."]
[Marcar capítulo como omnisciente]
[Es narrador no fiable: ignorar]
```

---

## H5.2 — Marcado de Cambios Focales

### Descripción
Los cambios de focalización están señalados (cambio de sección, marcador textual).

### Señal
**Media** - Depende de convenciones.

### Contexto de aplicación
Narraciones con focalización variable.

### Cuándo NO aplicar
- Omnisciencia fluida tradicional
- Fusión focal deliberada

### Cómo puede fallar
- **Falso positivo**: Cambios sutiles intencionales
- **Problema**: Las convenciones varían

### Tipos de alertas

| Tipo | Ejemplo | Severidad |
|------|---------|-----------|
| Violación de POV | Narrador interno accede a mente de otro | 🟠 Alta |
| Conocimiento prematuro | Personaje sabe algo antes de revelarse | 🟠 Alta |
| Salto de focalización no marcado | Cambio de POV sin separador | 🟡 Media |
| Ironía dramática rota | Lector debería saber pero no se reveló | 🔵 Info |
| Omnisciencia selectiva | Narrador sabe X pero ignora Y arbitrariamente | 🟡 Media |

---

## Limitación Crítica: Pro-drop

### El problema del español

En español, el sujeto puede omitirse (pro-drop):

```
"Llegó tarde. Pensó que nadie lo notaría."
     ↑           ↑
  (él/ella)   (él/ella) - sujetos omitidos
```

**Implicación**: ~40-50% de los sujetos son invisibles para el NLP.

### Impacto en focalización

- No podemos detectar automáticamente "quién piensa" en la mayoría de casos
- Las violaciones de POV con sujeto implícito son indetectables

### Solución: Declaración Manual

En lugar de detección automática:

1. El corrector **declara** la focalización por capítulo/escena
2. El sistema **verifica** solo con sujetos **explícitos**
3. Para sujetos implícitos: confianza MUY BAJA o ignorar

```python
@dataclass
class FocalizationDeclaration:
    chapter_id: int
    scene_id: Optional[int]
    type: str  # 'omniscient', 'internal', 'external'
    focal_character_id: Optional[int]  # Para focalización interna
    declared_by: str  # 'user' o 'inferred'
    confidence: float
```

---

## Matriz de Conocimiento

Una herramienta útil para tracking de focalización:

```
MATRIZ DE CONOCIMIENTO

  Hecho              │ Lector │ María │ Pedro │
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  María es adoptada  │   ✓   │   ✗   │   ✓   │
  Pedro la traicionará│  ✗   │   ✗   │   ✓   │
  El tesoro existe   │   ✓   │   ✓   │   ✗   │

  ✓ = Conoce  ✗ = No conoce  ◐ = Parcial  ! = Cree falso
```

### Uso de la matriz
1. **Ironía dramática**: Lector sabe más que personaje
2. **Sorpresa**: Lector y personaje descubren juntos
3. **Misterio**: Personaje sabe más que lector
4. **Verificación**: Personaje no puede usar información que no tiene

---

## Fiabilidad del Narrador (Booth)

### Tipos de narrador

| Tipo | Descripción |
|------|-------------|
| **Fiable** | Sus juicios se alinean con las normas de la obra |
| **No fiable** | Discrepancia entre lo que dice y lo que la obra implica |

### Tipos de no fiabilidad (Phelan)

1. **Eje de hechos**: Informa mal (error o mentira)
2. **Eje de valores**: Evalúa mal pero reporta bien
3. **Eje de conocimiento**: No entiende lo que reporta

### Implicación para el sistema
- Un sistema NO debe asumir no fiabilidad sin señales textuales
- Las "inconsistencias" en narrador no fiable son features, no bugs
- El corrector debe poder marcar narradores como no fiables

---

## STEPs Relacionados

| STEP | Capacidad | Heurísticas |
|------|-----------|-------------|
| [6.1](../../steps/phase-6/step-6.1-focalization-declaration.md) | Declaración focalización | H5.1, H5.2 |
| [6.2](../../steps/phase-6/step-6.2-focalization-violations.md) | Violaciones focalización | H5.1 |

---

## Siguiente

Ver [H6: Gestión de Información](./heuristics-h6-information.md).
