# Referencias

[← Volver al índice principal](../../README.md)

---

## Bibliografía Académica

Este sistema se fundamenta en teoría narratológica establecida para definir qué constituye un "problema" narrativo, y en técnicas de NLP probadas para la implementación técnica.

---

### Narratología y Teoría Literaria

| Referencia | Concepto clave | Uso en el sistema |
|------------|----------------|-------------------|
| Genette, G. (1972). *Figures III*. Seuil. | Focalización, tiempo narrativo | Definición de tipos de focalización y análisis temporal |
| Genette, G. (1983). *Nouveau discours du récit*. Seuil. | Ampliación de conceptos narratológicos | Refinamiento de categorías |
| Booth, W. C. (1961). *The Rhetoric of Fiction*. University of Chicago Press. | Fiabilidad del narrador | Modelo de no fiabilidad narrativa |
| Phelan, J. (2005). *Living to Tell about It*. Cornell University Press. | Ejes de no fiabilidad | Clasificación de tipos de narrador no fiable |
| Bal, M. (2009). *Narratology: Introduction to the Theory of Narrative*. University of Toronto Press. | Narratología general | Marco teórico general |

---

### NLP y Procesamiento de Texto Literario

| Referencia | Concepto clave | Uso en el sistema |
|------------|----------------|-------------------|
| Bamman, D., Underwood, T., & Smith, N. A. (2014). A Bayesian Mixed Effects Model of Literary Character. *ACL*. | Análisis de personajes | Inspiración para fichas de personaje |
| Elson, D. K., Dames, N., & McKeown, K. R. (2010). Extracting Social Networks from Literary Fiction. *ACL*. | Redes de personajes | Relaciones entre entidades |
| Chambers, N., & Jurafsky, D. (2008). Unsupervised Learning of Narrative Event Chains. *ACL*. | Cadenas de eventos | Inspiración para timeline |
| Bamman, D., Popat, S., & Shen, S. (2019). An Annotated Dataset of Literary Entities. *NAACL*. | LitBank corpus | Referencia para evaluación de NER literario |

---

### Correferencia y Resolución de Entidades

| Referencia | Concepto clave | Uso en el sistema |
|------------|----------------|-------------------|
| Kirstain, Y., Ram, O., & Levy, O. (2021). Coreference Resolution without Span Representations. *ACL*. | s2e-coref | Arquitectura candidata para Fase 2C |
| Otmazgin, S., et al. (2022). LingMess: Linguistically Informed Multi-Expert Scoring for Coreference Resolution. *EACL*. | LingMess | Arquitectura alternativa |
| Dobrovolskii, V. (2021). Word-Level Coreference Resolution. *EMNLP*. | wl-coref | Modelo base para fine-tuning |
| Taulé, M., Martí, M. A., & Recasens, M. (2008). AnCora: Multilevel Annotated Corpora for Catalan and Spanish. *LREC*. | AnCora corpus | Datos de entrenamiento para coref español |

---

### Herramientas Relacionadas (Antecedentes)

| Referencia | Descripción | Relación con el sistema |
|------------|-------------|------------------------|
| Bamman, D. (2021). BookNLP. GitHub. | Pipeline NLP para libros (inglés) | Antecedente más cercano; nuestro sistema es para español y offline |
| Honnibal, M., & Montani, I. (2017). spaCy 2. GitHub. | Biblioteca NLP | Componente técnico central (NER, parsing) |
| Wolf, T., et al. (2020). Transformers: State-of-the-Art NLP. *EMNLP*. | Hugging Face Transformers | Infraestructura para embeddings y modelos |

---

### Estilometría y Análisis de Estilo

| Referencia | Concepto clave | Uso en el sistema |
|------------|----------------|-------------------|
| Burrows, J. (2002). Delta: A Measure of Stylistic Difference. *LLC*. | Medidas de distancia estilística | Inspiración para perfiles de voz |
| Eder, M., Rybicki, J., & Kestemont, M. (2016). Stylometry with R: A Package for Computational Text Analysis. *R Journal*. | Métricas estilométricas | TTR, MATTR, Yule's K |

---

### Embeddings y Similitud Semántica

| Referencia | Concepto clave | Uso en el sistema |
|------------|----------------|-------------------|
| Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. *EMNLP*. | Sentence embeddings | Base teórica para similitud semántica |
| Chen, Q., et al. (2024). BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity. *arXiv*. | bge-m3 | Embeddings multilingües (considerar en Fase 2) |

---

### Modelos de Lenguaje para Español

| Referencia | Modelo | Uso en el sistema |
|------------|--------|-------------------|
| Cañete, J., et al. (2020). Spanish Pre-Trained BERT Model and Evaluation Data. *PML4DC at ICLR*. | BETO | Encoder para modelo coref propio |
| Gutiérrez-Fandiño, A., et al. (2022). MarIA: Spanish Language Models. *Procesamiento del Lenguaje Natural*. | MarIA | Alternativa a BETO |

---

## Diferenciación del Sistema

**BookNLP** (Bamman, 2021) es el antecedente técnico más cercano, pero:

1. Solo funciona para inglés
2. Requiere conexión para algunos componentes
3. No está diseñado para el flujo de trabajo de correctores profesionales

Este sistema llena un vacío: **análisis narrativo con IA, para español, 100% offline, orientado a correctores profesionales**.

---

## Documentos de esta Sección

| Documento | Descripción |
|-----------|-------------|
| [Glosario](./glossary.md) | Definiciones de términos clave |

---

## Volver

[← Índice principal](../../README.md)
