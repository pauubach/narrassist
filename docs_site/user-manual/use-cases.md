# Casos de Uso

Ejemplos prácticos de cómo usar Narrative Assistant en diferentes escenarios.

---

## Novela de Ficción: Detectar Inconsistencias de Personajes

### Escenario

Estás escribiendo una novela de 400 páginas con 15 personajes principales. Quieres asegurarte de que no hay contradicciones en sus descripciones, relaciones y evolución.

### Flujo de Trabajo

1. **Importa** tu manuscrito completo
2. **Aplica** el preset "Novela"
3. **Analiza** el documento
4. **Revisa** alertas de categoría "Personajes"
5. **Fusiona** menciones duplicadas (ej: "María" y "Mari")
6. **Verifica** atributos de personajes principales:
    - Edad coherente con timeline
    - Descripción física consistente
    - Relaciones sin contradicciones
7. **Corrige** en tu editor
8. **Reanaliza** hasta eliminar todas las alertas críticas

### Resultado Esperado

- ✅ Sin contradicciones de edad
- ✅ Descripciones físicas coherentes
- ✅ Relaciones bien definidas
- ✅ Timeline lógica

---

## Libro Técnico: Validar Terminología Consistente

### Escenario

Escribes un manual técnico de 200 páginas. Necesitas asegurarte de que usas los términos técnicos de forma consistente a lo largo del libro.

### Flujo de Trabajo

1. **Importa** el manual
2. **Aplica** preset "Técnico"
3. **Analiza**
4. **Revisa** alertas de categoría "Terminología"
5. **Verifica** que:
    - Los acrónimos se definen en primera aparición
    - Los términos técnicos no cambian (ej: no usar "servidor" y "server" indistintamente)
    - Las referencias a secciones anteriores son correctas
6. **Crea reglas** para términos específicos de tu dominio
7. **Exporta** glosario de términos para referencia

### Resultado Esperado

- ✅ Terminología unificada
- ✅ Acrónimos definidos
- ✅ Sin mezcla de idiomas en términos técnicos

---

## Saga de Fantasía: Coherencia Entre Tomos

### Escenario

Has escrito una trilogía de fantasía. Quieres asegurarte de que los personajes, lugares y eventos son coherentes entre los tres libros.

### Flujo de Trabajo

1. **Crea** una colección "Mi Trilogía"
2. **Importa** los tres libros como proyectos separados
3. **Vincula** los personajes principales entre libros:
    - Tomo 1: "Elara, la maga" → Tomo 2: "Elara" → Tomo 3: "Maestra Elara"
4. **Ejecuta** análisis de colección
5. **Revisa** reporte de inconsistencias cross-book:
    - ¿Cambió el color de ojos de Elara?
    - ¿La descripción del castillo es la misma?
    - ¿Los eventos clave se narran igual en los flashbacks?
6. **Corrige** contradicciones
7. **Genera** reporte final para llevar un registro

### Resultado Esperado

- ✅ Personajes coherentes entre tomos
- ✅ Lugares descritos consistentemente
- ✅ Eventos clave sin contradicciones

---

## Memoria/Biografía: Cronología Correcta

### Escenario

Escribes tus memorias cubriendo 40 años de vida. Necesitas asegurarte de que todas las fechas y edades son correctas.

### Flujo de Trabajo

1. **Importa** el manuscrito
2. **Aplica** preset "Memoria"
3. **Analiza** con sensibilidad "Alta" para timeline
4. **Revisa** alertas de cronología:
    - Edades en cada evento
    - Secuencia de acontecimientos
    - Fechas coherentes
5. **Usa** el inspector de timeline para verificar capítulo por capítulo
6. **Corrige** discrepancias
7. **Valida** que eventos históricos reales coincidan con fechas

### Resultado Esperado

- ✅ Todas las edades correctas
- ✅ Fechas sin contradicciones
- ✅ Secuencia cronológica lógica
- ✅ Coherencia con eventos históricos reales

---

## Novela Policíaca (Serie): Mantener Coherencia del Detective

### Escenario

Escribes el 5º libro de una serie policíaca. El detective protagonista tiene un pasado complejo que has ido revelando en libros anteriores. Quieres asegurarte de no contradecir nada.

### Flujo de Trabajo

1. **Crea** colección con los 5 libros
2. **Vincula** al detective en todos los libros
3. **Revisa** ficha completa del personaje:
    - Atributos acumulados de los 5 libros
    - Relaciones establecidas
    - Eventos de su pasado mencionados
4. **Verifica** que el nuevo libro no contradice nada
5. **Añade** manualmente cualquier dato nuevo importante a su ficha
6. **Exporta** la ficha del detective como referencia para futuros libros

### Resultado Esperado

- ✅ Pasado del detective coherente
- ✅ Sin contradicciones con libros anteriores
- ✅ Ficha de personaje completa para referencia

---

## Corrección Editorial: Revisión Rápida Pre-Publicación

### Escenario

Eres corrector profesional. El autor te envía un manuscrito de 300 páginas que debe publicarse en 2 semanas. Necesitas detectar inconsistencias rápidamente.

### Flujo de Trabajo

1. **Importa** el manuscrito del autor
2. **Analiza** con preset según género
3. **Prioriza**:
    - Primero: Alertas críticas (muerte, edad, hechos)
    - Segundo: Alertas altas (relaciones, timeline)
    - Después: Calidad (solo si hay tiempo)
4. **Genera** informe para el autor con:
    - Inconsistencias detectadas
    - Sugerencias de corrección
    - Capítulos y líneas específicas
5. **Exporta** a PDF y envía al autor
6. **Tras correcciones**: Reanaliza para verificar que se resolvieron

### Resultado Esperado

- ✅ Informe profesional de inconsistencias
- ✅ Ahorro de tiempo vs. lectura manual
- ✅ Detección de problemas que fácilmente se pasan por alto

---

## Consejos Generales

!!! tip "Usa el Sistema Como Complemento"
    Narrative Assistant detecta inconsistencias **objetivas** (edad, fechas, hechos). No sustituye la lectura atenta para detectar problemas de estilo, tono o calidad literaria.

!!! tip "Combina con Otras Herramientas"
    - **Narrative Assistant**: Inconsistencias narrativas
    - **Antidote/LanguageTool**: Ortografía y gramática
    - **ProWritingAid**: Estilo y legibilidad

!!! tip "Guarda Versiones"
    Antes de hacer correcciones masivas basadas en alertas, guarda una copia del manuscrito por si necesitas revertir cambios.

---

## Próximos Pasos

- Volver al [Índice del Manual](../index.md)
- Ver [Configuración Avanzada](settings.md)
- Consultar [FAQ](../../FAQ.md)
