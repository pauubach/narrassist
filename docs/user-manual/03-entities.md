# 3. Gestión de Entidades

Las **entidades** son los elementos clave de tu manuscrito: personajes, lugares, organizaciones, objetos, eventos. Narrative Assistant las detecta automáticamente y te permite gestionarlas.

---

## Tipos de Entidades

| Tipo | Descripción | Ejemplos |
|------|-------------|----------|
| **PER** (Persona) | Personajes principales y secundarios | María González, Dr. López, El Inspector |
| **LOC** (Lugar) | Ubicaciones geográficas | Madrid, Hospital Central, Cafetería "El Sol" |
| **ORG** (Organización) | Empresas, instituciones, grupos | Ministerio de Salud, ONG Esperanza, Policía |
| **EVENT** | Acontecimientos narrativos | Boda de María, Incendio del hospital |
| **OBJECT** | Objetos relevantes | Espada mágica, Diario secreto |
| **OTHER** | Otros conceptos | Amor, Justicia, Democracia |

---

## Vista de Entidades (EntitiesTab)

### Acceder

1. Abre un proyecto analizado
2. Haz clic en **"Entidades"** en la barra lateral

### Interfaz

```
┌─────────────────────────────────────────────────────┐
│ 🔍 [Buscar entidades...]                            │
│ Filtros: [Tipo▼] [Menciones▼] [Atributos▼]         │
├─────────────────────────────────────────────────────┤
│ Entidad          │ Tipo │ Menciones │ Atributos     │
├──────────────────┼──────┼───────────┼───────────────┤
│ María González   │ PER  │ 145       │ edad:25, rol  │
│ Juan Pérez       │ PER  │ 89        │ edad:30       │
│ Madrid           │ LOC  │ 34        │ país          │
│ Hospital Central │ LOC  │ 67        │ tipo          │
└─────────────────────────────────────────────────────┘
```

---

## Editar Entidades

### Cambiar Nombre o Tipo

1. **Selecciona** una entidad de la lista
2. Haz clic en **"Editar"** (icono lápiz)
3. Modifica:
   - **Nombre**: Nombre canónico (ej: "María González" en vez de "Mari")
   - **Tipo**: PER, LOC, ORG, EVENT, OBJECT, OTHER
4. Haz clic en **"Guardar"**

**Ejemplo de uso**:
- Cambiar "El doctor" → "Dr. López" (nombre más específico)
- Cambiar tipo: "Esperanza" (PER) → "Esperanza" (ORG) si es una ONG

### Ver Menciones

Las **menciones** son todas las apariciones de una entidad en el texto.

1. **Selecciona** una entidad
2. Haz clic en **"Ver Menciones"**
3. Verás lista con contexto:

```
Capítulo 3, línea 145:
"María salió del hospital cansada."

Capítulo 5, línea 289:
"La doctora González revisó los análisis."

Capítulo 12, línea 892:
"Mari decidió renunciar."
```

**Nota**: Si ves menciones de entidades diferentes (María ≠ Mari), **fusiónalas** (ver siguiente sección).

---

## Fusionar Entidades Duplicadas

El sistema NER a veces detecta la misma entidad con nombres ligeramente distintos:

- María, Mari, Sra. González, La doctora → **Mismo personaje**
- Juan, Sr. Pérez, El ingeniero → **Mismo personaje**

### Cómo Fusionar

1. **Selecciona** la entidad **primaria** (la que quieres mantener)
2. Haz clic en **"Fusionar"**
3. Selecciona las entidades **secundarias** (duplicados)
4. Confirma

**Resultado**:
- Todas las menciones se transfieren a la entidad primaria
- Atributos se combinan
- Entidades secundarias se eliminan

**Ejemplo**:
```
Antes:
- María González (145 menciones)
- Mari (23 menciones)
- La doctora (12 menciones)

Después de fusionar:
- María González (180 menciones) ✅
```

**Tip**: Fusionar duplicados **mejora la precisión** de alertas de inconsistencia.

---

## Atributos de Entidades

Los **atributos** son características extraídas automáticamente:

### Atributos de Personajes (PER)

| Categoría | Ejemplos |
|-----------|----------|
| **Físicos** | edad, altura, color_ojos, color_pelo, complexión |
| **Profesionales** | profesión, ocupación, rango |
| **Relacionales** | padre_de, hermano_de, esposo_de |
| **Emocionales** | estado_ánimo, personalidad |
| **Temporales** | fecha_nacimiento, fecha_muerte |

### Ver Atributos

1. **Selecciona** un personaje
2. Haz clic en **"Ver Detalles"**
3. Verás tabla de atributos:

```
┌──────────────┬───────────────────┬────────────┐
│ Atributo     │ Valor             │ Confianza  │
├──────────────┼───────────────────┼────────────┤
│ edad         │ 25 años           │ 95%        │
│ profesión    │ médica            │ 90%        │
│ color_ojos   │ azules            │ 85%        │
│ estado_civil │ soltera → casada  │ 80%        │
└──────────────┴───────────────────┴────────────┘
```

### Editar Atributos

#### Editar Existente

1. Haz clic en el **valor** del atributo
2. Modifica el texto
3. Presiona **Enter** o haz clic fuera

#### Añadir Nuevo

1. Haz clic en **"Añadir Atributo"**
2. Completa:
   - **Categoría**: physical, professional, relational, emotional, temporal
   - **Nombre**: color_ojos, profesión, hermano_de, etc.
   - **Valor**: El valor específico
3. Haz clic en **"Guardar"**

#### Eliminar

1. Haz clic en **icono de papelera** junto al atributo
2. Confirma

**Ejemplo de uso**:
Si el sistema no detectó que "Juan es ingeniero", puedes añadirlo manualmente:
```
Categoría: professional
Nombre: profesión
Valor: ingeniero
```

---

## Relaciones entre Entidades

Las **relaciones** conectan entidades entre sí:

- María **hermana_de** Juan
- Madrid **capital_de** España
- Juan **trabaja_en** Hospital Central

### Ver Relaciones

1. **Selecciona** un personaje
2. Ve a la pestaña **"Relaciones"**
3. Verás grafo de relaciones:

```
        María González
         │
    ┌────┼────┐
    │         │
hermana_de  trabaja_en
    │         │
   Juan    Hospital Central
```

### Añadir Relación

1. Desde los detalles de entidad, haz clic en **"Añadir Relación"**
2. Completa:
   - **Tipo**: hermano_de, trabaja_en, vive_en, etc.
   - **Entidad destino**: Selecciona de la lista
3. Haz clic en **"Guardar"**

---

## Filtros y Búsqueda

### Filtro por Tipo

Muestra solo entidades de un tipo específico:
- `PER` → Solo personajes
- `LOC` → Solo lugares
- `ORG` → Solo organizaciones

### Filtro por Menciones

Filtra por frecuencia de aparición:
- `> 50 menciones` → Personajes principales
- `10-50 menciones` → Personajes secundarios
- `< 10 menciones` → Personajes menores

**Tip**: Personajes con < 3 menciones a menudo son falsos positivos (nombres comunes mal detectados).

### Búsqueda de Texto

Busca por nombre:
```
🔍 [María]  →  Encuentra: María González, María Pérez, Mari
```

---

## Ocultar Entidades Irrelevantes

Si el sistema detectó entidades que no son relevantes para tu análisis:

1. **Selecciona** la entidad
2. Haz clic en **"Ocultar"**
3. Confirma

**Resultado**: La entidad ya no aparece en listas ni genera alertas.

**Uso común**:
- Nombres comunes detectados incorrectamente ("Lunes", "Marzo")
- Personajes muy menores sin importancia narrativa
- Marcas o nombres propios genéricos

**Nota**: Ocultar NO elimina, solo filtra de la vista.

---

## Exportar Lista de Entidades

Para usar en otras herramientas (Scrivener, hojas de cálculo, etc.):

1. Haz clic en **"Exportar"**
2. Selecciona formato:
   - **CSV**: Hoja de cálculo (Excel, Google Sheets)
   - **JSON**: Programático
   - **Markdown**: Fichas de personajes legibles
3. Elige ubicación y guarda

**Ejemplo de export Markdown**:
```markdown
# Personajes - El Reino Olvidado

## María González
- **Tipo**: Personaje principal
- **Menciones**: 145
- **Atributos**:
  - Edad: 25 años
  - Profesión: Médica
  - Ojos: Azules
- **Relaciones**:
  - Hermana de Juan Pérez
  - Trabaja en Hospital Central
```

---

## Casos de Uso Comunes

### Detectar Personajes Sin Caracterización

**Problema**: Personaje con muchas menciones pero sin atributos físicos/emocionales.

**Solución**:
1. Filtrar por `Menciones > 20`
2. Ordenar por `Atributos` (ascendente)
3. Revisar personajes con 0-2 atributos
4. Añadir descripción en el manuscrito

### Encontrar Personajes con Nombres Similares

**Problema**: "Juan", "Juanito", "Sr. Pérez" son el mismo personaje pero no fusionados.

**Solución**:
1. Buscar `Juan` en barra de búsqueda
2. Revisar resultados
3. Fusionar duplicados

### Verificar Consistencia de Relaciones

**Problema**: En cap. 5 dice "hermano", en cap. 20 dice "primo".

**Solución**:
1. Abrir relaciones de entidad
2. Revisar tipo de relación
3. Si hay conflicto, aparecerá alerta en AlertsDashboard

---

## Próximos Pasos

- **Trabajar con Alertas**: [Capítulo 4](04-alerts.md)
- **Timeline y Eventos**: [Capítulo 5](05-timeline-events.md)
- **Configuración**: [Capítulo 7](07-settings.md)

---

**Tip**: Dedica tiempo a limpiar entidades al inicio. Una base de entidades bien fusionada genera alertas mucho más precisas.
