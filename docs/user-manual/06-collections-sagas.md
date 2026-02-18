# 6. Colecciones y Sagas

Si escribes una **serie de libros**, una **trilogía** o una **saga**, necesitas coherencia no solo dentro de cada tomo, sino **entre todos ellos**. Las **Colecciones** permiten agrupar proyectos y detectar inconsistencias cross-book.

---

## ¿Qué es una Colección?

Una **Colección** es un grupo de proyectos (libros) que comparten el mismo universo narrativo:

| Concepto | Descripción | Ejemplo |
|----------|-------------|---------|
| **Colección** | Contenedor de proyectos relacionados | "Las Crónicas de Aldara" |
| **Proyecto** | Un libro individual dentro de la colección | "Tomo 1: El Despertar" |
| **Entidad vinculada** | Personaje/lugar presente en varios libros | "Elena" aparece en Tomos 1, 2 y 3 |

```
Colección: Las Crónicas de Aldara
├── Tomo 1: El Despertar        (proyecto)
├── Tomo 2: La Traición          (proyecto)
├── Tomo 3: El Retorno           (proyecto)
└── Entidades vinculadas
    ├── Elena  ──── Tomo 1, 2, 3
    ├── Lord Varen ─ Tomo 1, 2
    └── Aldara ──── Tomo 1, 2, 3
```

---

## Crear una Colección

1. Ve a la **pantalla principal** (lista de proyectos)
2. Haz clic en **"Nueva Colección"**
3. Completa el formulario:
   - **Nombre**: Nombre de la saga (ej: "Las Crónicas de Aldara")
   - **Descripción** *(opcional)*: Sinopsis general de la saga
   - **Orden**: Secuencial o cronológico
4. Haz clic en **"Crear"**

### Añadir Proyectos a la Colección

1. **Abre** la colección creada
2. Haz clic en **"Añadir Proyecto"**
3. Selecciona proyectos existentes de la lista, o crea uno nuevo
4. **Arrastra** para reordenar según el orden de lectura

> **Tip**: Analiza cada proyecto individualmente **antes** de añadirlo a la colección. Así las entidades ya estarán limpias.

---

## Vincular Entidades entre Libros

El paso más importante de una colección es **vincular** las entidades que aparecen en varios tomos. Narrative Assistant ofrece dos métodos:

### Método 1: Auto-Sugerencias (Fuzzy Matching)

Al crear una colección, el sistema compara automáticamente las entidades de todos los proyectos y sugiere vínculos:

```
Sugerencias de Vinculación
──────────────────────────────────────────────
✅ "Elena" (Tomo 1) ↔ "Elena" (Tomo 2)        Similitud: 100%
✅ "Elena" (Tomo 1) ↔ "Elena" (Tomo 3)        Similitud: 100%
⚠️ "Lord Varen" (Tomo 1) ↔ "Varen" (Tomo 2)  Similitud: 87%
⚠️ "Aldara" (Tomo 1) ↔ "La ciudad" (Tomo 2)  Similitud: 72%
❓ "El anciano" (Tomo 1) ↔ "Maestro" (Tomo 3) Similitud: 45%
```

**Acciones**:
- **Aceptar** (✅): Confirmar vínculo sugerido
- **Rechazar** (❌): Descartar sugerencia
- **Revisar** (❓): Marcar para decisión posterior

> **Nota**: El umbral de similitud por defecto es 70%. Puedes ajustarlo en Configuración → Colecciones.

### Método 2: Vinculación Manual

1. Abre la vista de **Entidades de Colección**
2. Selecciona una entidad de un tomo (ej: "Elena" en Tomo 1)
3. Haz clic en **"Vincular"**
4. Busca y selecciona la entidad equivalente en otro tomo
5. Confirma el vínculo

```
Elena (vinculada en 3 tomos)
├── Tomo 1: "Elena", 145 menciones, edad: 18
├── Tomo 2: "Elena", 203 menciones, edad: 21
└── Tomo 3: "Elena", 178 menciones, edad: 25
```

---

## Análisis Cross-Book

Una vez vinculadas las entidades, puedes ejecutar el **análisis cross-book** que detecta inconsistencias entre tomos.

### Tipos de Inconsistencias Cross-Book

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| **Atributo contradictorio** | Mismo atributo, valor diferente sin justificación | Ojos azules (T1) → Ojos verdes (T3) |
| **Muerte y reaparición** | Personaje muere en un tomo y aparece vivo después | Muere en T2, cap. 30 → Habla en T3, cap. 5 |
| **Herida sin continuidad** | Lesión grave ignorada en tomo posterior | Pierde brazo izquierdo (T1) → Usa ambos brazos (T2) |
| **Relación incoherente** | Relación cambia sin explicación | Hermanos (T1) → Primos (T3) |
| **Edad imposible** | Envejecimiento inconsistente entre tomos | 18 años (T1) → 25 años (T2), pero pasan 2 años |
| **Lugar contradictorio** | Ubicación descrita de forma diferente | Aldara al norte del río (T1) → al sur (T3) |

### Ejecutar Análisis Cross-Book

1. Abre la colección
2. Haz clic en **"Analizar Colección"**
3. Espera el proceso (compara entidades vinculadas entre todos los tomos)

```
Análisis Cross-Book: Las Crónicas de Aldara
─────────────────────────────────────────────
Comparando entidades vinculadas...
├── Elena: 3 tomos, 12 atributos → 2 inconsistencias
├── Lord Varen: 2 tomos, 8 atributos → 0 inconsistencias
├── Aldara: 3 tomos, 5 atributos → 1 inconsistencia
└── Resultados: 3 alertas cross-book generadas
```

### Ejemplo de Alerta Cross-Book

```
🔴 ALTA | Inconsistencia de Atributo entre Tomos

Tomo 1, Capítulo 8, línea 234:
"Elena lo miró con sus ojos azules, herencia de su madre."

Tomo 3, Capítulo 2, línea 45:
"Sus ojos verdes reflejaban la luz del atardecer."

⚠️ Problema: El color de ojos de Elena cambia de "azules" (Tomo 1)
a "verdes" (Tomo 3) sin justificación narrativa.

Confianza: 92%
```

---

## Flujo de Trabajo para Sagas

### Paso a Paso Recomendado

1. **Crea un proyecto** por cada tomo y analízalo individualmente
2. **Limpia entidades** en cada tomo (fusiona duplicados, corrige tipos)
3. **Crea la colección** y añade los tomos en orden
4. **Revisa sugerencias** de vinculación automática
5. **Vincula manualmente** entidades que el sistema no detectó
6. **Ejecuta análisis cross-book**
7. **Resuelve alertas** por severidad (críticas primero)
8. **Corrige en tu editor** y re-importa los tomos modificados
9. **Re-analiza** para verificar correcciones

### Diagrama del Flujo

```
Tomo 1 ──→ Analizar ──→ Limpiar entidades ──┐
Tomo 2 ──→ Analizar ──→ Limpiar entidades ──┼──→ Crear Colección
Tomo 3 ──→ Analizar ──→ Limpiar entidades ──┘         │
                                                        ▼
                                              Vincular Entidades
                                                        │
                                                        ▼
                                             Análisis Cross-Book
                                                        │
                                                        ▼
                                              Resolver Alertas
```

---

## Tips para Series Grandes (5+ Libros)

### Organización

- **Vincula primero los personajes principales** (los que aparecen en todos los tomos)
- **Deja para después** personajes que solo aparecen en un tomo
- **Crea una convención de nombres**: decide el nombre canónico antes de vincular

### Rendimiento

- **Analiza en lotes**: No añadas los 10 tomos de golpe. Empieza con 2-3 y ve ampliando
- **Usa nombres canónicos** consistentes: facilita el fuzzy matching automático

### Mantenimiento

- **Actualiza la colección** cuando termines un nuevo tomo: impórtalo, analízalo, vincúlalo
- **Revisa alertas cross-book periódicamente**: cada nuevo tomo puede revelar inconsistencias anteriores

### Checklist para Series Grandes

| Tarea | Frecuencia |
|-------|-----------|
| Fusionar duplicados en cada tomo | Al importar |
| Vincular entidades nuevas | Al añadir tomo |
| Análisis cross-book completo | Cada 2-3 tomos nuevos |
| Revisar atributos de protagonistas | Antes de cada publicación |
| Exportar reporte de colección | Al cerrar cada tomo |

---

## Exportar Reporte de Colección

Para tener un resumen completo de la saga:

1. Abre la colección
2. Haz clic en **"Exportar Reporte"**
3. Selecciona formato (PDF, Markdown, CSV)
4. El reporte incluye:
   - Lista de entidades vinculadas y sus atributos por tomo
   - Alertas cross-book activas y resueltas
   - Historial de cambios entre tomos
   - Resumen de coherencia general

---

## Próximos Pasos

- **Configurar la herramienta**: [Capítulo 7](07-settings.md)
- **Ver casos de uso detallados**: [Capítulo 8](08-use-cases.md)
- **Gestión de alertas**: [Capítulo 4](04-alerts.md)

---

**Tip**: Una saga bien vinculada es mucho más que la suma de sus partes. Invertir tiempo en vincular entidades correctamente al principio ahorra horas de revisión manual después.
