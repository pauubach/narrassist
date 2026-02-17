# Test Cases - Contexto de Selección en Chat

**Objetivo**: Verificar que el LLM prioriza correctamente el texto seleccionado sobre el historial en casos de uso reales.

**Requisitos previos**:
1. Servidor backend recargado con los últimos cambios
2. Historial de chat limpio (o al menos sin conversación previa sobre estos temas)
3. Documento cargado con el manuscrito "Full"

---

## Caso 1: Atributo → Sujeto

**Contexto en el documento**:
```
Isabel Vargas era una joven de veinticinco años, pelirroja y de ojos claros.
```

**Test**:
1. Selecciona: `pelirroja`
2. Pregunta: `¿De quién es esta característica?`

**Resultado esperado**:
- ✅ Respuesta: "De Isabel Vargas [REF:1]" o "Esta característica es de Isabel Vargas [REF:1]"
- ✅ Navegación al hacer clic en [REF:1]: va a la palabra "pelirroja"
- ❌ NO debe responder sobre otra persona del historial

**Resultado real**:
```
[Pega aquí la respuesta del LLM]
```

**¿Navegación correcta?**: SÍ / NO
**¿Respuesta sobre la selección?**: SÍ / NO

---

## Caso 2: Referencia temporal → Anclaje

**Contexto en el documento**:
```
Mi sobrina Isabel ha desaparecido hace tres días. La policía no encuentra indicios.
```

**Test**:
1. Selecciona: `tres días`
2. Pregunta: `¿Cuándo fue eso?` o `¿Qué pasó?`

**Resultado esperado**:
- ✅ Respuesta: "Hace tres días Isabel desapareció [REF:1]" o "El evento ocurrió hace tres días: la desaparición de Isabel [REF:1]"
- ✅ Debe mencionar el evento anclado (desaparición de Isabel)
- ❌ NO debe solo repetir "tres días"

**Resultado real**:
```
[Pega aquí la respuesta del LLM]
```

**¿Respuesta sobre el evento?**: SÍ / NO

---

## Caso 3: Pronombre anafórico → Referente

**Contexto en el documento**:
```
Isabel Vargas era una joven de veinticinco años, pelirroja y de ojos claros.
Trabajaba como bibliotecaria en el pueblo y vivía en el ala este de la mansión.
Don Ramiro la describió como una persona tranquila, metódica y profundamente introvertida.
```

**Test**:
1. Selecciona: `Don Ramiro la describió como una persona tranquila`
2. Pregunta: `¿A quién se refiere con "la"?`

**Resultado esperado**:
- ✅ Respuesta: "Se refiere a Isabel Vargas [REF:1]" o "El pronombre 'la' se refiere a Isabel Vargas [REF:1]"
- ✅ Debe resolver la correferencia correctamente
- ❌ NO debe responder "a una persona tranquila" (descripción literal)

**Resultado real**:
```
[Pega aquí la respuesta del LLM]
```

**¿Resolvió la correferencia?**: SÍ / NO

---

## Caso 4: Expresión definida → Detalles específicos

**Test** (si hay menciones de "arma" o similar en el documento):
1. Selecciona una expresión como: `el arma del crimen` o `el objeto mencionado`
2. Pregunta: `¿Qué es exactamente?` o `¿Dónde se describe?`

**Resultado esperado**:
- ✅ Respuesta con detalles del documento sobre el objeto
- ✅ Cita del fragmento donde se describe [REF:1]

**Resultado real**:
```
[Si no hay caso apropiado en el documento, escribe: NO APLICABLE]
```

---

## Caso 5: Párrafo complejo → Clarificación

**Test**:
1. Selecciona un párrafo completo (50-100 palabras) que sea descriptivo o complejo
2. Pregunta: `Explica esto` o `¿Qué significa?`

**Resultado esperado**:
- ✅ Resumen o explicación del párrafo
- ✅ Referencia [REF:1] al párrafo
- ❌ NO debe inventar información no presente en la selección

**Resultado real**:
```
[Pega aquí la respuesta del LLM]
```

**¿Explicó correctamente?**: SÍ / NO

---

## Caso 6: Referencia a evento → Descripción del evento

**Contexto en el documento** (buscar expresiones como "aquel día", "ese momento", etc.):

**Test**:
1. Selecciona: `[expresión temporal que encuentres como "ese día", "aquel momento", etc.]`
2. Pregunta: `¿Qué pasó?`

**Resultado esperado**:
- ✅ Descripción del evento al que se refiere la expresión
- ✅ Referencia [REF:1]

**Resultado real**:
```
[Si no hay caso apropiado, escribe: NO APLICABLE]
```

---

## Caso 7: Prueba con historial conflictivo

**Setup**:
1. Primero haz una conversación normal (SIN selección):
   - Pregunta: "¿Quién es el protagonista?"
   - Espera respuesta del LLM
2. Luego, selecciona texto sobre **otro personaje** (por ejemplo, "Don Ramiro")
3. Pregunta: "¿Quién es este personaje?"

**Resultado esperado**:
- ✅ Debe responder sobre Don Ramiro (la selección), NO sobre el protagonista del historial
- ✅ Debe incluir [REF:1]

**Resultado real**:
```
[Pega aquí la respuesta del LLM]
```

**¿Priorizó la selección sobre el historial?**: SÍ / NO

---

## Resumen de Resultados

| Caso | Respuesta correcta | Navegación correcta | Notas |
|------|-------------------|---------------------|-------|
| 1. Atributo → Sujeto | ☐ SÍ ☐ NO | ☐ SÍ ☐ NO | |
| 2. Temporal → Anclaje | ☐ SÍ ☐ NO | ☐ SÍ ☐ NO | |
| 3. Pronombre → Referente | ☐ SÍ ☐ NO | ☐ SÍ ☐ NO | |
| 4. Expresión → Detalles | ☐ SÍ ☐ NO | ☐ SÍ ☐ NO | |
| 5. Párrafo → Clarificación | ☐ SÍ ☐ NO | ☐ SÍ ☐ NO | |
| 6. Evento → Descripción | ☐ SÍ ☐ NO | ☐ SÍ ☐ NO | |
| 7. Historial conflictivo | ☐ SÍ ☐ NO | ☐ SÍ ☐ NO | |

**Tasa de éxito**: ___/7 casos exitosos

---

## Problemas encontrados

**Lista aquí cualquier comportamiento inesperado**:
1.
2.
3.

---

## Conclusión

¿El sistema prioriza correctamente el texto seleccionado en casos de uso reales?
☐ SÍ, funciona bien en la mayoría de casos
☐ NO, sigue teniendo problemas
☐ PARCIAL, funciona solo en algunos casos

**Siguiente paso recomendado**:
