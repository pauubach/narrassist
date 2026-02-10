# Sistema de Licencias - Narrative Assistant

> **Última actualización**: 2026-02-09
> **Estado**: Especificación aprobada, implementación en progreso

---

## Resumen Ejecutivo

Sistema de licencias basado en suscripción con tres tiers (Corrector, Profesional, Editorial). Todas las funciones incluidas según tier, sin módulos separados. Medición de cuota en páginas (250 palabras = 1 página). Verificación online con 14 días de gracia offline. Protección media con hardware fingerprint. Aplicación 100% local — los manuscritos nunca salen de la máquina del usuario.

---

## Modelo de Negocio

### Principios

- **No es SaaS**: La app corre en local. No hay coste de servidor por análisis.
- **Suscripción por mejoras**: El usuario paga por actualizaciones continuas (nuevos modelos, patrones, features), no por acceso a servidores.
- **Sin módulos**: Todo incluido en cada tier. La diferencia es capacidades + volumen.
- **Medición justa**: Se mide en páginas, no en proyectos. Un cuento de 20 páginas no es lo mismo que una novela de 500.
- **Al cancelar**: Los datos siguen accesibles. Solo se desactiva el motor de análisis.

### Tiers

| | Corrector | Profesional | Editorial |
|---|:---:|:---:|:---:|
| **Target** | Corrector freelance | Corrector profesional | Agencia / editorial |
| **Dispositivos** | 1 | 2 | 10 |
| **Páginas/mes** | 1.500 | 3.000 | Ilimitado |
| **Rollover** | 1 mes | 1 mes | — |
| **Cambio dispositivo** | Cooldown 48h | Cooldown 48h | Cooldown 48h |

### Capacidades por Tier

| Capacidad | Corrector | Profesional | Editorial |
|---|:---:|:---:|:---:|
| Consistencia de atributos | Sí | Sí | Sí |
| Gramática y ortografía | Sí | Sí | Sí |
| NER + correferencias | Sí | Sí | Sí |
| Detección de variantes de nombre | Sí | Sí | Sí |
| Character profiling | — | Sí | Sí |
| Análisis de red de personajes | — | Sí | Sí |
| Detección de anacronismos | — | Sí | Sí |
| Detección out-of-character | — | Sí | Sí |
| Español clásico (Siglo de Oro) | — | Sí | Sí |
| Análisis multi-modelo | — | Sí | Sí |
| Informes completos | — | Sí | Sí |

**Hardware**: El análisis se adapta al equipo del usuario (graceful degradation). Si la máquina no soporta multi-modelo, se usa un solo modelo con mejor prompt. No se bloquea ninguna feature por hardware.

---

## Precios

| | Corrector | Profesional | Editorial |
|---|:---:|:---:|:---:|
| **Mensual** | **24€/mes** | **49€/mes** | **299€/mes** |
| **Anual** (paga 10, usa 12) | **240€/año** | **490€/año** | **2.990€/año** |
| **Precio de lanzamiento** (paga 9, usa 12) | **215€/año** | **440€/año** | **2.690€/año** |

> *Anual: paga 10 meses, disfruta 12.*
> *Precio de lanzamiento (tiempo limitado): paga 9 meses, disfruta 12.*
> *Más de 10 dispositivos: contáctanos.*

### Condiciones generales

- **Prueba gratuita**: 14 días con todas las funciones de Profesional, sin tarjeta.
- **Re-análisis**: Analizar el mismo manuscrito no consume cuota (mismo fingerprint de documento).
- **Al cancelar**: Tus datos siguen accesibles. Solo se desactiva el motor de análisis.
- **Rollover**: Las páginas no usadas del mes anterior se suman al mes actual. No se acumulan más allá de un mes.

### Medición de cuota

- **1 página = 250 palabras** (estándar editorial)
- Se contabilizan las palabras del manuscrito en el primer análisis
- Re-analizar el mismo documento (mismo fingerprint SHA-256 + Jaccard) es gratuito
- El rollover arrastra solo las páginas no usadas del mes inmediatamente anterior

---

## Arquitectura Técnica

### Backend de Licencias

```
src/narrative_assistant/licensing/
├── __init__.py          # Exports públicos
├── models.py            # Dataclasses: License, Device, Subscription, UsageRecord
├── verification.py      # LicenseVerifier: verificación online/offline
└── fingerprint.py       # Hardware fingerprinting (CPU, RAM, disco, MAC)
```

### Flujo de Verificación

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO DE LICENCIAS                        │
├─────────────────────────────────────────────────────────────┤
│  1. PRIMER INICIO                                            │
│     App Init → Check License → License Dialog → Activar      │
│                                                              │
│  2. USO NORMAL (OFFLINE)                                     │
│     App Init → Check Local Cache → Validate                  │
│     Si cache < 14 días → OK                                  │
│     Si cache >= 14 días → Requiere verificación online       │
│                                                              │
│  3. REVALIDACIÓN PERIÓDICA                                   │
│     Online Check cada 24h si hay conexión                    │
│     Actualiza cache local con nueva fecha                    │
│                                                              │
│  4. CANCELACIÓN                                              │
│     Verificación online detecta cancelación →                │
│     14 días de gracia → Motor de análisis desactivado        │
│     Datos accesibles en modo lectura                         │
└─────────────────────────────────────────────────────────────┘
```

### Control de Dispositivos

```
┌─────────────────────────────────────────────────────────────┐
│                    DEVICE SLOTS                              │
├─────────────────────────────────────────────────────────────┤
│  Corrector: 1     Profesional: 2     Editorial: 10          │
│                                                              │
│  Al activar en nueva máquina:                                │
│  1. Calcular fingerprint del hardware                        │
│  2. Verificar si fingerprint ya registrado → OK              │
│  3. Si nuevo y hay slot libre → registrar                    │
│  4. Si nuevo y NO hay slot → error DeviceLimitError          │
│                                                              │
│  Al desactivar dispositivo:                                  │
│  1. Marcar como INACTIVE                                     │
│  2. Aplicar cooldown de 48 horas                             │
│  3. Durante cooldown no puede usarse en otro dispositivo     │
│                                                              │
│  Más de 10 dispositivos: contacto directo                    │
└─────────────────────────────────────────────────────────────┘
```

### Control de Cuota (Páginas)

```
┌─────────────────────────────────────────────────────────────┐
│                    CUOTA MENSUAL (PÁGINAS)                   │
├─────────────────────────────────────────────────────────────┤
│  Al analizar un manuscrito:                                  │
│  1. Contar palabras del documento                            │
│  2. Convertir a páginas (÷ 250, redondeo arriba)             │
│  3. Calcular fingerprint del documento (SHA-256 + Jaccard)   │
│  4. Buscar en usage_records del periodo actual               │
│  5. Si ya analizado antes → NO cuenta contra cuota           │
│  6. Si nuevo:                                                │
│     - Verificar cuota disponible (incluyendo rollover)       │
│     - Si hay cuota → registrar uso → OK                      │
│     - Si no hay cuota → QuotaExceededError                   │
│                                                              │
│  Rollover:                                                   │
│  - Las páginas no usadas del mes anterior se suman           │
│  - Solo se arrastra 1 mes (no acumulación infinita)          │
│                                                              │
│  Editorial: Sin límite (pages_per_month = -1)                │
└─────────────────────────────────────────────────────────────┘
```

### Hardware Fingerprint

Componentes utilizados para el fingerprint:

| Componente | Datos extraídos | Privacidad |
|------------|-----------------|------------|
| CPU | Modelo, núcleos, threads | Completo |
| RAM | Total memoria | Completo |
| Disco | Serial (últimos 8 chars) | Parcial |
| Red | MAC (últimos 6 chars) | Parcial |
| Sistema | Hostname, OS, arch | Parcial |
| Machine ID | ID único del SO | Parcial |

El fingerprint final es un hash SHA-256 de todos los componentes concatenados. No se puede revertir a los datos originales.

---

## Integración con Pagos

### Opción recomendada: LemonSqueezy

Para el lanzamiento se recomienda usar **LemonSqueezy** como plataforma de pagos y gestión de licencias:

- Genera license keys automáticamente al comprar
- API REST para `/activate` y `/verify`
- Gestiona suscripciones, renovaciones y cancelaciones
- Maneja IVA de la UE automáticamente
- Portal de cliente incluido
- Coste: 5% por transacción

### Endpoints del servidor de licencias

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/activate` | POST | Activar licencia con key + fingerprint |
| `/verify/{key}` | POST | Verificar estado (fingerprint + versión app) |

### Webhooks necesarios

| Evento | Acción |
|--------|--------|
| Suscripción creada | Crear/activar licencia |
| Suscripción actualizada | Actualizar tier |
| Suscripción cancelada | Marcar licencia como cancelada |
| Pago recibido | Renovar período de facturación |
| Pago fallido | Marcar en grace period |

### Metadata de licencia

```json
{
  "tier": "CORRECTOR|PROFESIONAL|EDITORIAL",
  "max_devices": 1,
  "pages_per_month": 1500,
  "billing_period": "monthly|annual"
}
```

---

## Seguridad

### Protección Media (Hardware Binding)

- Fingerprint de máquina vinculado a licencia
- Verificación online cada 24 horas (si hay conexión)
- Grace period de 14 días sin conexión
- Cooldown de 48h al cambiar de dispositivo

### Manuscritos — Aislamiento total

- Los manuscritos NUNCA salen de la máquina del usuario
- Sin telemetría ni analytics de contenido
- La verificación de licencia solo envía: fingerprint de hardware, versión de la app
- Ningún dato del manuscrito se transmite al servidor de licencias

### No implementado (deliberadamente)

- Ofuscación de código (complejidad alta, mantenimiento difícil)
- Verificación en cada operación (impacto en rendimiento)
- DRM agresivo (mala UX para usuarios legítimos)

---

## Errores de Licencia

| Error | Código | Mensaje usuario |
|-------|--------|-----------------|
| `LicenseNotFoundError` | NO_LICENSE | "No se encontró una licencia válida" |
| `LicenseExpiredError` | EXPIRED | "Tu licencia ha expirado" |
| `LicenseOfflineError` | OFFLINE_EXPIRED | "Necesitas conexión para verificar tu licencia" |
| `DeviceLimitError` | DEVICE_LIMIT | "Has alcanzado el límite de dispositivos" |
| `DeviceCooldownError` | DEVICE_COOLDOWN | "Debes esperar 48h antes de usar otro dispositivo" |
| `QuotaExceededError` | QUOTA_EXCEEDED | "Has alcanzado el límite de páginas este mes" |
| `TierFeatureError` | TIER_FEATURE | "Esta funcionalidad requiere el plan Profesional" |

---

## Trial

- 14 días con todas las funciones de Profesional
- Sin tarjeta de crédito
- 1 dispositivo
- Cuota de páginas: 3.000 (igual que Profesional)
- Al terminar: datos accesibles, motor de análisis desactivado
- Puede activar suscripción en cualquier momento

---

## Archivos Relacionados

- `src/narrative_assistant/licensing/` — Implementación backend
- `api-server/routers/license.py` — Endpoints REST de licencias
- `frontend/src/components/LicenseDialog.vue` — UI de licencias
- `frontend/src/stores/license.ts` — Store Pinia de licencias
