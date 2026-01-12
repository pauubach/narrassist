# Índice Optimizado para Claude Code

Este índice está diseñado para minimizar el contexto necesario al trabajar con Claude Code.

---

## Navegación Rápida

### Antes de empezar un STEP
1. Lee **solo** el STEP específico que vas a implementar
2. Consulta [enums-reference.md](./02-architecture/enums-reference.md) para valores exactos
3. Si necesitas schema: [database-schema.md](./02-architecture/database-schema.md)

### Documentos por Frecuencia de Consulta

| Frecuencia | Documento | Cuándo |
|------------|-----------|--------|
| **SIEMPRE** | [steps/README.md](./steps/README.md) | Ver dependencias y prioridades |
| **SIEMPRE** | [enums-reference.md](./02-architecture/enums-reference.md) | Valores de enums |
| **FRECUENTE** | [database-schema.md](./02-architecture/database-schema.md) | Implementar persistencia |
| **AL INICIO** | [corrections-and-risks.md](./00-overview/corrections-and-risks.md) | Expectativas NLP |
| **SI HAY DUDAS** | Heurísticas H1-H6 en `01-theory/` | Lógica de detección |

---

## Estructura Simplificada

```
docs/
├── 00-overview/          # Leer UNA VEZ al inicio
├── 01-theory/            # Consultar para heurísticas específicas
├── 02-architecture/      # Consultar según necesidad
│   ├── database-schema.md      ★ Frecuente
│   ├── enums-reference.md      ★ Muy frecuente
│   └── [otros]                 → Solo si hay problemas
├── 03-roadmap/           # Solo para planificación
├── 04-references/        # Glosario y bibliografía
└── steps/                # ★ Principal para implementación
    ├── phase-0/  P0 Setup
    ├── phase-1/  P0 Parser + NER
    ├── phase-2/  P0 Coref + Atributos
    ├── phase-3/  P1-P2 Repeticiones
    ├── phase-4/  P3 Timeline
    ├── phase-5/  P2 Voz
    ├── phase-6/  P3 Focalización
    └── phase-7/  P0-P1 Motor + CLI
```

---

## Prioridades (Orden de Implementación)

### P0 - OBLIGATORIO
```
0.1 → 0.2 → 0.3 → 1.1 → 1.2 → 1.3 → 1.4 → 2.1 → 2.2 → 2.3 → 2.4 → 7.1
```

### P1 - ALTO VALOR
```
3.1, 7.3, 7.4 (pueden hacerse en paralelo tras P0)
```

### P2+ - POST-VALIDACIÓN
```
Evaluar tras feedback de usuarios reales
```

---

## Archivos Grandes (>400 líneas) - Evitar cargar completos

| Archivo | Líneas | Qué contiene |
|---------|--------|--------------|
| position-synchronization.md | 647 | Sistema de anclas - cargar solo si hay problemas de sincronización |
| history-system.md | 609 | Estados de alertas - cargar solo para STEP 7.1 |
| step-7.1-alert-engine.md | 557 | Motor de alertas |
| step-7.3-style-guide.md | 546 | Hoja de estilo |
| step-7.4-cli.md | 545 | CLI |

---

## Consejos para Claude Code

1. **Un STEP a la vez**: No cargues múltiples STEPs simultáneamente
2. **Schema parcial**: El schema tiene secciones separadas - lee solo las tablas relevantes
3. **Heurísticas bajo demanda**: Solo lee H1-H6 cuando implementes detección específica
4. **Usa grep**: Busca términos específicos antes de cargar archivos completos
5. **enums-reference.md**: Es compacto (~250 líneas) y tiene todos los valores válidos

---

## Enlaces Directos a STEPs P0

- [STEP 0.1: Entorno](./steps/phase-0/step-0.1-environment.md)
- [STEP 0.2: Estructura](./steps/phase-0/step-0.2-project-structure.md)
- [STEP 0.3: Schema BD](./steps/phase-0/step-0.3-database-schema.md)
- [STEP 1.1: Parser DOCX](./steps/phase-1/step-1.1-docx-parser.md)
- [STEP 1.2: Detector Estructura](./steps/phase-1/step-1.2-structure-detector.md)
- [STEP 1.3: Pipeline NER](./steps/phase-1/step-1.3-ner-pipeline.md)
- [STEP 1.4: Detector Diálogos](./steps/phase-1/step-1.4-dialogue-detector.md)
- [STEP 2.1: Correferencia](./steps/phase-2/step-2.1-coreference.md)
- [STEP 2.2: Fusión Entidades](./steps/phase-2/step-2.2-entity-fusion.md)
- [STEP 2.3: Extracción Atributos](./steps/phase-2/step-2.3-attribute-extraction.md)
- [STEP 2.4: Consistencia Atributos](./steps/phase-2/step-2.4-attribute-consistency.md)
- [STEP 7.1: Motor Alertas](./steps/phase-7/step-7.1-alert-engine.md)
