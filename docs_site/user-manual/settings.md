# Configuración

Ajusta el comportamiento del análisis según el tipo de manuscrito y tus preferencias.

---

## Presets por Género

Los **presets** son configuraciones predefinidas optimizadas para diferentes tipos de manuscritos.

### Presets Disponibles

| Preset | Descripción | Optimizado Para |
|--------|-------------|-----------------|
| **Novela** | Ficción narrativa | Personajes, diálogos, timeline |
| **Técnico** | Libros técnicos | Terminología, acrónimos, sin diálogos |
| **Jurídico** | Textos legales | Registro formal, precisión |
| **Memoria** | Biografías | Timeline estricto, coherencia temporal |
| **Infantil** | Literatura infantil | Vocabulario simple, legibilidad |
| **Ensayo** | Ensayos, artículos | Coherencia argumental |

### Aplicar Preset

1. Ve a **Configuración** → **Presets**
2. Selecciona el preset más adecuado
3. Haz clic en **"Aplicar"**
4. El sistema ajustará automáticamente todos los parámetros

!!! tip "Personalizar Tras Preset"
    Puedes aplicar un preset y luego **ajustar manualmente** los parámetros específicos que necesites.

---

## Ajustes de Corrección

### Sensibilidad de Detección

Control de cuán estricto es el sistema al detectar problemas.

=== "Baja"
    Solo alertas **muy evidentes**.

    **Uso**: Manuscritos experimentales, fantasía/ciencia ficción con muchas licencias narrativas.

=== "Media (Recomendada)"
    Balance entre precisión y falsos positivos.

    **Uso**: Novelas estándar, no ficción.

=== "Alta"
    Detecta incluso **posibles** inconsistencias.

    **Uso**: Textos técnicos, memorias, donde la precisión es crítica.

### Categorías de Análisis

Activa/desactiva tipos específicos de análisis:

- ☑️ **Detección de Personajes**: Atributos, relaciones
- ☑️ **Análisis de Timeline**: Fechas, edades, secuencias
- ☑️ **Validación de Diálogos**: Hablantes, registro
- ☑️ **Calidad de Texto**: Repeticiones, muletillas
- ☑️ **Ortografía/Gramática**: Errores básicos

!!! warning "Desactivar con Cuidado"
    Desactivar categorías reduce el tiempo de análisis pero puede hacer que pases por alto problemas importantes.

---

## Modelos Avanzados (Ollama)

Para usuarios avanzados que quieran usar análisis semántico profundo.

### ¿Qué es Ollama?

Sistema que ejecuta **modelos de lenguaje** (como ChatGPT) pero **en tu propio ordenador**, sin enviar datos a internet.

### Modelos Disponibles

| Modelo | Tamaño | Velocidad | Calidad | Requisitos |
|--------|--------|-----------|---------|------------|
| **llama3.2** | Pequeño | ⚡⚡⚡ | ⭐⭐ | 8 GB RAM |
| **qwen2.5** | Mediano | ⚡⚡ | ⭐⭐⭐ | 16 GB RAM |
| **mistral** | Grande | ⚡ | ⭐⭐⭐ | 16 GB RAM |

### Configurar Ollama

!!! info "Instalación Automática"
    Narrative Assistant puede instalar Ollama automáticamente:

    1. Ve a **Configuración** → **Modelos Avanzados**
    2. Haz clic en **"Instalar Ollama"**
    3. Selecciona modelo recomendado (**llama3.2**)
    4. Espera la descarga (~ 2 GB, una sola vez)

!!! warning "Opcional"
    El uso de Ollama es **completamente opcional**. El sistema funciona perfectamente sin él, solo con menor profundidad en algunos análisis semánticos.

---

## Exportación y Backup

### Configuración de Exportación

- **Formato preferido**: DOCX, PDF, CSV
- **Incluir resueltas**: ¿Exportar también alertas ya resueltas?
- **Nivel de detalle**: Resumido o completo

### Backup Automático

Configura copias de seguridad automáticas:

1. **Frecuencia**: Diaria, semanal, nunca
2. **Ubicación**: Carpeta donde guardar backups
3. **Retención**: Cuántos backups mantener

!!! tip "Recomendación"
    Activa backup **semanal** con retención de 4 copias (último mes).

---

## Gestión de Datos

### Limpiar Datos

Para liberar espacio en disco:

- **Proyectos archivados**: Eliminar proyectos antiguos
- **Modelos no usados**: Desinstalar modelos Ollama que no uses
- **Caché**: Limpiar archivos temporales

### Ubicación de Datos

Por defecto, todos los datos se guardan en:

- **Windows**: `C:\Users\[usuario]\AppData\Local\Narrative Assistant\`
- **macOS**: `~/Library/Application Support/Narrative Assistant/`
- **Linux**: `~/.local/share/narrative-assistant/`

!!! warning "No Editar Manualmente"
    No modifiques archivos en estas carpetas directamente, usa siempre la interfaz de la aplicación.

---

## Idioma y Región

### Configuración Regional

- **Idioma de interfaz**: Español, Inglés
- **Variante de español**: España, México, Argentina, etc.
- **Formato de fechas**: DD/MM/AAAA o MM/DD/AAAA

!!! info "Variantes de Español"
    El sistema ajusta la detección de regionalismos según la variante seleccionada (voseo, ustedes vs. vosotros, etc.).

---

## Accesibilidad

### Opciones Disponibles

- **Tamaño de texto**: Pequeño, mediano, grande
- **Contraste alto**: Para mejor legibilidad
- **Atajos de teclado**: Personalizar combinaciones

---

## Restaurar Configuración

Si algo no funciona tras cambiar configuración:

1. Ve a **Configuración** → **Avanzado**
2. Haz clic en **"Restaurar Valores por Defecto"**
3. Confirma
4. La aplicación volverá a la configuración inicial

---

## Próximos Pasos

- [Casos de Uso](use-cases.md)
- Volver al [Índice](../index.md)
