# Test Books - Corpus de Pruebas para Narrative Assistant

Esta carpeta contiene libros de prueba organizados por tipo de documento para validar
el clasificador automático y las diferentes funciones de análisis de Narrative Assistant.

**IMPORTANTE**: Esta carpeta NO se sube al repositorio (está en `.gitignore`).
Los libros deben descargarse manualmente de fuentes de dominio público.

## Estructura de carpetas

La estructura refleja los tipos de documento soportados por el clasificador
(`src/narrative_assistant/parsers/document_classifier.py`) y los perfiles de features
(`src/narrative_assistant/feature_profile/models.py`).

```
test_books/
├── 01_ficcion/          # FICTION (FIC) - Novela, relatos
├── 02_memorias/         # MEMOIR (MEM) - Autobiografías
├── 03_biografia/        # BIOGRAPHY (BIO) - Biografías de terceros
├── 04_famosos/          # CELEBRITY (CEL) - Influencers, deportistas
├── 05_divulgacion/      # DIVULGATION (DIV) - Divulgación científica/histórica
├── 06_ensayo/           # ESSAY (ENS) - Ensayo académico/literario
├── 07_autoayuda/        # SELF_HELP (AUT) - Desarrollo personal
├── 08_tecnico/          # TECHNICAL (TEC) - Manuales técnicos
├── 09_practico/         # PRACTICAL (PRA) - Cocina, DIY, guías
├── 10_grafico/          # GRAPHIC (GRA) - Cómic, manga
├── 11_infantil/         # CHILDREN (INF) - Literatura infantil/juvenil
├── 12_teatro_guion/     # DRAMA (DRA) - Teatro, guiones
└── test_documents/      # Documentos sintéticos para tests unitarios
```

## Fuentes de libros en dominio público

### Español
- **Biblioteca Virtual Miguel de Cervantes**: https://www.cervantesvirtual.com/
- **Project Gutenberg (español)**: https://www.gutenberg.org/browse/languages/es
- **Feedbooks Public Domain**: https://www.feedbooks.com/publicdomain
- **Standard Ebooks**: https://standardebooks.org/

### Formatos recomendados
Incluir cada libro en múltiples formatos cuando sea posible:
- `.docx` - Para probar el parser de Word
- `.txt` - Texto plano UTF-8
- `.epub` - Para probar el parser de EPUB
- `.pdf` - Para probar el parser de PDF

---

## Libros sugeridos por categoría

### 01_ficcion/ - Ficción narrativa

#### literaria/ (FIC_LIT)
- **Don Quijote de la Mancha** - Miguel de Cervantes ✓ (incluido)
- **La Regenta** - Leopoldo Alas "Clarín" ✓ (incluido)
- **Lazarillo de Tormes** - Anónimo ✓ (incluido)
- **Fortunata y Jacinta** - Benito Pérez Galdós
- **La familia de Pascual Duarte** - Camilo José Cela
- **Niebla** - Miguel de Unamuno

#### genero/ (FIC_GEN)
- **El capitán Alatriste** - Arturo Pérez-Reverte (thriller histórico)
- **La sombra del viento** - Carlos Ruiz Zafón (misterio)
- Cualquier novela de género: romance, ciencia ficción, fantasía, thriller

#### historica/ (FIC_HIS)
- **Episodios Nacionales** - Benito Pérez Galdós
- **El hereje** - Miguel Delibes
- Novelas ambientadas en épocas históricas con vocabulario de época

#### relatos/ (FIC_COR)
- **Novelas ejemplares** - Miguel de Cervantes ✓ (incluido)
- **Cuentos** - Emilia Pardo Bazán
- **El Aleph** - Jorge Luis Borges

#### microrrelatos/ (FIC_MIC)
- **Dinosaurio** - Augusto Monterroso
- Colecciones de microrrelatos contemporáneos

### 02_memorias/ - Memorias y autobiografías

#### autobiografia/ (MEM_AUT)
- **Confieso que he vivido** - Pablo Neruda
- **Vivir para contarla** - Gabriel García Márquez

#### parciales/ (MEM_PAR)
- **Recuerdos de niñez y de mocedad** - Miguel de Unamuno

#### diarios/ (MEM_DIA)
- **Diario de un poeta recién casado** - Juan Ramón Jiménez

### 03_biografia/ - Biografías

#### autorizada/ (BIO_AUT)
- Biografías autorizadas de escritores, artistas

#### historica/ (BIO_HIS)
- **Vida de Don Quijote y Sancho** - Miguel de Unamuno (meta-biografía)
- Biografías de personajes históricos

### 04_famosos/ - Libros de celebridades

- Libros de deportistas, influencers, youtubers
- Buscar en librerías secciones "no ficción" / "biografías"

### 05_divulgacion/ - Divulgación

#### cientifica/ (DIV_CIE)
- **Breve historia del tiempo** - Stephen Hawking (español)
- **El gen egoísta** - Richard Dawkins
- Libros de divulgación científica traducidos

#### historica/ (DIV_HIS)
- **Sapiens** - Yuval Noah Harari (español)
- Libros de divulgación histórica

### 06_ensayo/ - Ensayos

#### academico/ (ENS_ACA)
- Artículos académicos, papers
- Tesis doctorales (muchas disponibles en repositorios universitarios)

#### literario/ (ENS_LIT)
- **Del sentimiento trágico de la vida** - Miguel de Unamuno
- **Meditaciones del Quijote** - José Ortega y Gasset

#### filosofico/ (ENS_FIL)
- **La rebelión de las masas** - José Ortega y Gasset
- Ensayos filosóficos clásicos

### 07_autoayuda/ - Desarrollo personal

- **El poder del ahora** - Eckhart Tolle (español)
- Libros de productividad, coaching, bienestar

### 08_tecnico/ - Manuales técnicos

- Documentación de software
- Manuales de usuario
- Guías técnicas

### 09_practico/ - Libros prácticos

#### cocina/ (PRA_COC)
- **1080 recetas de cocina** - Simone Ortega
- Libros de recetas con ingredientes y pasos

#### jardineria/ (PRA_JAR)
- Guías de jardinería, huerto urbano

#### manualidades/ (PRA_MAN)
- Libros de DIY, bricolaje, costura

### 10_grafico/ - Novela gráfica

- **Arrugas** - Paco Roca
- **El arte de volar** - Antonio Altarriba
- Cómics con guión en texto extraíble

### 11_infantil/ - Literatura infantil/juvenil

#### cartone_0-3/ (INF_CAR)
- Libros de cartón para bebés (poco texto)

#### album_3-5/ (INF_ALB)
- **¿A qué sabe la luna?** - Michael Grejniec
- Álbumes ilustrados

#### primeras_lecturas_5-8/ (INF_PRI)
- **El pequeño Nicolás** - René Goscinny

#### middle_grade_8-12/ (INF_MID)
- **Manolito Gafotas** - Elvira Lindo
- **Harry Potter** (español)

#### young_adult_12+/ (INF_YA)
- Novelas juveniles contemporáneas

### 12_teatro_guion/ - Teatro y guiones

#### teatro/ (DRA_TEA)
- **La casa de Bernarda Alba** - Federico García Lorca
- **Don Juan Tenorio** - José Zorrilla
- **La vida es sueño** - Pedro Calderón de la Barca

#### cine_tv/ (DRA_GUI)
- Guiones de películas españolas
- Formato: INT./EXT., sluglines, acotaciones

---

## test_documents/ - Documentos sintéticos

Documentos creados específicamente para probar funciones del análisis:

- `test_simple.txt` - Texto mínimo con inconsistencias obvias
- `test_document.txt` - Texto corto con cambios de atributos
- `test_document_rich.txt` - Texto más largo con múltiples inconsistencias:
  - Cambios de color de ojos (azules → verdes → azules)
  - Cambios de color de pelo (negro → rubio → negro)
  - Cambios de altura (bajo → alto)
  - Cambios de edad (30 → 50 años)

Estos documentos están diseñados para:
1. Probar detección de entidades (María, Juan, Madrid)
2. Probar detección de atributos (ojos, pelo, altura, edad)
3. Probar alertas de inconsistencia
4. Probar fusión semántica

---

## Cómo añadir libros

1. Descargar el libro de una fuente legal (dominio público o con permiso)
2. Colocarlo en la subcarpeta correspondiente
3. Renombrar con formato: `titulo_autor.ext` (sin espacios, usar guiones bajos)
4. Si es posible, incluir múltiples formatos del mismo libro

## Ejecutar tests con el corpus

```bash
# Probar clasificador con todos los libros
python -m pytest tests/evaluation/test_document_classifier.py -v

# Probar análisis completo
python -m pytest tests/integration/test_full_analysis.py -v

# Ver estadísticas del corpus
python scripts/corpus_stats.py
```
