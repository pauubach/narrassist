# H2: Coherencia de Personajes

[← Volver a Heurísticas](./README.md) | [← Índice principal](../../README.md)

---

## Visión General

Esta familia verifica la consistencia psicológica, de conocimiento y de voz de los personajes a lo largo de la narrativa.

**Viabilidad técnica**: MEDIA (requiere validación manual significativa)

---

## H2.1 — Consistencia Psicológica

### Descripción
Las acciones de un personaje son comprensibles desde su psicología establecida.

### Señal
**Débil** - La psicología es inherentemente ambigua.

### Contexto de aplicación
Personajes con desarrollo significativo.

### Cuándo NO aplicar
- Personajes arquetípicos/funcionales
- Acciones bajo estados alterados (pánico, trauma)
- Revelaciones que recontextualizan comportamiento previo

### Cómo puede fallar
- **Falso positivo**: Comportamiento que parece inconsistente pero está justificado por información posterior
- **Riesgo alto**: Proyectar psicología "normal" sobre personajes atípicos

### Lo que NO es error
- Un personaje que miente sobre sus motivaciones
- Un personaje que se autoengaña
- Comportamiento irracional si está contextualizado emocionalmente

### Implementación
Esta heurística requiere mucha intervención manual. El sistema puede:
1. Listar acciones significativas del personaje
2. Permitir al corrector marcar inconsistencias
3. NO intentar inferir psicología automáticamente

---

## H2.2 — Consistencia de Conocimiento

### Descripción
Los personajes saben lo que podrían saber y no saben lo que no podrían.

### Señal
**Media** - Más objetiva que la psicológica.

### Contexto de aplicación
Escenas donde personajes usan información.

### Cuándo NO aplicar
- Información inferible que el personaje pudo deducir "offscreen"
- Personajes con capacidades especiales (telepatía, etc.)

### Cómo puede fallar
- **Falso positivo**: Deducciones razonables que el sistema no modela
- **Falso negativo**: Violaciones sutiles de información

### Modelo de datos
```python
@dataclass
class KnowledgeEvent:
    """Momento en que un personaje adquiere información."""
    character_id: int
    fact_id: int
    learned_at: SourceRef  # Cap, pág donde lo aprende
    method: str  # 'direct', 'told', 'inferred', 'observed'

def character_knows(char: Character, fact: Fact, at_position: int) -> bool:
    """True si el personaje conoce el hecho en esa posición del texto."""
    events = [e for e in char.knowledge_events
              if e.fact_id == fact.id and e.learned_at.position <= at_position]
    return len(events) > 0
```

### Ejemplo de alerta
```
⚠️ CONOCIMIENTO PREMATURO

María actúa sobre información que aún no tiene:

Cap.9, pág.189: "María evitó el callejón donde sabía que le
esperaba el peligro..."

El peligro se revela en Cap.11, pág.234

[Es intuición del personaje] [Es error] [Ignorar]
```

---

## H2.3 — Consistencia de Voz en Diálogo

### Descripción
Cada personaje tiene patrones de habla distinguibles y consistentes.

### Señal
**Media** - Analizable lingüísticamente.

### Contexto de aplicación
Escenas dialogadas.

### Cuándo NO aplicar
- Personajes que conscientemente modifican su habla (imitación, engaño)
- Personajes que evolucionan lingüísticamente (aprendizaje)

### Cómo puede fallar
- **Falso positivo**: Variación natural dentro del mismo idiolecto
- **Dificultad**: Modelar idiolectos con poco texto de referencia

### Métricas de perfil de voz

| Métrica | Descripción | Cálculo |
|---------|-------------|---------|
| Formalidad | Nivel de registro | Análisis léxico |
| Longitud media | Palabras por turno | Estadística |
| Muletillas | Expresiones repetidas | Frecuencia |
| Vocabulario | Riqueza léxica | TTR |
| Complejidad | Estructura sintáctica | POS analysis |

### Ejemplo de perfil
```
PERFILES DE VOZ

Personaje │ Formalidad │ Long.frase │ Muletillas     │ Vocabulario
──────────┼────────────┼────────────┼────────────────┼─────────────
María     │ Media      │ 12.3       │ "bueno", "ya"  │ Coloquial
Pedro     │ Alta       │ 18.7       │ "en efecto"    │ Culto
Lucía     │ Media      │ 11.9       │ "bueno", "ya"  │ Coloquial  ⚠️
```

### Tipos de alertas

| Tipo | Ejemplo | Severidad |
|------|---------|-----------|
| Personajes indistinguibles | María y Lucía hablan igual | 🟠 Alta |
| Cambio de registro | Pedro formal → coloquial sin razón | 🟡 Media |
| Diálogo sin atribución | No se sabe quién habla | 🟡 Media |
| Vocabulario anacrónico | Personaje histórico usa jerga moderna | 🟠 Alta |
| Idiolecto perdido | Muletilla desaparece sin razón | 🔵 Info |

### Ejemplo de alerta
```
⚠️ PERSONAJES INDISTINGUIBLES

María y Lucía tienen perfiles de voz casi idénticos (92% similitud):

• Mismas muletillas: "bueno", "ya"
• Longitud de frase similar: 12.3 vs 11.9
• Mismo nivel de formalidad
• Vocabulario indistinguible

Sugerencia: Diferenciar con:
• Muletilla única para Lucía
• Expresiones regionales diferentes
• Nivel de formalidad distinto

[Ver diálogos de María] [Ver diálogos de Lucía] [Ignorar]
```

---

## STEPs Relacionados

| STEP | Capacidad | Heurísticas |
|------|-----------|-------------|
| [1.4](../../steps/phase-1/step-1.4-dialogue-detector.md) | Detector diálogos | H2.3 |
| [2.2](../../steps/phase-2/step-2.2-entity-fusion.md) | Fusión manual | H2.1, H2.2 |
| [2.3](../../steps/phase-2/step-2.3-attribute-extraction.md) | Extractor atributos | H2.1 |
| [5.1](../../steps/phase-5/step-5.1-voice-profiles.md) | Perfiles voz | H2.3 |
| [5.2](../../steps/phase-5/step-5.2-voice-deviations.md) | Desviaciones voz | H2.3 |
| [5.4](../../steps/phase-5/step-5.4-speaker-attribution.md) | Atribución hablante | H2.3 |

---

## Siguiente

Ver [H3: Estructura Narrativa](./heuristics-h3-structure.md).
