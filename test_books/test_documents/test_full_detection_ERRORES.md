# Errores Deliberados en test_full_detection.txt

Documento de prueba diseñado para disparar los 36 módulos de detección.
Cada error está documentado con su ubicación y el módulo que debería detectarlo.

---

## 1. Inconsistencias de Atributos Físicos
**Módulo**: `attribute_consistency.py`

| Personaje | Atributo | Cap 1 | Cap contradictorio | Tipo |
|-----------|----------|-------|-------------------|------|
| Elena | Ojos | verdes (cap 1) | azules (cap 3) | COLOR_ANTONYM |
| Elena | Cabello | castaño (cap 1) | rubio (cap 7) | COLOR_CHANGE |
| Elena | Edad | 32 años (cap 1) | 28 años (cap 7) | AGE_INCONSISTENCY |
| Carlos | Complexión | bajo y robusto (cap 1) | alto y delgado (cap 5) | BUILD_ANTONYM |
| Carlos | Complexión | alto y delgado (cap 5) | estatura media, normal (cap 8) | BUILD_CHANGE |
| Don Ramiro | Edad | 70 años (cap 1) | 85 años (cap 3) | AGE_JUMP |
| Don Ramiro | Edad | 85 años (cap 3) | 63 años (cap 8) | AGE_INCONSISTENCY |
| Isabel | Cabello | pelirroja (cap 1) | cabello negro (cap 8) | COLOR_CHANGE |
| Isabel | Ojos | ojos claros (cap 1) | ojos oscuros (cap 8) | COLOR_ANTONYM |

## 2. Estado Vital (Personaje muerto reaparece)
**Módulo**: `vital_status.py`

- **Isabel**: Muere en cap 3 (envenenamiento confirmado por forense) → reaparece viva en cap 6
- Tipo: DIRECT death → revival sin explicación sobrenatural válida
- La "explicación" de Isabel (cap 6) es narrativamente incoherente

## 3. Inconsistencia de Localización
**Módulo**: `character_location.py`

- **Carlos cap 3**: Está en Madrid comprando herramientas el mismo día del hallazgo
- **Carlos cap 6**: "seguía detenido en la comisaría" Y "estaba en la mansión cuando Isabel llegó" simultáneamente
- Tipo: SIMULTANEOUS_PRESENCE

## 4. Anacronismos
**Módulo**: `temporal/anachronisms.py`

| Objeto/Tecnología | Capítulo | Año historia | Año invención |
|-------------------|----------|--------------|---------------|
| Teléfono móvil | Cap 2 | 1923 | ~1983 |
| GPS | Cap 2 | 1923 | ~1995 |
| Móvil (Don Ramiro) | Cap 4 | 1923 | ~1983 |
| Radio en coche | Cap 8 | 1923 | ~1930 (limitado) |
| Autopista | Cap 8 | 1923 | ~1950s en España |

## 5. Problemas de Ritmo/Pacing
**Módulo**: `pacing.py`

- **Cap 2**: Descripción estilo telegrama (8 frases cortas consecutivas: "El edificio era de piedra. Las ventanas eran grandes...")
- **Cap 2**: Monólogo excesivamente largo de Carlos (parlamento de 10+ líneas sin interrupción)
- **Cap 5**: Capítulo desequilibrado (mucho texto sin diálogo)
- **Cap 8**: Párrafo duplicado del cap 2 (copy-paste)
- **Cap 9**: Capítulo extremadamente corto vs. otros

## 6. Contenido Duplicado
**Módulo**: `duplicate_detector.py`

- **Copia exacta**: "La mansión Aldebarán se encontraba en lo alto de una colina. El edificio era de piedra..." aparece IDÉNTICO en cap 2 y cap 8
- Tipo: EXACT_PARAGRAPH, severidad CRITICAL

## 7. Cambio de Registro
**Módulo**: `voice/register.py`

- **Don Ramiro cap 4**: Pasa de registro FORMAL_LITERARY a COLLOQUIAL extremo: "Oye, tía, mira lo que he pillao... Mola, ¿no? ...colega"
- El narrador lo señala como anómalo (meta-error)

## 8. Out-of-Character / Fuera de Personaje
**Módulo**: `out_of_character.py`

- **Don Ramiro cap 4**: Habla con jerga juvenil (contradicción total con su perfil formal establecido en cap 1)
- Tipo: SPEECH_REGISTER deviation
- **Carlos cap 5**: Descrito como "visiblemente furioso" pero actúa con "calma absoluta" y "sonrisa amplia"
- Tipo: EMOTION_SHIFT

## 9. Incoherencia Emocional
**Módulo**: `emotional_coherence.py`

- **Carlos cap 5**: Furioso → inmediatamente sonríe y ofrece café con total tranquilidad
- Tipo: EMOTION_DIALOGUE mismatch
- Sin transición ni justificación narrativa

## 10. Repeticiones Excesivas
**Módulo**: `style/repetition_detector.py`

- **Cap 2**: "Realmente" x5 en un párrafo (repetición léxica)
- **Cap 4**: "La detective..." x5 frases consecutivas (repetición estructural)
- **Cap 5**: "pueblo" x8 en un párrafo (repetición léxica extrema)
- **Cap 7**: "El farmacéutico" x4 frases consecutivas (repetición léxica + estructural)
- **Cap 8**: "silencio/silencioso" x5 en dos frases (repetición léxica)

## 11. Muletillas / Filler Words
**Módulo**: `style/filler_detector.py`

- **Cap 2**: "Realmente" x5 (WEAK_ADVERB)
- **Cap 4**: "O sea" x3 + "básicamente" + "en fin" (LINGUISTIC + CONNECTOR)

## 12. Frases Pegajosas (Sticky Sentences)
**Módulo**: `style/sticky_sentences.py`

- **Cap 7**: "De eso de lo que se trataba era de que no era otra cosa sino la que era en sí misma una de las cosas que en el fondo no eran sino lo que parecían ser..." (~90% glue words)
- **Cap 7**: "La solución al enigma residía en que la solución al enigma..." (circular, alta densidad de glue words)

## 13. Frases de Baja Energía
**Módulo**: `style/sentence_energy.py`

- **Cap 2**: 8 frases consecutivas con verbo "era/eran" (WEAK_VERB)
- **Cap 7**: 5 frases en voz pasiva consecutivas: "Era fue hecho por...", "La investigación era llevada a cabo...", "Las pruebas fueron recopiladas...", "Los testimonios fueron organizados...", "Una decisión fue tomada..."

## 14. Falta de Variación Sensorial
**Módulo**: `style/sensory_report.py`

- Todo el documento es predominantemente VISUAL
- Muy pocas referencias a sonidos, olores, texturas, sabores
- Cap 1 y 2: Solo descripciones visuales (colores, formas, tamaños)

## 15. Rupturas de Coherencia
**Módulo**: `style/coherence_detector.py`

- **Cap 7**: Cambio abrupto de POV: "Yo sabía que la clave..." (1ª persona) → "Elena repasó las notas" (3ª persona)
- Tipo: POV_SHIFT sin transición

## 16. Prolepsis (Flash-forward / Spoiler)
**Módulo**: `narrative_structure.py`

- **Cap 5**: "en el capítulo siguiente Isabel aparecería viva y coleando, lo cual arruinaría toda la investigación" — spoiler explícito del giro
- Tipo: PROLEPSIS no intencionada

## 17. Errores de Ortografía
**Módulo**: `orthography/` + alertas

| Error | Correcto | Capítulo | Línea aprox |
|-------|----------|----------|-------------|
| inposible | imposible | Cap 6 | Isabel habla |
| tienpo | tiempo | Cap 6 | Isabel habla |
| a estado | ha estado | Cap 6 | Elena pregunta |
| Hiva | Iba | Cap 6 | Isabel habla |
| avia | había | Cap 6 | Narración |

## 18. Errores Gramaticales
**Módulo**: `grammar/`

- **Cap 7**: "Era fue hecho por ella misma la reconstrucción" — concordancia rota + doble verbo
- **Cap 6**: "a estado" — confusión a/ha (preposición vs auxiliar)

## 19. Redundancia Semántica
**Módulo**: `semantic_redundancy.py`

- **Cap 7**: "La solución al enigma residía en que la solución al enigma no era otra que la respuesta al misterio que constituía el enigma cuya solución buscaban" — misma idea expresada 3 veces
- **Cap 8**: "El silencio era tan silencioso que se podía oír el silencio" — tautología

## 20. Variación de Longitud de Frase
**Módulo**: `SentenceVariationTab`

- **Cap 2**: 8 frases de longitud casi idéntica (~6 palabras cada una): "El edificio era de piedra. Las ventanas eran grandes. El tejado era de pizarra..."
- **Cap 4**: 5 frases con la misma estructura "La detective [verbo] [objeto]"

## 21. Inconsistencia Temporal
**Módulo**: `temporal/timeline.py`

- **Cap 7**: Don Ramiro dice que Isabel desapareció un jueves, pero el diario indica martes → contradicción temporal explícita

## 22. Desbalance de Capítulos
**Módulo**: `pacing.py` + `narrative_health.py`

- Cap 9 (epílogo): ~70 palabras — extremadamente corto
- Cap 2 y 7: mucho más largos — desequilibrio notable

---

## Resumen por Módulo

| Módulo | Errores esperados | Caps afectados |
|--------|------------------|----------------|
| attribute_consistency | 9 inconsistencias | 1,3,5,7,8 |
| vital_status | 1 muerte+revival | 3,6 |
| character_location | 2 ubicaciones imposibles | 3,6 |
| anachronisms | 5 anacronismos | 2,4,8 |
| pacing | 4+ problemas ritmo | 2,5,8,9 |
| duplicate_detector | 1 párrafo copiado | 2,8 |
| register | 1 cambio registro | 4 |
| out_of_character | 2 desviaciones | 4,5 |
| emotional_coherence | 1 incoherencia | 5 |
| repetition_detector | 5+ patrones | 2,4,5,7,8 |
| filler_detector | 2 clusters | 2,4 |
| sticky_sentences | 2 frases | 7 |
| sentence_energy | 2 clusters pasivos | 2,7 |
| sensory_report | desbalance global | todos |
| coherence_detector | 1 POV shift | 7 |
| narrative_structure | 1 prolepsis | 5 |
| orthography | 5 errores | 6 |
| grammar | 2 errores | 6,7 |
| semantic_redundancy | 2 redundancias | 7,8 |
| sentence_variation | 2 clusters monótonos | 2,4 |
| timeline | 1 contradicción | 7 |
| narrative_health | desbalance caps | 2,7,9 |

**Total**: 50+ errores detectables en 22 categorías distintas.
