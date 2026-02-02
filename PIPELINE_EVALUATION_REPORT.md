# Informe de Evaluaci&oacute;n de Pipeline - Narrative Assistant

**Fecha**: 2026-02-01
**Perfil usado**: `UnifiedConfig.standard()` (sin LLM)
**Documentos analizados**: 9 evaluation_tests (con ground truth documentado)
**Tiempo promedio por documento**: ~100-130s (documentos de 2-6 KB)

---

## BUGS CORREGIDOS (2026-02-01)

Se corrigieron 8 bugs cr&iacute;ticos. Resultados en `prueba_inconsistencias_personajes.txt`:
- **Consistencia**: 2 &rarr; **7** inconsistencias detectadas (de 15+ esperadas, ~47%)
- **Falsos positivos ortogr&aacute;ficos**: 81 &rarr; **0**
- **Alertas totales**: 165 &rarr; **89** (eliminado ruido)
- **Entidades**: Fusi&oacute;n autom&aacute;tica funcional (Mar&iacute;a S&aacute;nchez = Mar&iacute;a)
- **Correferencias**: M&oacute;dulo operativo (antes crasheaba)

Bugs corregidos:
1. `resolve_coreferences_voting()` - par&aacute;metro `use_llm` &rarr; `config=CorefConfig(...)`
2. `attr.attribute_type` &rarr; `attr.key` (persistencia de atributos)
3. `analyze_chapter()` retorna `list`, no `Result` (coherencia emocional)
4. `chain.representative` &rarr; `chain.main_mention` (CoreferenceChain)
5. `entity.mentions` &rarr; `entity.aliases` (fusi&oacute;n de entidades)
6. Regex `\s{2,}` &rarr; `[^\S\n]{2,}` (excluir saltos de p&aacute;rrafo)
7. Eliminado patr&oacute;n "May&uacute;scula innecesaria" (falsos positivos incorregibles)
8. Excluir n&uacute;meros romanos del patr&oacute;n "Letras repetidas"

---

## Resumen Ejecutivo

La pipeline tiene una base s&oacute;lida en **detecci&oacute;n gramatical** (deque&iacute;smo, que&iacute;smo, la&iacute;smo, concordancia, redundancias) y tras las correcciones, la **detecci&oacute;n de inconsistencias de atributos** funciona razonablemente (47% recall). Quedan problemas en la extracci&oacute;n de atributos (misatribuci&oacute;n) y NER (entidades falsas).

---

## 1. BUGS CR&Iacute;TICOS (M&oacute;dulos rotos)

### 1.1 Correferencias completamente rotas

**Error**: `resolve_coreferences_voting() got an unexpected keyword argument 'use_llm'`
**Impacto**: La resoluci&oacute;n de correferencias NO se ejecuta en ning&uacute;n documento.
**Causa**: `unified_analysis.py:1152` pasa `use_llm=self.config.use_llm`, pero la funci&oacute;n en `coreference_resolver.py:2067` no acepta ese par&aacute;metro. Deber&iacute;a usar `config=CorefConfig(use_llm_for_coref=...)`.
**Consecuencia**: Sin correferencias, los pronombres no se resuelven, las cadenas de menci&oacute;n no se construyen, y la fusi&oacute;n de entidades queda muy limitada.

### 1.2 Persistencia de atributos rota

**Error**: `'ExtractedAttribute' object has no attribute 'attribute_type'`
**Impacto**: Los atributos extra&iacute;dos no se persisten correctamente en la base de datos.
**Causa**: `unified_analysis.py:1854,2845` accede a `attr.attribute_type`, pero la clase `ExtractedAttribute` en `attributes.py:149` define el campo como `attr.key` (de tipo `AttributeKey`).

### 1.3 Coherencia emocional completamente rota

**Error**: `'list' object has no attribute 'is_success'`
**Impacto**: El an&aacute;lisis de coherencia emocional no produce resultados en ning&uacute;n documento (siempre 0 incoherencias).
**Causa**: `emotional_coherence.py:analyze_chapter()` retorna `list[EmotionalIncoherence]` directamente, pero `unified_analysis.py:2441` espera un `Result[list]` con `.is_success`.

### 1.4 Ollama/LLM consistentemente falla

**Error**: `Error de Ollama: 500 - {"error":"llama runner process has terminated: exit status 2"}`
**Impacto**: Todos los m&eacute;todos que usan LLM fallan silenciosamente.
**Nota**: Aunque el perfil standard tiene `use_llm=False`, el m&oacute;dulo de correferencias y atributos intentan conectar de todos modos.

---

## 2. FALSOS POSITIVOS MASIVOS EN ORTOGRAF&Iacute;A

### 2.1 "Espacios m&uacute;ltiples" en saltos de p&aacute;rrafo (SEVERIDAD: CR&Iacute;TICA)

**Frecuencia**: 20-70 alertas falsas por documento (el mayor generador de ruido).
**Causa**: El regex `r'\s{2,}'` en `spelling_checker.py:142` detecta `\n\n` (separaci&oacute;n normal de p&aacute;rrafos) como error ortogr&aacute;fico.
**Severidad asignada**: CRITICAL (deberia ser ignorado).
**Ejemplo**: Cada doble salto de l&iacute;nea genera: `[CRITICAL] Error ortogr&aacute;fico: Espacios m&uacute;ltiples`

### 2.2 "May&uacute;scula innecesaria" tras comas

**Frecuencia**: 5-15 alertas falsas por documento.
**Causa**: El regex en `spelling_checker.py:148` detecta may&uacute;sculas despu&eacute;s de comas sin considerar nombres propios ni inicios de oraci&oacute;n.
**Ejemplos falsos**: `", Mar&iacute;a"`, `", An"`, `", Luc&iacute;a"` &mdash; todos nombres propios.

### 2.3 "III" como "Letras repetidas"

**Causa**: El regex `r'(\w)\1{2,}'` en `spelling_checker.py:138` trata n&uacute;meros romanos como letras repetidas.

### 2.4 Sugerencias ortogr&aacute;ficas incorrectas

El corrector sin Hunspell (fallback) produce sugerencias absurdas:

| Error | Sugerencia dada | Correcta |
|-------|----------------|----------|
| `aciendo` | `asiendo` | `haciendo` |
| `acia` | `Asia` | `hacia` |
| `abitacion` | `aviaci&oacute;n` | `habitaci&oacute;n` |
| `acer` | `Aser` | `hacer` |
| `Abian` | `Av&iacute;an` | `Hab&iacute;an` |
| `Sono` | `Sue&ntilde;o` | `So&ntilde;&oacute;` |
| `bolo` | `vuelo` | `vol&oacute;` |

**Causa**: Sin diccionario Hunspell, el corrector usa LanguageTool remoto o heur&iacute;sticas simples que no reconocen errores con h- aspirada.

---

## 3. DETECCI&Oacute;N GRAMATICAL (parcialmente buena)

### 3.1 Funciona bien

- **Deque&iacute;smo**: Detecta "pensaba de que", "pienso de que", "opinaba de que" correctamente
- **Que&iacute;smo**: Detecta "estaba segura que", "me acuerdo que", "estoy seguro que"
- **La&iacute;smo**: Detecta "la dijo", "la hab&iacute;a preparado", "la cont&oacute;", "las dijo"
- **Concordancia de g&eacute;nero**: "El casa", "casa antiguo", "el ventanas", "La amor"
- **Concordancia de n&uacute;mero**: "vaso llenos", "el mesa"
- **Redundancias**: "subi&oacute; arriba", "baj&oacute; abajo", "salieron afuera", "m&aacute;s mejor"
- **Habemos**: Detecta correctamente como incorrecto

### 3.2 Problemas

- **Alertas duplicadas**: Muchos errores se detectan 2 veces (por el detector custom Y por LanguageTool), generando alertas redundantes
- **Falsos positivos de concordancia**: "diferentes formatos", "mismos ojos" marcados como error
- **G&eacute;nero incorrecto asignado**: "CAPITULO INCLUIDOS" reporta que CAPITULO es femenino
- **"coma innecesaria antes de y"**: `"libre, y ella"` no es siempre incorrecto en espa&ntilde;ol

---

## 4. EXTRACCI&Oacute;N DE ENTIDADES (NER)

### 4.1 Entidades falsas o absurdas

Se crean entidades a partir de fragmentos de texto que no son entidades:

| Entidad detectada | Tipo | Problema |
|-------------------|------|----------|
| `Estoy seguro` | CONCEPT | Fragmento de di&aacute;logo |
| `Pedro? Que opinas tu` | CHARACTER | Pregunta de di&aacute;logo |
| `havia leido` | CHARACTER | Verbo mal escrito |
| `nuebo` | CHARACTER | Adjetivo mal escrito |
| `Aqui crecimos` | CONCEPT | Fragmento de di&aacute;logo |
| `Ella habia` | CONCEPT | Inicio de oraci&oacute;n |
| `Sofia + Miguel` | CONCEPT | Anotaci&oacute;n del autor |
| `Decisiones dificiles` | CONCEPT | T&iacute;tulo de cap&iacute;tulo |
| `Tres dias` | CONCEPT | Marcador temporal |
| `Miguel discutian` | CHARACTER (alias) | Verbo adjuntado al nombre |

### 4.2 Tipos de entidad incorrectos

| Entidad | Tipo asignado | Correcto |
|---------|--------------|----------|
| `Garc&iacute;a` | LOCATION | CHARACTER (apellido) |
| `Asi` | LOCATION | No es entidad |

### 4.3 Confianza siempre 0.00

Todas las entidades reportan `confidence=0.00` y `mention_count=0`, lo que indica que los metadatos de entidades no se est&aacute;n calculando o persistiendo.

### 4.4 Importancia no refleja la realidad

Mar&iacute;a (protagonista en varios textos) frecuentemente aparece como `SECONDARY`, mientras que personajes menores aparecen como `PRIMARY`.

### 4.5 Fusi&oacute;n de entidades incompleta

- `Mar&iacute;a` y `Maria` (con/sin tilde) NO se fusionan como misma entidad
- `hermanos Garc&iacute;a` no se relaciona con `Miguel`, `Sof&iacute;a`, `Pedro`
- Muchos alias incorrectos: `Pedro segun`, `Miguel discutian`

---

## 5. EXTRACCI&Oacute;N DE ATRIBUTOS

### 5.1 Atributos misatribuidos

En `prueba_inconsistencias_personajes.txt` (con ground truth):

| Atributo extra&iacute;do | Problema |
|--------------------------|----------|
| `Mar&iacute;a.BUILD = fornido` | INCORRECTO: fornido es de Juan, no de Mar&iacute;a |
| `Juan.HAIR_COLOR = rubio` | INCORRECTO: el cabello rubio es de Mar&iacute;a |
| `del.PROFESSION = m&eacute;dico` | INCORRECTO: la entidad "del" no existe; es Pedro |
| `vestido.COLOR = azul` | INCORRECTO: "vestido" no es un personaje |
| `Barba.OTHER = mencionada` | INCORRECTO: "Barba" no es una entidad |

### 5.2 Atributos absurdos en otros documentos

| Atributo | Problema |
|----------|----------|
| `Tres dias.EYE_COLOR = verdes` | "Tres d&iacute;as" no es una entidad con ojos |
| `deteccion.OTHER = automatica` | No es una entidad |
| `habia.OTHER = pegamento` | "hab&iacute;a" no es una entidad |
| `Andres.PROFESSION = fantastico` | "fant&aacute;stico" no es una profesi&oacute;n |
| `Capitulo.OTHER = escrito` | T&iacute;tulo tratado como entidad |
| `+.OTHER = epilogo` | El s&iacute;mbolo "+" tratado como entidad |
| `mi.OTHER = miguel--` | Pronombre tratado como entidad |

### 5.3 Atributos correctos encontrados (parcial)

Solo en `prueba_inconsistencias_personajes.txt` se extrajeron algunos atributos reales:
- `Mar&iacute;a.EYE_COLOR = azules` &check;
- `Mar&iacute;a.HAIR_COLOR = negro` &check;
- `Mar&iacute;a.HAIR_TYPE = largo` &check;
- `Mar&iacute;a.HEIGHT = alta` &check; y `bajo` &check; (detecta ambos)
- `Juan.EYE_COLOR = marrones` &check;
- `Juan.HEIGHT = bajo` &check;
- `Juan.BUILD = fornido` &check;
- `Pedro.EYE_COLOR = verdes` &check; y `azules` &check;
- `Pedro.HAIR_COLOR = canoso` &check;

Pero esto solo funciona parcialmente y con muchos atributos basura mezclados.

---

## 6. DETECCI&Oacute;N DE INCONSISTENCIAS

### 6.1 Resultados en `prueba_inconsistencias_personajes.txt`

**Inconsistencias esperadas**: 15+ (documentadas en el archivo)
**Inconsistencias detectadas**: 2

| Detectada | Esperada |
|-----------|----------|
| &check; `Mar&iacute;a.HEIGHT: alta vs bajo` | &check; |
| &check; `Pedro.EYE_COLOR: verdes vs azules` | &check; |
| &cross; Cabello Mar&iacute;a: negro &rarr; rubio &rarr; casta&ntilde;o | No detectada |
| &cross; Profesi&oacute;n Mar&iacute;a: literatura &rarr; matem&aacute;ticas | No detectada |
| &cross; Bebida Mar&iacute;a: t&eacute; verde &rarr; espreso | No detectada |
| &cross; Barba Juan: espesa &rarr; afeitado | No detectada |
| &cross; Edad Juan: 35 &rarr; 38 &rarr; 40 | No detectada |
| &cross; Chocolate Juan: favorito &rarr; al&eacute;rgico | No detectada |
| &cross; Profesi&oacute;n Juan: carpintero &rarr; abogado | No detectada |
| &cross; Barba Pedro: inexistente &rarr; pelirroja | No detectada |
| &cross; Pelo Elena: pelirroja &rarr; negro &rarr; rubio | No detectada |
| &cross; Todas las temporales | No detectadas |
| &cross; Perfume Mar&iacute;a: floral &rarr; c&iacute;tricos | No detectada |

**Tasa de detecci&oacute;n: ~13% (2/15)**

### 6.2 Resultados en `prueba_inconsistencias_temporales.txt`

**Inconsistencias esperadas**: 15 (documentadas)
**Inconsistencias detectadas**: 0

**Tasa de detecci&oacute;n: 0%**

Nota: `run_temporal_consistency=False` en perfil standard. Pero incluso con temporal activado, no se generan alertas de consistencia temporal.

---

## 7. ESTRUCTURA Y CAP&Iacute;TULOS

### 7.1 Detecci&oacute;n parcial

En `prueba_capitulos_estructura.txt` (10 cap&iacute;tulos esperados con distintos formatos):
- Detecta 12 "cap&iacute;tulos" (incluye metadata y FIN como cap&iacute;tulos extra)
- NO separa "CAPITULO III / Revelaciones" como cap&iacute;tulo independiente (queda dentro del contenido del cap&iacute;tulo 4)
- NO detecta "Capitulo Cinco:" como separador de cap&iacute;tulo
- N&uacute;meros de cap&iacute;tulo duplicados (dos cap&iacute;tulos con number=4)
- Cap&iacute;tulos con contenido vac&iacute;o (PARTS como "SEGUNDA PARTE: EL VIAJE" con 0 palabras)

### 7.2 Todos los cap&iacute;tulos reportan number=0

El campo `number` de los cap&iacute;tulos se muestra siempre como 0 en las entidades, sugiriendo un problema de mapeo.

### 7.3 Metadata incluida como cap&iacute;tulo

Secciones como "LISTA DE INCONSISTENCIAS INTENCIONADAS:" y "RESUMEN DE ESTRUCTURA ESPERADA:" se tratan como cap&iacute;tulos reales, contaminando el an&aacute;lisis.

---

## 8. REPETICIONES

### 8.1 Nombres propios como repeticiones

Los nombres de personajes (Mar&iacute;a x10, Juan x13, Ana x11) se marcan como repeticiones l&eacute;xicas. En narrativa, repetir nombres de personajes es normal y necesario.

### 8.2 Anotaciones del autor incluidas

Las notas al final del documento ("Notas del autor: Este texto contiene...") se analizan junto con la narrativa, generando falsos positivos en repeticiones, ortograf&iacute;a y gram&aacute;tica.

---

## 9. COHERENCIA NARRATIVA

### 9.1 Alertas vagas

Todas las alertas de coherencia dicen: "Posible discontinuidad narrativa entre segmentos" sin especificar qu&eacute; tipo de ruptura o por qu&eacute;.

### 9.2 Falsos positivos en l&iacute;mites de cap&iacute;tulo

Los cambios normales entre cap&iacute;tulos se detectan como "saltos de coherencia", lo cual es esperado en narrativa estructurada.

---

## 10. RENDIMIENTO

| Documento | Tama&ntilde;o | Tiempo |
|-----------|--------|--------|
| manuscrito_prueba_errores.txt | 2.5 KB | 121s |
| prueba_capitulos_estructura.txt | 3.4 KB | 83s |
| prueba_correferencias_complejas.txt | 6.1 KB | 131s |
| prueba_focalizacion_sentimiento.txt | 5.7 KB | ~130s |

**~100-130 segundos para documentos de 2-6 KB** es excesivamente lento. Para documentos reales (100+ KB), esto ser&iacute;a impracticable sin optimizaci&oacute;n.

---

## 11. RESUMEN DE PRIORIDADES

### Severidad CR&Iacute;TICA (impide el uso)

1. **Fix coreference call**: Pasar `config=CorefConfig(...)` en vez de `use_llm=`
2. **Fix attribute persistence**: Usar `attr.key` en vez de `attr.attribute_type`
3. **Fix emotional coherence**: Manejar retorno `list` o wrappear en `Result`
4. **Fix "Espacios m&uacute;ltiples"**: Excluir `\n\n` del regex `\s{2,}`
5. **Fix "May&uacute;scula innecesaria"**: Filtrar nombres propios y post-punto

### Severidad ALTA (reduce calidad significativamente)

6. **Instalar diccionario Hunspell espa&ntilde;ol**: Sugerencias ortogr&aacute;ficas absurdas sin &eacute;l
7. **Filtrar entidades falsas**: Validar que tokens de NER no sean fragmentos de di&aacute;logo o verbos
8. **Mejorar atribuci&oacute;n de atributos**: Los atributos se asignan a la entidad equivocada con frecuencia
9. **Deduplicar alertas gramaticales**: El detector custom y LanguageTool generan alertas duplicadas
10. **Excluir metadata/anotaciones**: Las notas del autor no deber&iacute;an analizarse

### Severidad MEDIA (mejoras importantes)

11. **Habilitar temporal_consistency en standard**: Actualmente `False`, pero es una funcionalidad core
12. **Mejorar detecci&oacute;n de cap&iacute;tulos**: Soportar n&uacute;meros romanos, "Capitulo Cinco:", etc.
13. **Confidence y mention_count**: Siempre 0.00/0, calcular valores reales
14. **Importancia de entidades**: No refleja la realidad del texto
15. **Excluir nombres propios de repeticiones**: O al menos reducir su severidad
16. **Mejorar mensajes de coherencia**: Especificar qu&eacute; tipo de ruptura en vez de mensaje gen&eacute;rico
17. **Fusi&oacute;n de entidades con/sin tilde**: "Mar&iacute;a" y "Maria" deber&iacute;an fusionarse

### Severidad BAJA (nice-to-have)

18. **Rendimiento**: 100-130s para 2-6 KB es muy lento
19. **Roman numerals**: "III" no deber&iacute;a ser "letras repetidas"
20. **Sticky sentences**: El porcentaje de palabras funcionales se muestra como 0% o 1% (parece un bug de c&aacute;lculo)
