# Revisión de Expertos - Narrative Assistant v0.4.30

**Fecha**: 2026-02-03
**Versión reportada por UI**: v0.3.34 (BUG - debería ser v0.4.30)
**Documento de prueba**: test_document_fresh.txt

---

## Panel de Revisión

| Rol | Área de Expertise |
|-----|-------------------|
| **Desarrollador Backend** | API, Base de datos, Pipeline de análisis |
| **Desarrollador Frontend** | UI/UX, Componentes Vue, Visualizaciones |
| **Especialista NLP** | spaCy, Procesamiento de texto, Extracción de entidades |
| **Especialista IA/LLM** | Ollama, Análisis semántico, Clasificación |
| **Lingüista** | Análisis narrativo, Temporalidad, Estilo |
| **QA/Usuario** | Experiencia de usuario, Consistencia visual |

---

## Hallazgos Críticos

### 1. VERSIÓN INCORRECTA EN UI
**Severidad**: Alta
**Ubicación**: StatusBar / Footer
**Síntoma**: Muestra "v0.3.34" en lugar de "v0.4.30"

**Análisis Backend**:
- El fix de versión dinámica (Fix 5) se implementó pero puede no estar llegando al frontend
- Verificar endpoint `/api/version` o source de la versión en Tauri

**Análisis Frontend**:
- Revisar si `StatusBar.vue` usa versión hardcodeada o dinámica
- Posible cache del build anterior

**Acción**:
- [ ] Verificar que tauri.conf.json tiene versión correcta
- [ ] Verificar que frontend lee versión dinámicamente

---

### 2. TIMELINE TEMPORAL - Múltiples Problemas

#### 2.1 Fechas Absurdas
**Síntoma**: "Día -693952", "desde diciembre de 1"

**Análisis Lingüista**:
- -693952 días = ~1900 años antes de época actual
- Claramente un error de cálculo o parsing de fechas
- "diciembre de 1" sugiere año 1 d.C. - imposible en contexto narrativo

**Análisis NLP**:
- El extractor de fechas puede estar interpretando mal expresiones temporales
- "temprano", "aquella mañana de martes" son referencias relativas, no absolutas
- El sistema puede estar asignando una fecha base incorrecta (epoch 0?)

**Análisis Backend**:
- Revisar `TimelineAnalyzer` o servicio equivalente
- Verificar cómo se calcula la fecha base del documento
- Los días negativos sugieren resta de fechas mal manejada

**Acción**:
- [ ] Revisar extracción de expresiones temporales en NLP
- [ ] Si no hay fechas concretas, mostrar solo "8 días de historia" sin fechas
- [ ] Validar que días sean siempre >= 0

#### 2.2 Flashbacks Mal Detectados
**Síntoma**: Muestra "2 analepsis" pero pueden no ser flashbacks reales

**Análisis Lingüista**:
- "temprano" y "aquella mañana de martes" son referencias temporales normales
- No necesariamente son flashbacks (analepsis)
- Un flashback real requiere ruptura temporal significativa

**Análisis NLP**:
- El clasificador puede estar siendo muy agresivo
- Necesita contexto más amplio para determinar si hay salto temporal real

**Acción**:
- [ ] Revisar lógica de detección de analepsis
- [ ] Requerir evidencia más fuerte (cambio de tiempo verbal, indicadores explícitos)

---

### 3. ANÁLISIS DE ESTILO - Barras No Visibles

**Síntoma**:
- "poetic" 9.1% muestra barra azul
- "Coloquial" 27.3% y "Neutro" 63.6% no muestran barras

**Análisis Frontend**:
- Posible problema de CSS con barras de bajo valor vs alto valor
- O los datos no están llegando correctamente al componente

**Análisis Backend**:
- Verificar estructura de respuesta del endpoint de estilo

**Acción**:
- [ ] Revisar componente de distribución de registros
- [ ] Verificar que todas las barras se renderizan independiente del %

---

### 4. RITMO NARRATIVO - Error de Análisis

**Síntoma**: "No se pudo analizar el ritmo narrativo"

**Análisis Backend**:
- El servicio de ritmo puede no estar en la pipeline principal
- O hay un error silencioso durante el análisis

**Análisis NLP**:
- El análisis de ritmo requiere tokenización de oraciones
- Posible fallo en el procesamiento del documento

**Acción**:
- [ ] Verificar que ritmo está incluido en pipeline de análisis
- [ ] Revisar logs del backend para errores específicos
- [ ] Añadir mejor manejo de errores con mensajes descriptivos

---

### 5. EMOCIONES - Todo en 0%

**Síntoma**: Todos los valores emocionales en 0 y 0%

**Análisis NLP/IA**:
- El clasificador de emociones puede no estar ejecutándose
- O el modelo no está cargado correctamente
- Posible timeout si usa LLM

**Análisis Backend**:
- Verificar si el análisis emocional está habilitado
- Revisar configuración de Ollama para este feature

**Acción**:
- [ ] Verificar que análisis emocional se ejecuta
- [ ] Revisar logs para errores de modelo
- [ ] Considerar fallback si LLM no está disponible

---

### 6. FOCALIZACIÓN - No Declarada

**Síntoma**: "Focalización aparece sin declarar en ningún capítulo"

**Análisis Lingüista**:
- La focalización (POV) debería detectarse automáticamente
- Narrador omnisciente, primera persona, tercera limitada, etc.

**Análisis NLP**:
- Detector de POV puede no estar funcionando
- Necesita análisis de pronombres y verbos para inferir perspectiva

**Acción**:
- [ ] Revisar detector de focalización
- [ ] Implementar heurísticas básicas si no existe

---

### 7. SALUD NARRATIVA - No Detecta Personajes

**Síntoma**: "No se detectaron personajes" pero hay 3 entidades (2 personajes)

**Análisis Backend**:
- Desconexión entre entidades detectadas y módulo de salud narrativa
- El módulo de salud puede estar usando su propia detección

**Acción**:
- [ ] Hacer que salud narrativa use las entidades ya detectadas
- [ ] No duplicar detección de personajes

---

### 8. ARQUETIPOS - Pantalla Vacía

**Síntoma**: La sección de arquetipos aparece vacía

**Análisis IA**:
- Clasificación de arquetipos probablemente requiere LLM
- Puede no haberse ejecutado o falló silenciosamente

**Acción**:
- [ ] Verificar endpoint de arquetipos
- [ ] Mostrar mensaje claro si no hay datos

---

### 9. DENSIDAD - Problemas de Contraste

**Síntoma**:
- Texto blanco sobre gris
- Rojo claro sobre rojo
- Dice "crítico" pero luego dice "dentro del rango normal"

**Análisis Frontend/UX**:
- Problema de diseño de colores
- Inconsistencia en mensajes (crítico vs normal)

**Acción**:
- [ ] Revisar paleta de colores para accesibilidad
- [ ] Corregir lógica de clasificación (crítico vs normal)

---

### 10. ECOS - No Se Pudieron Analizar

**Síntoma**: Error al analizar repeticiones

**Análisis Backend**:
- Servicio de repeticiones puede tener error
- Posible problema con documentos cortos

**Acción**:
- [ ] Revisar servicio de análisis de repeticiones
- [ ] Manejar caso de documentos muy cortos

---

### 11. VARIACIÓN - Gráficas Vacías

**Síntoma**: Gráficas de variación de oraciones vacías

**Análisis Frontend**:
- Datos no están llegando al componente de gráficas
- O el formato de datos es incorrecto

**Acción**:
- [ ] Verificar endpoint de variación
- [ ] Revisar binding de datos a componente Chart

---

### 12. SENSORIAL - Requiere Análisis Manual

**Síntoma**: No se ejecuta automáticamente

**Análisis Backend**:
- Puede estar excluido de pipeline por ser costoso
- O es feature opcional

**Decisión**:
- [ ] Decidir si debe ser automático o manual
- [ ] Si manual, documentar claramente

---

### 13. UBICACIONES - Frase Cortada

**Síntoma**: "cafetería del" en lugar de ubicación completa

**Análisis NLP**:
- Extractor de ubicaciones cortando en preposición
- Debería extraer "cafetería del barrio" completo

**Acción**:
- [ ] Revisar regex/extractor de ubicaciones
- [ ] No cortar en preposiciones

---

### 14. STORY BIBLE - Carga Manual

**Síntoma**: Requiere clic manual para cargar

**Análisis**:
- Puede ser intencional (feature pesado)
- O debería cargarse con el proyecto

**Acción**:
- [ ] Decidir comportamiento esperado
- [ ] Si manual, mejorar UX con indicador claro

---

### 15. ASISTENTE - Failed to Fetch

**Síntoma**: Búsqueda termina con error "failed to fetch"

**Análisis Backend**:
- Error de red o timeout
- Endpoint puede estar caído o no implementado

**Acción**:
- [ ] Revisar endpoint del asistente
- [ ] Mejorar manejo de errores en frontend

---

### 16. RELACIONES - Sin Datos

**Síntoma**: Tab de relaciones vacío

**Análisis**:
- Detección de relaciones puede no estar ejecutándose
- O requiere más contexto del que tiene el documento de prueba

**Acción**:
- [ ] Verificar que análisis de relaciones está en pipeline
- [ ] Mostrar mensaje apropiado si no hay relaciones

---

## Plan de Acción Priorizado

### Fase 1: Críticos (Bloquean uso básico)
1. **Versión en UI** - Fix inmediato
2. **Timeline fechas absurdas** - Fix de cálculo
3. **Ritmo - Error** - Revisar pipeline
4. **Asistente failed to fetch** - Fix endpoint

### Fase 2: Altos (Afectan experiencia)
5. **Barras de estilo no visibles** - Fix CSS
6. **Emociones en 0%** - Verificar análisis
7. **Salud narrativa sin personajes** - Conectar datos
8. **Variación gráficas vacías** - Fix datos

### Fase 3: Medios (Mejoras de calidad)
9. **Flashbacks mal detectados** - Mejorar NLP
10. **Focalización no detectada** - Implementar/mejorar
11. **Densidad contraste** - Fix accesibilidad
12. **Ubicaciones cortadas** - Fix extractor

### Fase 4: Bajos (Nice to have)
13. **Ecos error** - Revisar servicio
14. **Arquetipos vacío** - Verificar LLM
15. **Sensorial manual** - Documentar
16. **Story Bible manual** - Documentar
17. **Relaciones vacío** - Verificar pipeline

---

## Métricas de Éxito

| Métrica | Estado Actual | Objetivo |
|---------|---------------|----------|
| Features funcionando sin error | ~40% | 95% |
| Análisis automático completo | Parcial | Total |
| Datos correctos en visualizaciones | Bajo | Alto |
| Mensajes de error informativos | Pobre | Excelente |

---

## Próximos Pasos

1. **Inmediato**: Investigar los 4 críticos
2. **Esta semana**: Resolver Fase 1 y 2
3. **Próxima semana**: Fase 3
4. **Backlog**: Fase 4

---

*Documento generado por revisión de expertos - Narrative Assistant*
