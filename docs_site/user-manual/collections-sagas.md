# Colecciones y Sagas

Análisis de **múltiples libros** de una serie para detectar inconsistencias entre tomos.

---

## ¿Qué es una Colección?

Una **colección** agrupa varios libros de una misma saga, trilogía o serie para analizar la **coherencia cross-book** (entre libros).

!!! example "Ejemplos de Uso"
    - Trilogía de fantasía: ¿Los personajes mantienen sus características?
    - Serie de novelas policíacas: ¿El detective mantiene su pasado coherente?
    - Saga familiar: ¿Las relaciones entre generaciones son consistentes?

---

## Crear una Colección

1. Ve a **Colecciones** en el menú principal
2. Haz clic en **"Nueva Colección"**
3. Completa:
    - **Nombre**: "El Reino Olvidado - Trilogía"
    - **Descripción**: Breve sinopsis de la saga
4. Añade libros:
    - Arrastra proyectos existentes
    - O importa nuevos documentos directamente

---

## Vincular Entidades Entre Libros

El paso más importante: indicar qué personajes/lugares son **los mismos** en diferentes libros.

### Cómo Vincular

1. Abre una colección
2. Ve a **"Vínculos de Entidades"**
3. Selecciona un personaje del Libro 1
4. Haz clic en **"Vincular con..."**
5. Selecciona el mismo personaje en Libro 2/3
6. Confirma

!!! example "Ejemplo"
    ```
    Libro 1: "María González" (médica, 25 años, ojos azules)
       ↕
    Libro 2: "Dra. González" (cirujana, 30 años)
       ↕
    Libro 3: "María" (directora hospital, 35 años)
    ```

    Al vincularlas, el sistema las trata como **la misma persona** y valida que los atributos evolucionen coherentemente.

---

## Análisis Cross-Book

Una vez vinculados los personajes, el sistema analiza:

### Inconsistencias de Atributos

=== "Físicos"
    **Ejemplo de Inconsistencia**:

    - Libro 1: "ojos azules"
    - Libro 3: "ojos verdes"

    ⚠️ **Problema**: Los ojos no cambian de color (salvo fantasía/ciencia ficción).

=== "Profesionales"
    **Ejemplo de Evolución Coherente**:

    - Libro 1: "médica residente"
    - Libro 2: "cirujana"
    - Libro 3: "directora de hospital"

    ✅ **Correcto**: Progresión profesional lógica.

=== "Relacionales"
    **Ejemplo de Inconsistencia**:

    - Libro 1: "su hermano Juan"
    - Libro 3: "su primo Juan"

    ⚠️ **Problema**: El parentesco no puede cambiar.

### Contradicciones de Eventos

El sistema detecta si un evento clave se describe de **forma diferente** en distintos libros.

!!! danger "Ejemplo"
    **Libro 1, Cap. 5**:
    > "María y Juan se conocieron en una conferencia médica en 2015."

    **Libro 3, Cap. 12** (flashback):
    > "Recordó cuando conoció a Juan en el hospital, en 2014."

    ⚠️ **Problema**: Lugar y fecha contradictorios.

---

## Reporte de Colección

### Contenido del Reporte

1. **Resumen General**
    - Número de libros analizados
    - Total de entidades vinculadas
    - Inconsistencias detectadas

2. **Inconsistencias por Personaje**
    - Atributos que cambian sin justificación
    - Eventos contradictorios

3. **Inconsistencias por Libro**
    - Qué libro tiene más problemas de coherencia
    - Capítulos específicos con contradicciones

### Exportar Reporte

- **PDF**: Informe imprimible completo
- **Excel**: Tabla de inconsistencias para seguimiento
- **HTML**: Reporte interactivo navegable

---

## Navegación al Texto Fuente

Desde el reporte, puedes **hacer clic** en cualquier inconsistencia para:

1. Ver el texto exacto en cada libro
2. Navegar al capítulo y línea específica
3. Comparar las dos versiones lado a lado

!!! tip "Ventana Comparativa"
    El sistema abre una **vista dividida** mostrando ambos libros en paralelo para que puedas comparar fácilmente.

---

## Casos de Uso

### Saga de Fantasía (3 tomos)

**Problema común**: Personaje secundario aparece en Libro 1 con descripción detallada, en Libro 3 reaparece con características diferentes.

**Solución**: Vincula el personaje en ambos libros, el sistema te alertará de las diferencias.

### Serie Policíaca (10+ libros)

**Problema común**: El detective menciona un evento de su pasado que contradice lo narrado en libro anterior.

**Solución**: El sistema mantiene un "registro" de todos los eventos mencionados y te alerta si hay contradicción.

### Trilogía Romántica

**Problema común**: Relación entre personajes cambia (de enemigos a amigos sin justificación).

**Solución**: El sistema detecta cambios abruptos de relación y te pide confirmar si es intencional.

---

## Limitaciones

!!! warning "Ten en cuenta"
    - **Requiere vinculación manual**: Debes indicar qué personajes son los mismos
    - **No detecta cambios sutiles de personalidad**: Solo atributos explícitos
    - **Saltos temporales grandes**: Si entre libros pasan décadas, algunos cambios son esperables

---

## Consejos

!!! tip "Vincula Solo Principales"
    No necesitas vincular **todos** los personajes secundarios. Enfócate en los principales y aquellos que reaparecen significativamente.

!!! tip "Documenta Cambios Intencionales"
    Si un personaje cambia radicalmente entre libros **a propósito** (ej: tras trauma, magia, etc.), añade una nota en la colección para recordarlo.

!!! tip "Revisa Antes de Publicar"
    Ejecuta el análisis de colección **antes de enviar el segundo/tercer libro a imprenta** para detectar inconsistencias a tiempo.

---

## Próximos Pasos

- [Configuración](settings.md)
- [Casos de Uso](use-cases.md)
