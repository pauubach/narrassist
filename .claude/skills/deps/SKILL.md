---
name: deps
description: "Auditoría de dependencias desactualizadas y vulnerabilidades de seguridad en ambos stacks (Python + Node/npm). Invocar cuando el usuario diga 'revisa las dependencias', 'hay deps desactualizadas', 'vulnerabilidades en paquetes', 'pip audit', 'npm audit'."
---

# /deps — Auditoría de dependencias (Python + Node)

## Cuándo usar

- Mensualmente como mantenimiento preventivo.
- Antes de una release para detectar CVEs conocidos.
- Tras un aviso de seguridad en algún paquete del stack.
- Cuando el usuario quiere actualizar dependencias de forma controlada.

## Argumentos

- (sin args) — auditoría completa de ambos stacks
- `--python` — solo backend Python
- `--node` — solo frontend Node/npm
- `--security-only` — ignorar updates menores/patch, mostrar solo CVEs

## Flujo

### Paso 1 — Python: desactualizadas

```bash
cd /Users/PABLO/repos/narrassist && .venv/bin/pip list --outdated --format=columns 2>&1
```

### Paso 2 — Python: vulnerabilidades (pip-audit)

```bash
cd /Users/PABLO/repos/narrassist && .venv/bin/pip-audit --format=json 2>&1
```

Si `pip-audit` no está disponible:
```bash
cd /Users/PABLO/repos/narrassist && .venv/bin/pip install pip-audit --quiet && .venv/bin/pip-audit --format=json 2>&1
```

### Paso 3 — Node: desactualizadas

```bash
cd /Users/PABLO/repos/narrassist/frontend && npm outdated 2>&1
```

### Paso 4 — Node: vulnerabilidades

```bash
cd /Users/PABLO/repos/narrassist/frontend && npm audit --json 2>&1
```

### Paso 5 — Clasificar y priorizar

Para cada paquete, clasificar:

| Prioridad | Criterio |
|-----------|----------|
| 🔴 URGENTE | CVE conocido con CVSS ≥ 7.0 / severidad alta o crítica |
| 🟡 ATENCIÓN | CVE CVSS < 7.0 / versión mayor disponible con breaking changes |
| 🟢 OPCIONAL | Solo versión minor/patch, sin CVE |

### Paso 6 — Output

```
## Auditoría de dependencias — <fecha>

### 🐍 Python

#### Vulnerabilidades
| Paquete | Versión actual | CVE | Severidad | Fix disponible |
|---------|---------------|-----|-----------|----------------|
| requests | 2.28.1 | CVE-2023-XXXX | 🔴 HIGH | 2.31.0 |

#### Desactualizadas (sin CVE)
| Paquete | Actual | Última | Tipo |
|---------|--------|--------|------|
| spacy | 3.7.2 | 3.8.1 | 🟡 minor |

### 📦 Node/npm

#### Vulnerabilidades
| Paquete | Severidad | Path | Fix |
|---------|-----------|------|-----|

#### Desactualizadas (sin CVE)
| Paquete | Actual | Quería | Tipo |

### Acciones recomendadas

1. 🔴 Actualizar `requests` → 2.31.0: `pip install requests==2.31.0` (no breaking)
2. 🟡 Evaluar `spacy` 3.8.1: revisar CHANGELOG antes (puede requerir re-descarga de modelo)
...

⚠️ No actualizar automáticamente. Mostrar comandos exactos para que el usuario decida.
```

**No ejecutar `pip install` ni `npm install` sin OK explícito del usuario.**
Proporcionar los comandos exactos para que el usuario los ejecute cuando quiera.
