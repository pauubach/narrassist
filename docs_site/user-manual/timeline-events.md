# Timeline y Eventos

Visualización temporal del manuscrito y detección de contradicciones cronológicas.

---

## Timeline del Manuscrito

La **línea temporal** muestra los eventos clave del manuscrito en orden cronológico, ayudándote a detectar inconsistencias de fechas, edades y secuencias.

### Vista de Timeline

```
Día 1  │ María conoce a Juan en el hospital
Día 3  │ Primera cita en la cafetería
Día 7  │ Juan le propone matrimonio  ⚠️
Día 10 │ Boda                         ⚠️
```

!!! warning "Alerta de Timeline"
    **Matrimonio muy rápido**: Desde que se conocen hasta la boda pasan solo 10 días. ¿Es intencional?

---

## Eventos Narrativos

Los **eventos** son acontecimientos clave que el sistema detecta automáticamente:

### Tipos de Eventos

| Tipo | Descripción | Ejemplos |
|------|-------------|----------|
| **Encuentro** | Personajes se conocen | "María conoció a Juan" |
| **Muerte** | Fallecimiento | "El abuelo murió en mayo" |
| **Nacimiento** | Nuevo personaje nace | "Nació el hijo de María" |
| **Viaje** | Cambio de ubicación | "Viajaron a París" |
| **Decisión** | Punto de giro | "María renunció al hospital" |
| **Revelación** | Información nueva | "Descubrieron el secreto" |

### Ver Eventos

1. Abre **Vista de Timeline**
2. Los eventos aparecen como **puntos** en la línea temporal
3. Haz clic en un evento para ver **detalles y contexto**

---

## Detección de Contradicciones Temporales

### Tipos de Contradicciones

=== "Edades Incoherentes"
    **Problema**: Edad del personaje no concuerda con el tiempo transcurrido.

    **Ejemplo**:
    - Cap. 3: "María tiene 25 años"
    - Cap. 12: "María tiene 30 años"
    - Tiempo transcurrido en historia: 2 meses

    **¿Por qué es problema?**: No pueden pasar 5 años en 2 meses.

=== "Fechas Imposibles"
    **Problema**: Secuencia de fechas que no tiene sentido.

    **Ejemplo**:
    - "Nació el 15 de marzo de 1990"
    - "Su cumpleaños número 20 fue el 10 de abril de 2010"

    **¿Por qué es problema?**: Debería cumplir 20 años el 15 de marzo de 2010, no el 10 de abril.

=== "Eventos Solapados"
    **Problema**: Dos eventos que no pueden ocurrir simultáneamente.

    **Ejemplo**:
    - Cap. 5: "María estaba en Madrid el lunes 10"
    - Cap. 5: "Ese mismo día, María atendió una urgencia en Barcelona"

    **¿Por qué es problema?**: No puede estar en dos ciudades a la vez.

===  "Secuencia Imposible"
    **Problema**: Causa ocurre después del efecto.

    **Ejemplo**:
    - Cap. 3: "María lloró la muerte de su padre"
    - Cap. 8: "El padre de María murió repentinamente"

    **¿Por qué es problema?**: No puede llorar su muerte antes de que ocurra.

---

## Inspector de Capítulos

Herramienta para revisar la cronología capítulo por capítulo.

### Información Mostrada

- **Fecha estimada** del capítulo
- **Duración** de tiempo transcurrido
- **Eventos clave** que ocurren
- **Personajes** que aparecen
- **Alertas temporales** relacionadas

### Uso

1. Abre **Inspector** desde la barra de herramientas
2. Navega por capítulos usando flechas
3. Revisa información temporal
4. Compara con capítulos anteriores/posteriores

---

## Validación de Secuencias

El sistema valida automáticamente que:

- ✅ Las **edades** sean coherentes con fechas de nacimiento
- ✅ Los **eventos** ocurran en orden lógico
- ✅ Las **ubicaciones** sean alcanzables en el tiempo disponible
- ✅ Los **estados vitales** sean consistentes (no aparece vivo tras morir)

### Ejemplo de Validación

!!! success "Secuencia Válida"
    ```
    01/03/2010 │ María nace
    15/03/2030 │ María cumple 20 años
    20/06/2035 │ María se casa a los 25 años
    ```

!!! danger "Secuencia Inválida"
    ```
    01/03/2010 │ María nace
    15/03/2025 │ María cumple 20 años  ⚠️ Debería ser 15 años
    ```

---

## Consejos

!!! tip "Timeline Complejo"
    Si tu manuscrito tiene **saltos temporales** o **narrativa no lineal**, puedes:

    1. Marcar capítulos con **flashbacks** en configuración
    2. Indicar **líneas temporales paralelas**
    3. El sistema ajustará la validación

!!! tip "Marcadores Temporales"
    El sistema detecta automáticamente frases como:
    - "Tres días después..."
    - "Un mes más tarde..."
    - "Al día siguiente..."

    Asegúrate de usarlas consistentemente.

---

## Próximos Pasos

- [Colecciones y Sagas](collections-sagas.md)
- [Configuración](settings.md)
