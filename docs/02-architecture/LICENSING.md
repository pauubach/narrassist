# Sistema de Licencias - Narrative Assistant

> **Última actualización**: 2026-01-15
> **Estado**: Especificación aprobada, implementación en progreso

---

## Resumen Ejecutivo

Sistema de licencias basado en suscripción con tres tiers (Freelance, Agencia, Editorial) y módulos adicionales. Verificación online con 14 días de gracia offline. Protección media con hardware fingerprint.

---

## Modelo de Negocio

### Tiers de Usuario

| Tier | Target | Manuscritos/mes | Dispositivos | Cambio máquina |
|------|--------|-----------------|--------------|----------------|
| **Freelance** | Corrector autónomo | 5 | 1 | cooldown 48h |
| **Agencia** | Agencia literaria (2-5 personas) | 15 | 2 | cooldown 48h |
| **Editorial** | Grupo editorial | Ilimitado | 5+ | cooldown 48h |

### Módulos Funcionales

| Módulo | Descripción | Dependencias |
|--------|-------------|--------------|
| **CORE** | Ortografía, gramática, repeticiones, NER, capítulos | Base obligatoria |
| **NARRATIVA** | Consistencia atributos, timeline, fichas personajes | Requiere CORE |
| **VOZ_ESTILO** | Perfiles voz, desviaciones, LLM local, Style Guide | Requiere CORE |
| **AVANZADO** | Coherencia emocional, grafo relaciones, API REST | Requiere CORE |

### Bundles

| Bundle | Módulos incluidos | Ahorro vs individual |
|--------|-------------------|----------------------|
| **SOLO_CORE** | Core | - |
| **PROFESIONAL** | Core + Narrativa + Voz/Estilo | ~15% |
| **COMPLETO** | Todos | ~20% |

---

## Precios

### Módulos Individuales (Mensual)

| Módulo | Freelance | Agencia | Editorial |
|--------|-----------|---------|-----------|
| **CORE** | 19€ | 49€ | 149€ |
| **NARRATIVA** | +19€ | +45€ | +129€ |
| **VOZ & ESTILO** | +25€ | +59€ | +169€ |
| **AVANZADO** | +15€ | +39€ | +119€ |

### Bundles Mensuales

| Bundle | Freelance | Agencia | Editorial |
|--------|-----------|---------|-----------|
| **Solo Core** | 19€ | 49€ | 149€ |
| **Profesional** | 55€ | 129€ | 399€ |
| **Completo** | 65€ | 159€ | 499€ |

### Bundles Anuales (×10 meses = 17% descuento)

| Bundle | Freelance | Agencia | Editorial |
|--------|-----------|---------|-----------|
| Solo Core | 190€/año | 490€/año | 1.490€/año |
| Profesional | 550€/año | 1.290€/año | 3.990€/año |
| Completo | 650€/año | 1.590€/año | 4.990€/año |

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
│     App Init → Check License → License Dialog → Stripe       │
│                                                              │
│  2. USO NORMAL (OFFLINE)                                     │
│     App Init → Check Local Cache → Validate Signature        │
│     Si cache < 14 días → OK                                  │
│     Si cache >= 14 días → Requiere verificación online       │
│                                                              │
│  3. REVALIDACIÓN PERIÓDICA                                   │
│     Online Check cada inicio si hay conexión                 │
│     Actualiza cache local con nueva fecha                    │
└─────────────────────────────────────────────────────────────┘
```

### Control de Dispositivos

```
┌─────────────────────────────────────────────────────────────┐
│                    DEVICE SLOTS                              │
├─────────────────────────────────────────────────────────────┤
│  Freelance: 1 slot    Agencia: 2 slots    Editorial: 5+     │
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
└─────────────────────────────────────────────────────────────┘
```

### Control de Manuscritos

```
┌─────────────────────────────────────────────────────────────┐
│                    CUOTA MENSUAL                             │
├─────────────────────────────────────────────────────────────┤
│  Al abrir manuscrito:                                        │
│  1. Calcular fingerprint del documento (SHA-256 + Jaccard)   │
│  2. Buscar en usage_records del periodo actual               │
│  3. Si ya analizado antes → NO cuenta contra cuota           │
│  4. Si nuevo:                                                │
│     - Verificar cuota disponible                             │
│     - Si hay cuota → registrar uso → OK                      │
│     - Si no hay cuota → QuotaExceededError                   │
│                                                              │
│  Editorial: Sin límite (manuscripts_per_month = -1)          │
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
| Sistema | Hostname, OS, arch | Completo |
| Machine ID | ID único del SO | Parcial |

El fingerprint final es un hash SHA-256 de todos los componentes concatenados. No se puede revertir a los datos originales.

---

## Integración con Stripe

### Webhooks necesarios

| Evento | Acción |
|--------|--------|
| `customer.subscription.created` | Crear/activar licencia |
| `customer.subscription.updated` | Actualizar tier/módulos |
| `customer.subscription.deleted` | Cancelar licencia |
| `invoice.paid` | Renovar período de facturación |
| `invoice.payment_failed` | Marcar en grace period |

### Metadata de Stripe

```json
{
  "tier": "FREELANCE|AGENCIA|EDITORIAL",
  "bundle": "SOLO_CORE|PROFESIONAL|COMPLETO",
  "modules": ["CORE", "NARRATIVA"],
  "max_devices": 1,
  "manuscripts_per_month": 5
}
```

---

## Seguridad

### Protección Media (Hardware Binding)

- Fingerprint de máquina vinculado a licencia
- Verificación periódica online (mínimo cada 14 días)
- Cooldown de 48h al cambiar de dispositivo
- Firma digital del token de licencia

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
| `QuotaExceededError` | QUOTA_EXCEEDED | "Has alcanzado el límite de manuscritos este mes" |
| `ModuleNotLicensedError` | MODULE_NOT_LICENSED | "Esta funcionalidad requiere el módulo X" |

---

## Trial y Conversión

### Trial de 14 días

- Acceso a Bundle PROFESIONAL completo
- Sin límite de manuscritos
- 1 dispositivo
- Watermark en exportaciones: "Generado con Narrative Assistant - Trial"

### Conversión

- Al terminar trial: proyectos quedan en modo lectura
- Puede reactivar en cualquier momento
- Descuento 10% si convierte antes de terminar trial

---

## Archivos Relacionados

- `src/narrative_assistant/licensing/` - Implementación backend
- `api-server/main.py` - Endpoints de licencias (pendiente)
- `frontend/src/components/LicenseDialog.vue` - UI de licencias (pendiente)
- `frontend/src/stores/license.ts` - Store de licencias (pendiente)
