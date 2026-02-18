# Narrative Assistant

**Asistente de Corrección Narrativa para Escritores y Editores Profesionales**

---

## ¿Qué es Narrative Assistant?

Herramienta de **análisis de inconsistencias narrativas** que ayuda a escritores y editores profesionales a detectar errores de coherencia en manuscritos de cualquier género.

!!! info "Privacidad garantizada"
    Todos los modelos NLP y LLM corren localmente. **Tus manuscritos nunca salen de tu ordenador**.

---

## Características Principales

<div class="grid cards" markdown>

-   :material-account-check:{ .lg .middle } __Personajes__

    ---

    Detecta inconsistencias de atributos: edad, apariencia, profesión, relaciones.

-   :material-clock-outline:{ .lg .middle } __Timeline__

    ---

    Valida secuencias temporales, edades, fechas, eventos imposibles.

-   :material-message-text:{ .lg .middle } __Diálogos__

    ---

    Atribución de hablantes, cambios de registro, voz inconsistente.

-   :material-book-multiple:{ .lg .middle } __Sagas__

    ---

    Analiza múltiples libros y detecta contradicciones cross-book.

</div>

---

## Comenzar

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } __[Instalación](#instalacion)__

    ---

    Descarga e instala Narrative Assistant en tu sistema.

-   :material-rocket-launch:{ .lg .middle } __[Primer Análisis](user-manual/first-analysis.md)__

    ---

    Guía paso a paso para tu primer análisis de manuscrito.

-   :material-book-open-variant:{ .lg .middle } __[Manual de Usuario](user-manual/introduction.md)__

    ---

    Documentación completa de todas las funcionalidades.

-   :material-api:{ .lg .middle } __[Referencia API](api-reference/endpoints.md)__

    ---

    Documentación técnica de endpoints y servicios.

</div>

---

## Instalación

### Requisitos

- **SO**: Windows 10+, macOS 11+, Linux (Ubuntu 20.04+)
- **RAM**: 8 GB mínimo (16 GB recomendado)
- **Disco**: 5 GB libres
- **Conexión**: Solo primera vez (descarga de modelos)

### Pasos

1. **Descarga** la última versión desde [GitHub Releases](https://github.com/pauubach/narrassist/releases)

2. **Instala** según tu sistema operativo:

    === "Windows"
        ```powershell
        # Ejecuta el instalador .exe
        Narrative-Assistant-Setup-0.6.0.exe
        ```

    === "macOS"
        ```bash
        # Abre el .dmg y arrastra a Aplicaciones
        open Narrative-Assistant-0.6.0.dmg
        ```

    === "Linux"
        ```bash
        # Descarga AppImage y dale permisos
        chmod +x Narrative-Assistant-0.6.0.AppImage
        ./Narrative-Assistant-0.6.0.AppImage
        ```

3. **Primera ejecución**: Descargará modelos NLP (~1 GB, solo una vez)

---

## Formatos Soportados

| Formato | Extensión | Calidad |
|---------|-----------|---------|
| Word | `.docx` | :star::star::star: Recomendado |
| Texto plano | `.txt` | :star::star::star: |
| Markdown | `.md` | :star::star::star: |
| PDF | `.pdf` | :star::star: Solo texto |
| EPUB | `.epub` | :star::star: |

---

## Filosofía

!!! quote "Asistencia, no automatización"
    Narrative Assistant **detecta** inconsistencias, **señala** patrones sospechosos, **sugiere** qué revisar.

    **TÚ decides** si es un error real y cómo resolverlo.

---

## Recursos

- [Manual de Usuario](user-manual/introduction.md) - Guía completa
- [Referencia API](api-reference/endpoints.md) - Docs técnicas
- [FAQ](FAQ.md) - Preguntas frecuentes
- [GitHub Issues](https://github.com/pauubach/narrassist/issues) - Soporte

---

## Licencia

Narrative Assistant es software propietario. Ver [LICENSE](https://github.com/pauubach/narrassist/blob/master/LICENSE) para detalles.

---

**Versión**: v0.6.0 | **Última actualización**: 2026-02-18
