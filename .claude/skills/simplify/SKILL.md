---
name: simplify
description: "Simplificación de código sobredimensionado o complejo: reduce funciones largas, elimina abstracciones prematuras, aclara lógica condicional anidada. Invocar cuando el usuario diga 'simplifica esto', 'esta función es muy larga', 'hay demasiada abstracción aquí', 'hazlo más legible', 'refactor de complejidad'."
---

# /simplify — Simplificación de código complejo

## Cuándo usar

- Función o clase > 100 líneas que hace varias cosas a la vez.
- Lógica condicional anidada de más de 3 niveles.
- Abstracciones prematuras sin justificación real (un solo consumidor, lógica simple).
- Código duplicado que podría ser una función de 3 líneas.
- Componente Vue > 300 líneas con lógica mezclada.

## Argumentos

- `<archivo:función>` — target específico a simplificar
- `<archivo>` — analizar todo el archivo y proponer qué simplificar
- `--no-behavior-change` — modo estricto: la simplificación no puede cambiar el comportamiento observable (default: on siempre)

## Regla fundamental

**Simplificar ≠ refactorizar ≠ cambiar funcionalidad.** La simplificación reduce complejidad sin cambiar qué hace el código. Si la simplificación requiere cambiar tests, es un refactor.

## Flujo

### Paso 1 — Leer y diagnosticar

Leer el archivo/función objetivo. Identificar:

- **Complejidad ciclomática**: ¿cuántos if/else/try/for anidados hay?
- **Longitud**: ¿cuántas líneas tiene la función? ¿cuántos niveles de indentación?
- **Cohesión**: ¿la función hace una sola cosa o varias no relacionadas?
- **Abstracción prematura**: ¿hay clases/helpers con un solo consumidor que complican más de lo que ayudan?

### Paso 2 — Proponer simplificaciones

Para cada problema identificado, proponer una técnica concreta:

| Problema | Técnica |
|----------|---------|
| if/else anidado profundo | Early return / guard clause |
| Función que hace A+B+C | Extraer subfunciones privadas |
| Clase con un solo método útil | Convertir a función libre |
| Variable temporal que solo se usa una vez | Inline |
| Condición larga y compleja | Extraer a variable con nombre descriptivo |
| Código duplicado | Extraer función/constante |
| Lista de checks con lógica mixta | Separar validación de transformación |

### Paso 3 — Presentar propuesta

```
## Propuesta de simplificación: <archivo>:<función>

### Diagnóstico
- Longitud: N líneas (objetivo: <50)
- Niveles de indentación máximos: N (objetivo: ≤3)
- Cohesión: hace 3 cosas distintas (parse + validate + transform)

### Cambios propuestos

1. **Guard clauses** en las primeras 20 líneas (elimina 2 niveles de anidación)
   Antes:
   ```python
   if condition_a:
       if condition_b:
           # código real aquí
   ```
   Después:
   ```python
   if not condition_a:
       return ...
   if not condition_b:
       return ...
   # código real aquí (sin anidación)
   ```

2. **Extraer `_validate_input()`** — líneas 45-67 son validación pura
3. **Inline variable `tmp`** — solo se usa en la línea siguiente

Comportamiento: sin cambios. Los tests existentes pasan sin modificación.
```

### Paso 4 — Esperar OK y aplicar

Aplicar solo lo aprobado. Ejecutar los tests inmediatamente después:

```bash
# Backend
cd /Users/PABLO/repos/narrassist && .venv/bin/pytest tests/<ruta_test> -x -v

# Frontend
cd /Users/PABLO/repos/narrassist/frontend && npx vitest run <spec>
```

Si algún test falla → la simplificación cambió el comportamiento → revertir y diagnosticar.

### Paso 5 — Métricas finales

Mostrar:
```
Antes: 120 líneas, 5 niveles de indentación, complejidad ciclomática ~12
Después: 68 líneas, 3 niveles, complejidad ~6
Tests: ✅ sin cambios
```

## Anti-patrones de simplificación

- **NO** extraer funciones de 1 línea que no tienen nombre significativo — añade ruido.
- **NO** convertir código imperativo claro en funcional complejo (reduce, filter encadenados) si es menos legible.
- **NO** añadir type aliases para tipos simples (`type Path = str` cuando `str` es claro).
- **NO** simplificar y añadir funcionalidad en el mismo commit — simplify = refactor puro.
