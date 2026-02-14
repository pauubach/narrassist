# Plan de Produccion: Sistema de Licencias

> Documento generado por analisis experto (panel de 4 expertos en seguridad + 1 arquitecto senior).
> Fecha: 2026-02-10 | Version: 1.0

---

## Estado Actual

### Lo que existe (cliente - COMPLETO)

| Archivo | Contenido |
|---------|-----------|
| `licensing/models.py` | Enums (LicenseTier, LicenseFeature), dataclasses, SQL schema (5 tablas) |
| `licensing/verification.py` | LicenseVerifier: verify, quota con rollover, feature gating, 7 clases de error |
| `licensing/fingerprint.py` | HardwareDetector + FingerprintGenerator: SHA-256 cross-platform |
| `api-server/routers/license.py` | 7 endpoints FastAPI: status, activate, verify, devices, usage, check-feature |
| `frontend/src/stores/license.ts` | Pinia store con tipos, computed, acciones API |
| `tests/unit/test_licensing_*.py` | 147 tests (81 models + 66 verification) |

### Lo que NO existe

- **Servidor de licencias** (api.narrativeassistant.com no existe)
- **Enforcement en el pipeline** (analysis.py no llama a verificacion)
- **Integracion Stripe** (webhooks, checkout, portal)
- **Sistema de promos/regalos** (sin codigos, sin admin panel)
- **Tracking de trials server-side** (reinstall = trial infinito)

---

## 1. Superficie de Ataque (10 vulnerabilidades identificadas)

| # | Vulnerabilidad | Dificultad | Impacto | Prioridad |
|---|---------------|-----------|---------|-----------|
| 1 | Sin enforcement en pipeline de analisis | Trivial | Bypass total | **P0** |
| 2 | Dev bypass `if not verifier: return True` | Trivial | Bypass total | **P0** |
| 3 | Frontend `catch → return true` en recordUsage | Trivial | Bypass cuota | **P0** |
| 4 | SQLite editable sin integridad (tier, status, quota) | Facil | Bypass total | **P1** |
| 5 | Manipulacion de reloj (grace period infinito) | Facil | Uso offline ilimitado | **P1** |
| 6 | Trial infinito via reinstall (borrar ~/.narrative_assistant/) | Trivial | Uso perpetuo gratis | **P1** |
| 7 | Fingerprint spoofeable (VMs, registros editables) | Moderado | Bypass dispositivos | **P2** |
| 8 | Python decompilable (toda la logica visible) | Facil | Exposicion de codigo | **P2** |
| 9 | API local sin autenticacion (curl directo) | Facil | Manipulacion API | **P2** |
| 10 | Sin validacion de formato de clave | Trivial | Info disclosure | **P3** |

---

## 2. Checklist de Produccion (priorizado)

### P0 - BLOQUEANTE (antes de cualquier usuario de pago)

| # | Tarea | Archivos | Esfuerzo | Descripcion |
|---|-------|----------|----------|-------------|
| 1 | Enforcement en pipeline | `analysis.py`, `unified_analysis.py` | 2-4h | `verify()` + `check_quota()` + `check_feature()` antes de cada analisis |
| 2 | Quitar bypass dev `allowed=True` | `license.py` (2 sitios) | 30min | Cambiar a `allowed=False, error="License unavailable"` (fail-closed) |
| 3 | Fix frontend catch | `license.ts` linea ~216 | 5min | `return true` → `return false` |
| 4 | Servidor de licencias | Nuevo servicio | 2-4 sem | Endpoints verify, activate, device management |
| 5 | Trial tracking server-side | Tabla + endpoint en servidor | 1 sem | Fingerprint en servidor para evitar reinstall abuse |

### P1 - ALTO (antes de lanzamiento publico)

| # | Tarea | Esfuerzo | Descripcion |
|---|-------|----------|-------------|
| 6 | Cache de verificacion firmado (JWT/HMAC) | 1-2 sem | Servidor firma estado; Rust verifica firma |
| 7 | Integridad SQLite (HMAC por fila) | 1 sem | Clave HMAC en Rust, detecta ediciones manuales |
| 8 | Anti-manipulacion de reloj | 2-3 dias | High-water mark monotonico + deteccion de regresion |
| 9 | Registro de dispositivos server-side | 1 sem | Servidor es fuente de verdad para lista de dispositivos |
| 10 | Aviso de privacidad (GDPR Art. 13-14) | 2-3 dias | Obligatorio antes de procesar datos de usuarios UE |
| 11 | Minimizacion de datos | 1h | Eliminar hostname, memory_total_gb, cpu_threads de fingerprint |
| 12 | Rate limiting en servidor | 2-3 dias | Max 3 activaciones/IP/30d, 5 intentos/IP/h |

### P2 - MEDIO (primeros 3 meses post-lanzamiento)

| # | Tarea | Esfuerzo |
|---|-------|----------|
| 13 | Validacion formato de clave (client + server) | 2h |
| 14 | Auth API local (token compartido Tauri↔Python) | 1-2 dias |
| 15 | Deteccion de VMs para trials | 2-3 dias |
| 16 | Sistema de heartbeat (cada 4h) | 1 sem |
| 17 | Ofuscacion modulo licensing (Cython/.pyd) | 1-2 sem |
| 18 | Sistema de codigos promo | 1-2 sem |
| 19 | Fuzzy fingerprint matching en servidor | 3-5 dias |
| 20 | Admin dashboard web (licencias, comp, stats) | 2-3 sem |
| 21 | Endpoints admin: gift, revoke, comp stats | 1 sem |

### P3 - BAJO (cuando haya recursos)

| # | Tarea | Esfuerzo |
|---|-------|----------|
| 22 | Derecho a eliminacion (GDPR Art. 17) | 2-3 dias |
| 23 | Deteccion de anomalias geograficas | 1 sem |
| 24 | Analytics agregados de uso | 1 sem |
| 25 | Stripe webhooks en tiempo real | 2-3 dias |
| 26 | Push notification de revocacion | 3-5 dias |
| 27 | Limpieza automatica de datos expirados | 2-3 dias |

---

## 3. Licencias Regaladas / Promocionales

### 3.1 Categorias de licencias comp/regalo

| Tipo | Duracion | Descuento | Limite | Caso de uso |
|------|----------|-----------|--------|-------------|
| `beta` | 6-12 meses | 100% | 50 | Beta testers. Conversion: 50% off si adoptan |
| `press` | 12 meses | 100% | 30 | Prensa/influencers. 30% off si acuerdo continuo |
| `friend` | Indefinido | 50-100% | 10 | Friends & family. No transferible |
| `contest` | 6-12 meses | 100% | Ilimitado | Ganadores de concursos |
| `partner` | Negociado | 30-50% | Ilimitado | Editoriales, universidades (convenio) |
| `goodwill` | 1-6 meses | 100% | Ilimitado | Compensacion por bugs criticos, caidas |

**Reglas generales:**
- Todas las comp licenses tienen `is_comp=true` y `comp_type` en la BD
- Las comp NO son transferibles (vinculadas al email)
- Expiración automática + email 30 días antes del vencimiento
- Revocables desde admin dashboard
- Al expirar: "Tu acceso ha finalizado. Aquí tienes 30% off para continuar"

### 3.2 Tipos de codigo promo

| Tipo | Comportamiento | Caso de uso |
|------|---------------|-------------|
| `trial_extension` | Extiende acceso N dias al tier actual | Beta testers (30d), extender trial |
| `tier_upgrade` | Override temporal de tier (ej: corrector→pro) | Previews de features, eventos |
| `full_gift` | Licencia completa de cualquier tier y duracion | Empleados, socios, concursos |

### 3.3 Flujo de licencias regalo

```
1. Admin dashboard → "Crear licencia regalo"
   - Formulario: email, tier, comp_type, duracion, descuento %, notas internas
   - Sistema genera license key + envia email de bienvenida
   - License queda marcada: is_comp=true, comp_type, comp_expires_at

2. Usuario recibe email → activa con su clave
   - Sin Stripe (100% gratis) o con Stripe coupon (descuento parcial)

3. Comp expira → siguiente verificacion 24h
   - Servidor retorna valid=false, reason="comp_expired"
   - App muestra: "Tu periodo de acceso ha finalizado. Suscribete..."
   - Email automatico 30d antes con oferta de conversion

4. Admin dashboard → revocar si es necesario
   - POST /admin/licenses/{id}/revoke
   - Siguiente verificacion invalida la licencia
```

### 3.4 Codigos promo para eventos

| Tipo | Implementacion |
|------|---------------|
| **Beta tester** | `comp_type='beta'`, tier profesional/editorial, sin expiracion |
| **Conferencia** | Promo multi-uso (`max_redemptions=200`), 24h/48h/7d, codigo tipo "BOOKFAIR2026" |
| **Prensa/reviewer** | `comp_type='press'`, editorial 90d, metadata con nombre y publicacion |

### 3.5 Formato de clave de licencia

```
NA-TTCC-DDDD-RRRR-RRKK

T (2 chars) = Tipo + Tier (paid/trial/promo/gift + corrector/pro/editorial)
C (2 chars) = Fecha creacion (dias desde 2025-01-01, Base32)
D (4 chars) = Identificador deterministico (HMAC de email+tier+fecha)
R (6 chars) = Entropia aleatoria (30 bits, no adivinable)
K (2 chars) = Checksum CRC-10 (validable offline sin servidor)

Charset: Crockford Base32 (sin 0/1/I/O para evitar confusion)
Ejemplo: NA-3P4K-HMJN-XVBR-2QAW
```

---

## 4. Prevencion de Abuso de Trial

### Tracking server-side

```sql
trial_records (en servidor PostgreSQL)
--------------------------------------
hardware_fingerprint    TEXT UNIQUE     -- hash SHA-256
fingerprint_components  JSONB           -- componentes individuales para fuzzy match
email                   TEXT
trial_started_at        TIMESTAMPTZ
trial_expires_at        TIMESTAMPTZ
ip_address              INET
is_vm                   BOOLEAN
```

### Flujo

1. Primera ejecucion → envia fingerprint + componentes al servidor
2. **Sin match**: crea trial 14 dias, retorna licencia temporal
3. **Match exacto, trial activo**: retorna trial existente (reinstall durante trial = OK)
4. **Match exacto, trial expirado**: error "Ya has usado tu periodo de prueba"
5. **Match fuzzy (3+ de 5 componentes iguales)**: mismo que match exacto (cubre cambios de hardware)

### Deteccion de VMs

Best-effort, no bloqueo duro:
- CPU string con "Virtual"/"QEMU"/"VMware"/"KVM"
- MAC en rangos conocidos (00:0C:29 VMware, 08:00:27 VirtualBox, etc.)
- Si misma IP genera 3+ fingerprints de VM → bloquear IP 90 dias
- Trials en VM: 7 dias en vez de 14

---

## 5. Anti-Tamper

### Proteccion de integridad SQLite

**Recomendado: HMAC por fila con clave en Rust**

```
Para cada fila critica (licenses, devices, usage_records):
  hmac_value = HMAC-SHA256(rust_key, f"{license_key}|{tier}|{status}|{last_verified_at}")

Al leer, recomputar HMAC. Si no coincide → fila manipulada → invalida.
La clave HMAC vive en el binario Rust (Tauri), NO en Python.
```

### Anti-manipulacion de reloj

```
Tabla time_tracking:
  last_known_utc          TEXT    -- timestamp mas alto jamas observado
  clock_regression_count  INT     -- contador de regresiones

En cada inicio:
  if datetime.utcnow() < last_known_utc - 1h:
    regression_count += 1
    if regression_count >= 3:
      → Forzar verificacion online
  else:
    actualizar last_known_utc

Complemento: timestamp firmado del servidor como high-water mark.
```

### Auth API local

```
1. Tauri genera token aleatorio 256-bit al iniciar
2. Token → Python backend via env var
3. Token → Vue frontend via Tauri IPC
4. Todas las llamadas API requieren Authorization: Bearer <token>
5. Python rechaza requests sin token valido
```

---

## 6. GDPR / Privacidad

### Base legal para fingerprinting

- **Articulo 6(1)(b)**: Ejecucion de contrato (EULA requiere vinculacion de dispositivo)
- **Articulo 6(1)(f)**: Interes legitimo (prevencion de fraude)
- Fingerprint = dato pseudonimizado (Art. 4(5)), NO anonimo

### Requisitos obligatorios

| Requisito | Estado | Prioridad |
|-----------|--------|-----------|
| Aviso de privacidad en primer inicio | No existe | P1 |
| Minimizacion de datos (eliminar hostname, memory, cpu_threads) | No hecho | P1 |
| Derecho a eliminacion completa | No implementado | P3 |
| Politica de retencion de datos | No definida | P1 |
| DPA con proveedor de hosting | No firmado | P1 |

### Minimizacion de datos en fingerprint.py

| Campo | Usado en hash | Usado en display | Accion |
|-------|:---:|:---:|--------|
| cpu_model | Si | No | Mantener |
| cpu_cores | Si | No | Mantener |
| cpu_threads | No | No | **ELIMINAR** |
| memory_total_gb | No | No | **ELIMINAR** |
| disk_serial | Si | No | Mantener |
| mac_address | Si | No | Mantener |
| hostname | No | Si (device_name) | **Reemplazar por generico** |
| machine_id | Si | No | Mantener |
| os_name | Si | Si | Mantener |
| architecture | Si | No | Mantener |

### Retencion de datos

| Datos | Retencion | Justificacion |
|-------|-----------|---------------|
| Licencia activa | Duracion suscripcion + 30d | Ejecucion contrato |
| Fingerprints activos | Duracion suscripcion + 30d | Enforcement |
| Fingerprints desactivados | 48h cooldown + 30d | Prevenir device swapping |
| Usage records | 6 meses post billing period | Disputas de facturacion |
| Trial records | 2 anos | Prevenir re-abuso |
| Datos cuenta cancelada | 30d post solicitud | Tiempo de procesamiento |

---

## 7. Arquitectura del Servidor

### Stack recomendado

| Componente | Recomendacion | Razon |
|------------|--------------|-------|
| Lenguaje | Python 3.12 | Mismo que la app, modelos compartidos |
| Framework | FastAPI | Ya usado, async, auto-docs |
| Base de datos | PostgreSQL 16 | JSONB, TIMESTAMPTZ, constraints robustos |
| ORM | SQLAlchemy 2.0 + Alembic | Migraciones, type-safe |
| Pagos | Stripe SDK | Oficial, webhook signature verification |
| Hosting | Railway (~15 EUR/mes) | Auto-deploy desde GitHub, PostgreSQL incluido |

### Endpoints del servidor

**Publicos (llamados por la app):**

| Metodo | Endpoint | Funcion |
|--------|----------|---------|
| POST | /v1/licenses/activate | Activar clave en nuevo dispositivo |
| POST | /v1/licenses/verify/{key} | Verificacion periodica (24h) |
| POST | /v1/licenses/deactivate-device | Desactivar dispositivo (48h cooldown) |
| POST | /v1/licenses/redeem-promo | Canjear codigo promo |
| POST | /v1/stripe/webhook | Receptor Stripe webhooks |

**Admin (protegidos, requieren auth):**

| Metodo | Endpoint | Funcion |
|--------|----------|---------|
| GET | /admin/dashboard | Stats agregados (MRR, churn, uso, comp stats) |
| GET | /admin/licenses | Listar licencias (filtro por tier, status, comp_type) |
| POST | /admin/licenses/gift | Crear licencia regalo/comp |
| PATCH | /admin/licenses/{id} | Modificar tier/status/discount/expiry |
| POST | /admin/licenses/{id}/revoke | Revocar licencia comp |
| POST | /admin/promos/create | Generar codigos promo multi-uso |
| GET | /admin/promos | Listar promos con stats de redencion |
| GET | /admin/comp/stats | Estadisticas de licencias comp por tipo |
| GET | /admin/founding/stats | Estadisticas de founding members (discount amounts, upgrades) |

**Admin dashboard** (pendiente de implementar):
- Panel web protegido con autenticacion (JWT o API key)
- Vista de licencias con filtros (tier, status, founding, comp)
- Creacion de licencias regalo con formulario
- Estadisticas: MRR, churn rate, comp licenses activas, founding members
- Gestion de codigos promo (crear, revocar, ver estadisticas)
- NO es parte de la app Tauri — es un servicio web separado

### Estructura de precios (revisada 12-Feb-2026)

> Panel de pricing, sales y marketing. 3 tiers, sin tier adicional.

| | Corrector | Profesional | Editorial |
|---|-----------|-------------|-----------|
| **Precio standard** | €24/mo | €49/mo | €159/mo (3 puestos base) |
| **Precio anual** | €216/año (25% off) | €441/año (25% off) | €1,521/año (25% off) |
| **Puesto extra** | — | — | +€49/puesto/mo |
| **Páginas/mo** | 1,500 | 3,000 | Ilimitado |
| **Manuscrito max** | 60k palabras | Ilimitado | Ilimitado |
| **Dispositivos** | 1 | 1 | 3 base (+extras) |
| **Device swaps** | 2/mes + 7d cooldown | 2/mes + 7d cooldown | 2/mes + 7d cooldown |
| **Features** | 4 básicas | 11 (todas excepto export/import) | 12 (todas + export/import/merge) |

**Founding member program** (30 plazas totales):

| Tier original | Plazas | Precio inicial | Descuento fijo |
|---------------|:------:|:--------------:|:--------------:|
| Corrector | 10 | €19/mo (€24 - €5) | **€5/mes para siempre** |
| Profesional | 15 | €34/mo (€49 - €15) | **€15/mes para siempre** |
| Editorial | 5 | €119/mo (€159 - €40) | **€40/mes para siempre** |

**Reglas del descuento founding:**
- El descuento es una cantidad fija en €, no un porcentaje
- **Upgrade mantiene descuento**: founder corrector (€5 off) sube a Pro → paga €44 (€49-€5)
- **Downgrade pierde descuento**: si baja de tier, el descuento se pierde permanentemente
- **Grace period 90 días**: si sube de nuevo dentro de 90 días tras downgrade, recupera el descuento
- **Subida de precios**: si Corrector sube de €24→€29, el founder paga €24 (€29-€5). El descuento fijo se mantiene, la subida sí aplica
- El descuento NUNCA produce precio negativo (floor en €0)

**Device swap policy**: 2 swaps inmediatos/mes. A partir del 3o, 7 días de cooldown.
Para Editorial con puestos extra, cada puesto tiene su propio contador de swaps.

### Coste estimado

```
Costes fijos mensuales:
  Railway (app + DB):     ~15 EUR
  Dominio:                ~1 EUR (amortizado)

Por cliente (comisiones Stripe 2.9% + 0.30 EUR):
  Corrector (24 EUR):     neto ~23.00 EUR
  Profesional (49 EUR):   neto ~47.28 EUR
  Editorial (159 EUR):    neto ~154.09 EUR

Break-even: 1 cliente Corrector cubre los costes del servidor.
```

### Integracion Stripe

1. **Stripe Checkout (hosted)**: App abre browser → servidor crea Checkout Session → redirige a Stripe → despues de pago exitoso → muestra clave de licencia. Cero PCI compliance.
2. **Customer Portal**: Para gestion de suscripcion (upgrade, cancel, cambiar tarjeta). Sin UI custom necesaria.
3. **Webhooks**: Unica fuente de verdad. Eventos clave: `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`.

---

## 8. Migracion (3 fases)

### Fase 1: Enforcement Suave (2-4 semanas)

- Pipeline llama `check_feature()` pero solo AVISA (no bloquea)
- Frontend muestra banner: "Tu plan no incluye [feature]. Actualiza para mantener acceso"
- Comienza a registrar `record_usage()` para tener datos reales
- Quitar comentarios de bypass dev (log warning en vez de silent allow)

### Fase 2: Enforcement Duro (2-4 semanas despues)

- Features gated: `run_*` flags se fuerzan a `False` si tier no permite
- Quota enforced: analysis rechazada si quota agotada
- Frontend: iconos de candado en features premium, barra de uso
- Grace period de 14 dias funciona como disenado

### Fase 3: Produccion Completa (2-4 semanas despues)

- Deploy servidor de licencias
- Stripe Checkout para pagos
- Sistema de promos funcional
- Trial automatico 14d para nuevos usuarios
- Admin panel basico

### Beta testers existentes

1. Antes de Fase 2: generar licencias `beta_gift` por email de cada tester
2. Al actualizar app: "Bienvenido al lanzamiento. Introduce tu email para activar tu licencia beta"
3. Servidor busca email en lista pre-generada → devuelve clave
4. Licencias beta: tier editorial, 1 ano o indefinida

---

## 9. Edge Cases Clave

| Caso | Diseno |
|------|--------|
| Downgrade mid-analisis | Verificacion snapshot al inicio, no se re-verifica durante analisis |
| Pago falla (Stripe past_due) | Licencia activa durante reintentos (14d). Solo cancela si Stripe abandona |
| Fingerprint cambia (SSD nuevo) | Match fuzzy por machine_id → actualizar fingerprint in-place |
| Manipulacion de reloj | High-water mark + contador de regresiones. 3+ → forzar online |
| Documento 0 palabras | words_to_pages(0)=0, analisis corre pero consume 0 quota |
| Licencia expira mid-analisis | Snapshot al inicio, analisis completa, siguiente falla |
| 2 usuarios misma maquina | Cada OS user tiene su propia DB, mismo fingerprint es OK |
| Firewall corporativo | Grace period 14d + modo offline extendido para Editorial |
| Reinstall = trial infinito | Server-side fingerprint tracking (P0 item 5) |
| **Founder upgrade** | Descuento fijo (€5/15/40) persiste en tier superior. Stripe `price_data` override |
| **Founder downgrade** | Descuento se suspende. Grace period 90d para recuperarlo si sube de nuevo |
| **Founder downgrade + re-upgrade >90d** | Descuento perdido permanentemente. Es un upgrade normal sin descuento |
| **Subida de precios + founder** | Founder paga `nuevo_precio - descuento_fijo`. Ej: €29-€5=€24 |
| **Comp license expira** | Siguiente verify retorna `comp_expired`. Email 30d antes con oferta conversion |
| **Comp license revocada** | Admin revoca → siguiente verify invalida. Email de notificacion |
| **Descuento fijo > precio base** | Floor en €0. No puede producir precio negativo |

---

## Apendice A: Schema PostgreSQL del Servidor

```sql
-- Ver archivo completo en licensing-server/schema.sql cuando se implemente

-- Tablas principales:
-- users (id, email, name, stripe_customer_id)
-- licenses (id, user_id, license_key, tier, status, source,
--           is_founding_member, founding_tier, founding_discount_eur,
--           is_comp, comp_type, comp_discount_pct, comp_expires_at, comp_notes,
--           downgrade_grace_until,
--           tier_override, tier_override_until)
-- stripe_subscriptions (id, license_id, stripe_subscription_id, status, period_start/end)
-- devices (id, license_id, hardware_fingerprint, device_name, status, last_seen_at, last_ip)
-- usage_records (id, license_id, device_id, document_fingerprint, page_count, billing_period)
-- promo_codes (id, code, type, tier, duration_hours, max/current_redemptions, is_active)
-- promo_redemptions (id, promo_code_id, license_id, applied_tier, applied_until)
-- trial_records (id, hardware_fingerprint, fingerprint_components, ip_address, is_vm)
-- verification_log (id, license_id, device_id, verified_at, result, client_ip)
-- discount_events (id, license_id, event_type, old_tier, new_tier,
--                  discount_before, discount_after, notes, created_at)
-- pricing_history (id, tier, price_monthly, price_annual, effective_from)
```

## Apendice B: Calculo de precio con descuentos

```python
def calculate_monthly_price(license) -> float:
    """Calcula el precio mensual efectivo."""
    base_price = get_current_tier_price(license.tier)  # De pricing_history

    # 1. Descuento founding (solo si tier >= founding_tier original)
    if license.is_founding_member and license.tier_rank >= license.founding_tier_rank:
        if not license.downgrade_grace_until:  # No suspendido por downgrade
            base_price -= license.founding_discount_eur

    # 2. Descuento comp (si aplica y no expirado)
    if license.is_comp and license.comp_active:
        base_price *= (1 - license.comp_discount_pct / 100)

    return max(0.0, base_price)  # Floor en €0
```
