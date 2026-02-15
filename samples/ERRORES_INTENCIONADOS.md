# Errores intencionados en documento_prueba_completo.txt

Documento de prueba que activa todos los detectores y paneles del sistema.
~4500 palabras, 6 capitulos, 13+ personajes, 100+ errores intencionados en 61 categorias.

---

## PERSONAJES (panel Entidades + Network + Profiles + Timeline)

| Personaje | Edad | Rol | Notas |
|-----------|------|-----|-------|
| Elena Rodriguez | 34 (implica) | Investigadora, doctoranda | Protagonista |
| Dr. Martin Garcia | 58 | Director de tesis | Mentor |
| Lucia Fernandez | 27 | Companera de laboratorio | Amiga, Elena la ignora en cap. 5 |
| Carlos Mendoza | 45 | Tecnico de laboratorio | OOC x2 (caps. 3 y 5) |
| Hans Weber | ~60 | Profesor, U. Munich | Aparece cap. 3, fraude futuro |
| Padre de Elena | fallecido 2022 | Profesor de Fisica | RESUCITA en cap. 1 |
| Madre de Elena | - | - | Solo dialogos (caps. 1, 3, 6) |
| Pedro Jimenez | - | Dept. Fisica | PLANO: solo habla de laseres |
| Ana Ortiz | - | Dept. Quimica | PLANA: solo descrita como "rubia" |
| Roberto Sanz | - | Dept. Matematicas | PLANO: solo "gafas", mira telefono |
| Isabel Navarro | - | Dept. Biologia | PLANA: solo "sonrio" y asiente |
| Marta (camarera) | joven | Camarera La Tagliatella | Chekhov: aparece y desaparece |
| Maria Josefa | - | Secretaria departamento | Chekhov: aparece cap. 1, olvidada |

### Inconsistencias de atributos (AlertCategory.CONSISTENCY)
- Elena: "cabello castano" (cap. 1) vs "pelo rubio" (cap. 2 final)
- Elena: "ojos verdes" (cap. 2) - aparece tarde, sin mencion previa
- Carlos: "joven tecnico" (cap. 1) pero tiene 45 anos → edad contradictoria

### Timeline
- 15 marzo 2024: Llega al laboratorio
- 1 febrero 2024: Deadline abstract (ya pasado)
- 23 abril 2024: Congreso en Madrid
- 7 junio 2022: Muerte del padre
- Junio 2024: Cena de despedida (cap. 5) ← CONTRADICE partida en septiembre
- 1 agosto 2024: "Se habia marchado de Barcelona" (cap. 6) ← OTRA fecha
- 3 septiembre 2024: Llega a Munich (cap. 6)
- Septiembre 2024: Vuelo a Munich (cap. 3 final) ← TERCERA fecha
- ~2027: Prolepsis — fracaso del proyecto, fraude de Weber
- "setiembre" vs "septiembre" - variante ortografica

---

## ERRORES DE CONSISTENCIA NARRATIVA

### 18. VITAL STATUS — Resurreccion (vital_status.py)
- Cap. 1: "Su padre le habia dicho esa misma manana por telefono que no se preocupara"
  → El padre fallecio el 7 de junio de 2022 (cap. 3). Habla por telefono en marzo 2024.
  → **ALERT**: deceased_reappearance (CONSISTENCY)

### 19. CHARACTER LOCATION — Ubicacion imposible (character_location.py)
- Cap. 3: Lucia "habia acompanado al congreso" en Madrid (linea ~113)
- Cap. 3: "Mientras tanto, en Barcelona, Lucia estaba en el laboratorio" (linea ~145)
  → Lucia en Madrid Y Barcelona al mismo tiempo
  → **ALERT**: character_location_impossibility (WORLD)

### 20. KNOWLEDGE ASYMMETRY — Conocimiento prematuro (character_knowledge.py)
- Cap. 3: Elena piensa en "la oferta postdoctoral de Weber" ANTES de conocer a Weber
  → Weber se presenta y hace la oferta varias paginas despues
  → **ALERT**: knowledge_anachronism (CONSISTENCY)

### 21. EMOTIONAL COHERENCE — Emocion-dialogo mismatch (emotional_coherence.py)
- Cap. 3: "Elena estaba furiosa con Martin"
- Inmediatamente: "Todo va a salir maravillosamente bien, estoy encantada"
  → Furiosa pero habla con alegria y entusiasmo
  → **ALERT**: emotional_emotion_dialogue (EMOTIONAL)

### 22. OOC — Fuera de personaje (out_of_character.py)
- Carlos establecido como: "hombre callado", "voz grave", "no solia dar consejos"
- Cap. 3: Carlos grita "!!!FANTASTICO!!!", salta de alegria, abraza a todos
  → Completamente fuera del perfil establecido
  → **ALERT**: behavioral_speech_register + behavioral_action_atypical (BEHAVIORAL)

### 23. DIALOGUE — Dialogos huerfanos (dialogue.py)
- Cap. 3: "—Es la mejor noticia del ano." (sin atribucion de hablante)
- Cap. 3: "—Sin duda alguna." (sin atribucion de hablante)
  → **ALERT**: dialogue_orphan (DIALOGUE)

### 24. AGE CONTRADICTION (attribute_consistency.py)
- Cap. 1: "el joven tecnico de laboratorio" → implica <35
- Cap. 1: "Carlos tenia cuarenta y cinco anos" → 45
  → "Joven" + 45 anos = contradiccion
  → **ALERT**: attribute_inconsistency (CONSISTENCY)

### 25. NAME VARIANTS (name_variant_detector.py)
- Cap. 1: "Maria Josefa" (sin tilde) vs "María Josefa" (con tilde)
  → Mismo personaje con ortografia inconsistente del nombre
  → **ALERT**: name_variant (ENTITY)

### 26. STICKY SENTENCES / GLUE WORDS (sticky_sentences.py)
- Cap. 1: "La decision sobre el uso de los datos del analisis de las muestras de la primera fase del proyecto fue tomada por el comite de etica de la universidad."
  → >50% palabras funcionales (de, del, las, el, la, por, fue)
  → **ALERT**: sticky_sentence (STYLE)

### 27. SENTENCE ENERGY / VOZ PASIVA (sentence_energy.py)
- Cap. 1: "fue tomada por el comite" (voz pasiva)
  → Baja energia narrativa, construccion pasiva
  → **ALERT**: low_energy_sentence (STYLE)

### 28. SEMANTIC REDUNDANCY (semantic_redundancy.py)
- Cap. 2: "Elena decidio resetear todos los parametros del modelo y empezar desde cero"
- Cap. 2: "Elena opto por reiniciar la totalidad de las variables del algoritmo y comenzar el proceso nuevamente desde el principio"
  → Misma idea con palabras diferentes (>85% similitud semantica)
  → **ALERT**: semantic_duplicate (STYLE)

### 29. NON-LINEAR SIGNALS (non_linear_detector.py)
- Cap. 2: "De nina, Elena solia pasar las tardes en el despacho de su padre" (flashback)
- Cap. 2: "Anos despues recordaria aquel despacho como el lugar donde todo empezo" (flashforward)
  → Senales de analepsis y prolepsis detectadas
  → **INFO**: non_linear_signal (STRUCTURE)

### 30. CHEKHOV'S GUN (chekhov_tracker.py)
- Cap. 1: Maria Josefa, la secretaria, es introducida con detalle
- Caps. 2-3: Maria Josefa nunca mas es mencionada
  → Personaje secundario que desaparece sin resolucion
  → **ALERT**: chekhov_unfired (STRUCTURE)

### 31. REGISTER CHANGE (register.py)
- Cap. 3: Parrafo ultra-formal: "cuya trayectoria investigadora habia sido objeto de elogiosas valoraciones por parte del tribunal evaluador de la comision de posgrado"
- Inmediatamente: "Bueno, tia, que, nos pedimos unas canas o que?"
  → Salto abrupto de registro academico a coloquial
  → **ALERT**: register_change (STYLE)

### 32. SENSORY DEFICIT (sensory_report.py)
- Cap. 2 y 3: Muy pocas descripciones sensoriales (colores, olores, texturas, sonidos, sabores)
- Cap. 2 es casi 100% expositivo sin estimulos sensoriales
  → **ALERT**: low_sensory_density (STYLE)

---

## ERRORES POR CATEGORIA DE CORRECCION EDITORIAL

### 1. TYPOGRAPHY (tipografia)
- Cap. 1: Dialogo de Elena usa guion corto `- No mucho...` en vez de raya `--`
- Cap. 1: Dobles espacios despues de rayas `—.  ?Has dormido`
- Cap. 1: Doble espacio tras punto de Carlos `reemplazarlo.  El`
- Cap. 2: Comillas mezcladas: guillemets y comillas dobles en mismo parrafo
- Cap. 2: Cuatro puntos `....` en vez de puntos suspensivos
- Cap. 3: Doble espacio `—.  Esto representa`

### 2. REPETITION (repeticiones)
- Cap. 1: "laboratorio" x3 en primer parrafo
- Cap. 1: "Elena" x4 en segundo parrafo
- Cap. 1: "Lucia" x4 en parrafos consecutivos (inicio de oracion)
- Cap. 1: "Carlos" x4 en parrafos consecutivos (inicio de oracion)
- Cap. 2: "Los resultados" x4 en parrafo consecutivo
- Cap. 1: "La primera grafica... La segunda grafica... La tercera grafica..."
- Cap. 3: "Realmente... De hecho... Basicamente..." (muletillas)

### 3. AGREEMENT (concordancia)
- Cap. 1: "Los segundo muestra" (numero: segundo -> segunda)
- Cap. 1: "la calibracion del espectrometro este mal" (subjuntivo: este -> este)
- Cap. 1: "haya que reemplazarlo" (genero: la lampara -> reemplazarla)
- Cap. 1: "El mantenimiento del equipos" (numero: del equipos -> de los equipos)

### 4. GRAMMAR (gramatica)
- Cap. 1: "pienso de que tenia razon" (dequeismo)
- Cap. 1: "la dijo que no se preocupara" (laismo: la -> le)
- Cap. 1: "de que este en optimas condiciones" (dequeismo)
- Cap. 3: "dandola un abrazo" (laismo: dandola -> dandole)

### 5. CLARITY (claridad)
- Cap. 1: Frase de Martin con 70+ palabras (descripcion encadenada con "y que")
- Cap. 2: Frase de 100+ palabras sobre el problema fundamental (subordinadas anidadas)
- Cap. 2: Parrafos muy cortos de 1-2 frases intercalados

### 6. ANGLICISMS (anglicismos)
- Cap. 1: "issue", "preprocessing", "upload", "raw files", "bug", "pipeline"
- Cap. 2: "resetear", "backup", "approach", "framework", "script"
- Cap. 2: "laptop", "email", "deadline", "abstract"
- Cap. 3: "deep learning", "overfitting", "dataset"

### 7. CRUTCH_WORDS (muletillas)
- "basicamente" x4
- "realmente" x5
- "de hecho" x3
- Todas concentradas en caps. 1 y 3

### 8. ORTHOGRAPHIC VARIANTS (variantes ortograficas)
- "sicologia" (cap. 2) vs "psicologia" (cap. 2) - inconsistencia
- "setiembre" (cap. 2) vs "septiembre" (cap. 2) - inconsistencia

### 9. ANACOLUTO (rupturas sintacticas)
- Cap. 2: "Elena, que habia pasado la noche anterior sin dormir, y que ademas estaba preocupada..., y que no habia tenido tiempo de desayunar esa manana." (frase sin verbo principal — el sujeto queda colgado)

### 10. POV (punto de vista)
- Cap. 1: Cambio brusco de 3a persona a 1a persona: "Yo siempre he pensado que las graficas..." en medio de narracion en 3a persona
- Cap. 2: Mezcla tu/usted: "Tu debes entender..." + "Usted no puede esperar..."

### 11. STYLE_REGISTER (registro)
- Cap. 2: Texto academico con verbos de opinion: "Elena creia firmemente"
- Cap. 2: Cuantificadores vagos en contexto cientifico: "mejora significativa"
- Cap. 2: Primera persona en texto cientifico

### 12. REGIONAL (variantes regionales)
- Cap. 1: "cogio una silla" (Espana) + "agarro el raton" (Latinoamerica) en mismo parrafo
- Cap. 1: "ordenador" (Espana) + "computadora" (Latinoamerica) en mismo parrafo

### 13. TERMINOLOGY (terminologia)
- "ordenador" / "computadora" / "laptop" / "portatil" - 4 formas para lo mismo
- "tesis" / "investigacion" - contextos mezclados

### 14. REFERENCES (referencias)
- Cita [1] en texto y en bibliografia - OK
- Cita [3] en texto y en bibliografia - OK, pero falta [2] (salto de numeracion)
- Cita (Garcia et al., 2023) en texto pero NO en bibliografia (huerfana)
- Cita Lopez (2022) en texto pero NO en bibliografia (huerfana)
- Formato mixto: numerico [1] + autor-ano (Garcia et al., 2023) en mismo parrafo

### 15. ACRONYMS (siglas)
- "PLN" usado sin definicion previa (cap. 2 y 3)
- "IA" e "I.A." - formas inconsistentes (cap. 2)
- "OMS", "CSIC", "UNESCO" - conocidas, no deberian flaggearse
- "MIT" - usado sin definicion

### 16. COHERENCE (coherencia)
- Cap. 2: Cuatro frases seguidas empezando con "Los resultados..." (redundancia)
- Cap. 2: Parrafo sobre estructura de tesis es redundante/obvio

### 17. STRUCTURE (solo si tipo = cientifico)
- Sin seccion "Metodologia" explicita
- Sin seccion "Resultados" explicita
- Sin abstract/resumen

---

## ERRORES CAPITULOS 4-6 (nuevos)

### PERSONAJES NUEVOS (caps. 5-6)

| Personaje | Edad | Rol | Notas |
|-----------|------|-----|-------|
| Pedro Jimenez | - | Dept. Fisica | Superficial, solo habla de laseres |
| Ana Ortiz | - | Dept. Quimica | Solo "rubia", sin profundidad |
| Roberto Sanz | - | Dept. Matematicas | Solo "gafas", sin profundidad |
| Isabel Navarro | - | Dept. Biologia | Solo "sonrio", sin profundidad |
| Marta (camarera) | joven | Camarera | Aparece y desaparece (Chekhov) |

### 33. PACING — Capitulo muy corto (pacing.py)
- Cap. 4: ~200 palabras (min_chapter_words=800 para novela)
  → **ALERT**: chapter_too_short (PACING)

### 34. PACING — Capitulos desbalanceados (pacing.py)
- Cap. 4: ~200 palabras vs Cap. 5: ~800+ palabras vs Cap. 1-3: ~700-900 palabras
  → Coeficiente de variacion alto
  → **ALERT**: unbalanced_chapters (PACING)

### 35. PACING — Poco dialogo (pacing.py)
- Cap. 4: 0% dialogo — todo es narracion expositiva
  → **ALERT**: too_little_dialogue (PACING)

### 36. PACING — Bloque denso de texto (pacing.py)
- Cap. 4: Bloque narrativo sin dialogo de 200+ palabras
  → **ALERT**: dense_text_block (PACING)

### 37. PACING — Exceso de dialogo (pacing.py)
- Cap. 5: >60% de las palabras son dialogo (cena)
  → **ALERT**: too_much_dialogue (PACING)

### 38. FILLER WORDS — Muletillas linguisticas (filler_detector.py)
- Cap. 4: "en realidad" x3, "o sea" x3
- Cap. 5: "en realidad" x1, "o sea" x1
  → **ALERT**: filler_linguistic (STYLE)

### 39. FILLER WORDS — Intensificadores vacios (filler_detector.py)
- Cap. 4: "totalmente" x2, "completamente" x1, "absolutamente" x1
  → **ALERT**: filler_intensifier (STYLE)

### 40. FILLER WORDS — Coletillas (filler_detector.py)
- Cap. 4: "¿sabes?" x1, "¿no?" x1, "¿vale?" x1 (en narracion, no en dialogo)
  → **ALERT**: filler_tag_question (STYLE)

### 41. FILLER WORDS — Atenuadores (filler_detector.py)
- Cap. 4: "quizas" x2, "tal vez" x2, "un poco" x3
  → **ALERT**: filler_hedge (STYLE)

### 42. FILLER WORDS — Adverbios debiles (filler_detector.py)
- Cap. 5: "muy" x6, "bastante" x4 (en el discurso de Pedro)
  → **ALERT**: filler_weak_adverb (STYLE)

### 43. FILLER WORDS — Conectores sobreusados (filler_detector.py)
- Cap. 5: "entonces" x3, "luego" x3, "despues" x3 consecutivos
  → **ALERT**: filler_connector (STYLE)

### 44. REPETITION — Inicio de parrafo/oracion repetido (repetition)
- Cap. 4: "Era una ciudad muy..." x3, "Habia muchos..." x3
- Cap. 5: "Elena explico/dijo/comento/anadio/menciono/indico/senalo/subrayo/repitio" x9 seguidas
- Cap. 5: "Tambien llego..." x3
- Cap. 6: "Formularios para..." x7 seguidas
- Cap. 6: "Penso en..." x4 seguidas
  → **ALERT**: repetition_subject_start (STYLE)

### 45. SENTENCE LENGTH MONOTONY (sentence_energy.py)
- Cap. 4: Todas las oraciones ~8-12 palabras, sin variacion
  → "Elena tenia que escribir un informe. El informe era sobre los resultados..."
  → **ALERT**: style_sentence_length_monotony (STYLE)

### 46. WEAK VERBS (sentence_energy.py)
- Cap. 4: Abuso de "era", "estaba", "habia", "tenia" — casi sin verbos de accion
  → **ALERT**: style_weak_verb_usage (STYLE)

### 47. SHALLOW CHARACTERS — Personajes sin profundidad (character_profiling.py + narrative_health.py)
- Pedro: solo descrito como "alto", habla de laseres, sin motivacion ni arco
- Ana: solo descrita como "rubia", sin ningun dialogo relevante
- Roberto: solo descrito como "gafas", mira el telefono, sin desarrollo
- Isabel: solo descrita como "sonrio", asiente a todo, sin personalidad
  → **ALERT**: health_unbalanced_cast, archetype_mismatch (NARRATIVE)

### 48. DIALOGUE — Atribucion debil (dialogue)
- Cap. 5: 15+ lineas de dialogo usando SOLO "dijo" como verbo de atribucion
  → Sin accion beats, sin variacion (dijo, dijo, dijo, dijo...)
  → **ALERT**: dialogue_weak_attribution (DIALOGUE)

### 49. INTERACTION — Tono contradictorio con relacion (interactions)
- Cap. 5: Elena ignora a Lucia (su mejor amiga) durante toda la cena
  → Establecida como "mejor amiga" pero la trata como enemiga
  → SIN explicacion narrativa del cambio
  → Luego la abraza y le dice "eres la mejor amiga" — incoherente
  → **ALERT**: interaction_tone_mismatch, interaction_contradictory_behavior (BEHAVIORAL)

### 50. FOCALIZACION — Acceso mental no autorizado (focalization/violations.py)
- Cap. 5: Narracion en 3a persona focalizada en Elena
  → "Roberto pensaba que la cena era aburrida. Queria estar en su casa..."
  → Acceso a los pensamientos de Roberto (no es el focalizador)
  → **ALERT**: forbidden_mind_access (FOCALIZATION)

### 51. FOCALIZACION — Omniscient leak (focalization/violations.py)
- Cap. 6: "En ese mismo momento, en Barcelona, Carlos estaba limpiando el espectrometro y pensaba que..."
  → Elena esta en Munich, no puede saber que pasa en Barcelona
  → Salto a otra ubicacion + acceso mental a Carlos
  → **ALERT**: omniscient_leak (FOCALIZATION)

### 52. TEMPORAL — Inconsistencia de fecha (temporal)
- Cap. 5: "Era junio de 2024" (cena de despedida)
- Cap. 6: "Elena se habia marchado de Barcelona el primero de agosto de 2024"
  → Pero cap. 3 final: "En septiembre de 2024, Elena tomo un vuelo a Munich"
  → Tres fechas de partida: junio (cena), agosto (marcharse), septiembre (vuelo)
  → **ALERT**: temporal_inconsistency (CONSISTENCY)

### 53. PROLEPSIS / SPOILER (non_linear_detector.py)
- Cap. 6: "Tres anos despues, Elena recordaria este primer dia como el comienzo del peor error de su vida. El proyecto fracasaria estrepitosamente, Weber seria investigado por fraude academico..."
  → Prolepsis severa: revela el desenlace completo 3 anos despues
  → Destruye toda tension narrativa
  → **ALERT**: temporal_prolepsis_severe (STRUCTURE)

### 54. DUPLICATE — Parrafo duplicado exacto (duplicate_detector.py)
- Cap. 2: "Elena opto por reiniciar la totalidad de las variables del algoritmo..."
- Cap. 4: MISMA frase exacta copiada verbatim
  → Copy-paste accidental entre capitulos
  → **ALERT**: duplicate_exact_sentence (STYLE)

### 55. DUPLICATE — Repeticion de rutina (duplicate_detector.py)
- Cap. 6: "Se levantaba a las siete. Desayunaba un cafe y un bretzel. Iba al instituto en bicicleta..."
  → La misma secuencia de rutina repetida TEXTUALMENTE 2 veces consecutivas
  → **ALERT**: duplicate_near_paragraph (STYLE)

### 56. CHEKHOV'S GUN #2 — Personaje que desaparece (chekhov_tracker.py)
- Cap. 5: Marta la camarera es descrita ("joven con pelo recogido y delantal azul")
  → Solo dice "¿Desean postre?" y desaparece
  → No vuelve a mencionarse
  → **ALERT**: chekhov_unfired (STRUCTURE)

### 57. NARRATIVE HEALTH — Sin conflicto/climax (narrative_health.py)
- Cap. 4: Capitulo puramente expositivo, sin tension, sin conflicto, sin dialogo
- Cap. 6: No hay resolucion del conflicto principal (el proyecto)
  → La prolepsis dice que fracasara pero el capitulo termina con "empezaba a aburrirse"
  → **ALERT**: health_no_climax, health_no_resolution (NARRATIVE)

### 58. NARRATIVE HEALTH — Subtramas sin cerrar (narrative_health.py)
- Maria Josefa (cap. 1): introducida con detalle, nunca mas mencionada
- Resultado del espectrometro (cap. 1): ¿se arreglo? Nunca se resuelve
- La presentacion del congreso deadline pasado (cap. 2): se ignora
- Marta la camarera (cap. 5): aparece y desaparece
- Pedro/Ana/Roberto/Isabel: introducidos y olvidados
  → **ALERT**: chekhov_unfired (STRUCTURE), health_poor_coherence (NARRATIVE)

### 59. READABILITY — Nivel extremo (readability.py)
- Cap. 4: Oraciones muy simples (6-10 palabras) → INFLESZ muy alto (muy facil)
- Cap. 2: Oraciones de 100+ palabras → INFLESZ muy bajo (muy dificil)
  → Mezcla de niveles de legibilidad incompatibles
  → **ALERT**: readability metrics out of range

### 60. SENSORY DEFICIT (sensory_report.py)
- Cap. 4: CERO descripciones sensoriales (ni colores, ni olores, ni texturas, ni sonidos)
- Cap. 6: Muy pocas (solo "cielo nublado", "hacia frio")
  → **ALERT**: low_sensory_density (STYLE)

### 61. CARLOS OOC RECURRENTE (out_of_character.py + voice deviations)
- Cap. 3: Carlos grita y salta (primera vez)
- Cap. 5: Carlos "derramo una lagrima" — segunda desviacion de "hombre callado/parco"
  → Patron de OOC repetido sin desarrollo de personaje
  → **ALERT**: voice_formality_shift, behavioral_action_atypical (BEHAVIORAL)

---

## PANELES QUE DEBERIAN MOSTRAR DATOS

| Panel | Que deberia aparecer |
|-------|---------------------|
| **Texto** | 6 capitulos con highlights de alertas |
| **Alertas** | 100+ alertas de 45+ categorias |
| **Entidades** | 13+ personajes + 5 lugares (Barcelona, Madrid, Munich, Salamanca, Schwabing) + 4 orgs (MIT, UNESCO, OMS, CSIC) |
| **Relaciones** | Elena-Martin (director), Elena-Lucia (colegas→contradiccion), Elena-Carlos (colegas), Elena-Weber (postdoc), Elena-Padre (familia), Elena-Pedro/Ana/Roberto/Isabel (colegas superficiales) |
| **Timeline** | 8+ eventos: infancia (flashback), muerte padre (2022), lab (mar 2024), congreso (abr 2024), cena (jun 2024), partida (ago 2024), vuelo (sep 2024), fracaso (prolepsis 2027) |
| **Perfiles** | Elena: voz informal→contradictoria. Martin: formal. Carlos: parco→OOC x2. Lucia: bilingue. Weber: formal aleman. Pedro/Ana/Roberto/Isabel: vacios |
| **Glosario** | ordenador/computadora/laptop/portatil, sicologia/psicologia |
| **Salud narrativa** | Score MUY bajo — Chekhov's gun x3, sensory deficit, redundancia, sin climax, sin resolucion, subtramas abiertas, personajes planos |
| **Prosa** | Sticky sentences, frases largas (100+), voz pasiva, variacion baja, monotonia de longitud, verbos debiles |
| **Pacing** | Cap. 4 muy corto, desbalance, bloques densos, exceso dialogo cap. 5 |
| **Fillers** | "en realidad" x4, "o sea" x4, "totalmente" x2, "completamente" x1, "absolutamente" x1, "¿sabes?" x2, "muy" x6+, "bastante" x4+, "entonces/luego/despues" x9 |
| **Emocional** | Furia+alegria mismatch (cap. 3), frialdad con Lucia (cap. 5), tristeza (padre), nervios (congreso), apatia (cap. 6) |
| **Estado vital** | Padre: fallecido 2022, pero habla en 2024 |
| **Ubicaciones** | Lucia: Madrid y Barcelona simultaneamente (cap. 3) |
| **Conocimiento** | Elena sabe de Weber antes de conocerlo |
| **Comportamiento** | Carlos: OOC total x2 (callado→euforico, callado→lagrima). Elena: ignora a Lucia sin motivo |
| **Redundancia sem.** | Frase resetear/reiniciar duplicada entre caps. 2 y 4. Rutina repetida en cap. 6 |
| **Registro** | Salto abrupto formal academico→coloquial |
| **Focalizacion** | Roberto: acceso mental no autorizado (cap. 5). Carlos: omniscient leak desde Munich (cap. 6) |
| **Nombres** | Maria Josefa / María Josefa (tilde inconsistente) |
| **No-lineal** | Flashback (infancia) + flashforward ("anos despues") + prolepsis-spoiler (fracaso en 2027) |
| **Dialogos** | 2 huerfanos (cap. 3) + atribucion "dijo" x15 sin variacion (cap. 5) |
| **Temporal** | 3 fechas de partida contradictorias: junio, agosto, septiembre |
| **Duplicados** | Frase exacta copiada cap.2→cap.4, rutina repetida cap.6 |
| **Personajes planos** | Pedro, Ana, Roberto, Isabel: sin arco, sin profundidad, sin funcion narrativa |
