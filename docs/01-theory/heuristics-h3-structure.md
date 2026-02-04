# H3: Estructura Narrativa

[← Volver a Heurísticas](./README.md) | [← Índice principal](../../README.md)

---

## Visión General

Esta familia verifica la estructura narrativa: setup/payoff, progresión del conflicto y balance de escenas.

**Viabilidad técnica**: BAJA (requiere comprensión semántica profunda)

---

## H3.1 — Setup/Payoff

### Descripción
Los elementos significativos introducidos deben tener resolución, y las resoluciones deben tener preparación.

### Señal
**Media** - Rastreable estructuralmente si los elementos están marcados.

### Contexto de aplicación
Elementos marcados como significativos.

### Cuándo NO aplicar
- Subtramas deliberadamente abiertas (realismo)
- Red herrings intencionales
- Finales abiertos como elección estética

### Cómo puede fallar
- **Falso positivo**: Elementos que parecen plantados pero son atmósfera
- **Falso negativo**: Setups sutiles que el sistema no marca

### Principio de Chekhov

> "Si en el primer acto hay un rifle colgado en la pared, en el tercer acto debe dispararse."

**Chekhov invertido**: Si en el tercer acto se dispara un rifle, debería haberse mostrado antes.

### Implementación
Esta heurística requiere que el usuario marque manualmente:
1. Elementos que parecen ser "plantados" (setup)
2. Resoluciones significativas (payoff)

El sistema entonces verifica:
- ¿Hay setups sin payoff?
- ¿Hay payoffs sin setup?

```python
@dataclass
class StoryElement:
    id: int
    type: str  # 'setup', 'payoff'
    description: str
    source: SourceRef
    linked_to: Optional[int]  # ID del elemento vinculado

def check_setup_payoff(elements: List[StoryElement]) -> List[Alert]:
    setups = [e for e in elements if e.type == 'setup']
    payoffs = [e for e in elements if e.type == 'payoff']

    alerts = []
    for setup in setups:
        if not any(p.linked_to == setup.id for p in payoffs):
            alerts.append(Alert(
                type='SETUP_WITHOUT_PAYOFF',
                element=setup
            ))
    return alerts
```

---

## H3.2 — Progresión de Conflicto

### Descripción
El conflicto central avanza, se complica o se transforma.

### Señal
**Débil** - Subjetiva, dependiente de interpretación del conflicto.

### Contexto de aplicación
Tramas con conflicto identificable.

### Cuándo NO aplicar
- Narrativa slice-of-life o contemplativa
- Secciones deliberadamente estáticas (calma antes de tormenta)

### Cómo puede fallar
- **Falso positivo**: Malinterpretar cuál es el conflicto central
- **Problema**: Conflictos internos menos visibles que externos

### Señales editoriales útiles
- Secuencias de escenas sin avance de trama ni desarrollo de personaje
- Diálogos que no revelan ni avanzan
- Descripciones que no establecen atmósfera ni aportan información relevante

### Lo que NO es error
- Ralentización deliberada antes de un clímax
- Escenas "de respiro" tras momentos intensos
- Digresiones que construyen mundo o tema

---

## H3.3 — Balance de Escenas

### Descripción
Alternancia funcional entre tipos de escenas (acción, diálogo, reflexión, descripción).

### Señal
**Débil** - Muy dependiente de género y estilo.

### Contexto de aplicación
Obras con variación de escenas.

### Cuándo NO aplicar
- Estilos deliberadamente monolíticos (todo diálogo, todo interior)
- Obras cortas donde la variación no aplica

### Cómo puede fallar
- **Falso positivo**: Imponer patrón de género incorrecto
- **Problema**: Definir "demasiado" es subjetivo

### Tipos de escenas

| Tipo | Características | Función típica |
|------|-----------------|----------------|
| Acción | Verbos dinámicos, poco diálogo | Avanzar trama |
| Diálogo | Turnos conversacionales | Revelar personaje, relaciones |
| Reflexión | Pensamientos internos | Desarrollo psicológico |
| Descripción | Adjetivos, sensorial | Establecer atmósfera |

### Dependencia de género

| Género | Balance típico |
|--------|----------------|
| Thriller | Alta acción, diálogo rápido |
| Literario | Reflexión, descripción extensa |
| Romance | Diálogo emocional dominante |
| Fantasía | Descripción de mundo |

---

## Limitaciones de Implementación

### Por qué la viabilidad es BAJA

1. **Comprensión semántica**: Identificar qué es un "setup" requiere entender la narrativa
2. **Subjetividad**: Lo que "avanza" el conflicto es interpretable
3. **Contexto de género**: El balance esperado varía enormemente

### Enfoque recomendado

En lugar de detección automática:
1. Proporcionar **herramientas de marcado manual**
2. Ofrecer **visualizaciones** de estructura
3. Dejar que el corrector **identifique problemas**

---

## STEPs Relacionados

| STEP | Capacidad | Heurísticas |
|------|-----------|-------------|
| [1.2](../../steps/phase-1/step-1.2-structure-detector.md) | Detector estructura | Segmentación |
| [1.4](../../steps/phase-1/step-1.4-dialogue-detector.md) | Detector diálogos | H3.3 (balance) |

---

## Siguiente

Ver [H4: Voz y Estilo](./heuristics-h4-voice.md).
