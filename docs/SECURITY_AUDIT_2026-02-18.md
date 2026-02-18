# Security Audit — 18 Feb 2026

## npm audit (Frontend)

**Resultado**: 11 moderate severity vulnerabilities

Todas en **dev dependencies** (eslint, @typescript-eslint/*):
- No afectan producción
- No afectan runtime del build
- Cadena de dependencias: eslint → @typescript-eslint/* → vue-eslint-parser

**Fix disponible**: `npm audit fix --force` (breaking changes en typescript-eslint v8.14.0)

**Recomendación**:
- Monitorear pero **NO urgente** (solo dev)
- Considerar upgrade cuando se haga refactor de linting config
- Build y runtime no afectados

---

## pip audit (Backend)

**Resultado**: 83 known vulnerabilities in 31 packages

**Limitación técnica**: pip-audit crash con UnicodeEncodeError al generar reporte completo.

**Contexto**:
- Entorno Anaconda con ~400 paquetes
- Muchas son transitive dependencies
- Algunas pueden ser false positives (versiones específicas de Anaconda)

**Próximos pasos**:
1. Generar reporte con `pip-audit --format json` (requiere fix encoding)
2. Filtrar solo **direct dependencies** de pyproject.toml
3. Priorizar vulnerabilidades CRITICAL y HIGH
4. Verificar si Anaconda ya patcheó en su distribución

**Acción inmediata**:
- Agregar `pip-audit` al CI/CD para tracking continuo
- Revisar manualmente paquetes críticos: fastapi, pydantic, sqlalchemy, spacy

---

## Notas

- **Frontend build**: Limpio, 0 errores
- **Backend**: Anaconda + requirements.txt — considerar migración a poetry/pipenv para mejor dependency resolution
- **Ollama**: Separado del audit (binario externo)

---

## Estado

- ✅ npm audit: Documentado, no urgente
- ⚠️ pip audit: Requiere investigación adicional (83 vulns)
- 📋 Siguiente: C-3 (dead code scan)
