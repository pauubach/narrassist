# Estudio de Viabilidad Comercial (Espana)

Fecha: 2026-02-13  
Producto: Narrative Assistant (desktop, local-first)

## 1. Objetivo y alcance

Este documento estima:
- viabilidad economica realista (no solo infraestructura),
- coste inicial y coste mensual operativos,
- clientes necesarios por escenario,
- conversion esperable de `Corrector` a `Profesional`.

## 2. Inputs economicos

### 2.1 Pricing y neto por cliente (fuente interna)

Fuente: `docs/LICENSING_PRODUCTION_PLAN.md` (seccion "Coste estimado").

- Coste fijo mensual infraestructura licencias:
  - Railway (app + DB): ~15 EUR/mes
  - Dominio: ~1 EUR/mes
  - Total fijo base: **~16 EUR/mes**
- Neto por cliente (despues de Stripe 2.9% + 0.30 EUR):
  - Corrector (24 EUR): **~23.00 EUR/mes**
  - Profesional (49 EUR): **~47.28 EUR/mes**
  - Editorial (159 EUR): **~154.09 EUR/mes**

### 2.2 Estimacion propia de coste inicial (C0)

Se estima C0 incluyendo un mes de desarrollo y puesta en marcha.
No es presupuesto contable exacto; es una aproximacion de negocio para decidir.

Componentes de C0:
- Tiempo de desarrollo fundador: horas del mes x coste/hora de oportunidad.
- Herramientas IA de desarrollo (Claude/Codex y similares).
- Setup inicial legal/fiscal y operativa comercial minima.
- Preparacion de lanzamiento (material comercial, web minima, demos).
- Contingencia tecnica.

Escenarios de C0:
- `Prudente`: **6.000 EUR**
- `Base`: **9.700 EUR**
- `Exigente`: **16.700 EUR**

### 2.3 Estimacion propia de coste mensual (OPEX_m)

Componentes de OPEX:
- Soporte + mantenimiento + mejoras (tiempo mensual propio).
- Herramientas IA recurrentes.
- Infraestructura y utilidades operativas.
- Comercial/captacion continua.
- Gestion administrativa.

Escenarios de OPEX mensual:
- `Prudente`: **1.200 EUR/mes**
- `Base`: **1.876 EUR/mes**
- `Exigente`: **3.200 EUR/mes**

### 2.4 Formula operativa

Variables:
- `C0`: coste inicial total.
- `OPEX_m`: coste operativo mensual.
- `ARPU_aj`: ingreso neto medio por cliente/mes (mix de tiers y descuento anual).
- `N_eq`: clientes de equilibrio para recuperar C0 en `m` meses.

Formula:
- `N_eq = ceil((OPEX_m + C0/m) / ARPU_aj)`

### 2.5 Modelo recomendado para tu caso (bootstrap por reinversion)

Dado que no hay presupuesto inicial de caja, conviene trabajar con dos vistas:

- `Caja` (decision operativa):
  - `C0_cash = 0`
  - objetivo: no quedarte sin liquidez mensual.
- `Economica` (decision estrategica):
  - imputar tu tiempo con tarifa objetivo (60-80 EUR/h) para no infraestimar el negocio.

Regla:
- usar `Caja` para operar a corto plazo,
- usar `Economica` para decidir pricing, roadmap y objetivo de clientes.

## 3. Mercado (fuentes externas)

## 3.1 Demanda editorial

- En 2024: **89.347 titulos ISBN** y **3.158 editores con actividad**.  
  Fuente: https://publishnews.es/la-produccion-editorial-espanola-aumento-un-2-9-en-2024-con-89-347-titulos-inscritos
- Confirmacion del dato de editores activos (3.158).  
  Fuente: https://presidencia.gva.es/es/web/promocio-institucional/revista-gv/actualidad/-/asset_publisher/EP4nXqEvh8ZB/content/la-produccion-editorial-espanola-aumenta-un-2-9-en-2024-con-89-347-titulos-inscritos
- Mercado del libro en Espana: **3.037,51 M EUR** y **85.542 titulos** (ultimo informe publicado citado por el sector).  
  Fuente: https://www.gremieditors.cat/espana-libro-facturacion-2024/

## 3.2 Oferta profesional (proxy correctores)

No hay censo unico publico de correctores en Espana. Proxy util:
- CNAE 7430 (traduccion e interpretacion): **1.378 empresas**.  
  Fuente: https://www.empresia.es/Actividad/ACTIVIDADES-DE-TRADUCCION-E-INTERPRETACION/

## 4. TAM / SAM / SOM (estimacion)

- TAM operacional: **2.500-6.000 cuentas** (freelance + microestudios + equipos editoriales).
- SAM 12-24 meses (foco narrativa/correccion profesional): **2.000-4.000 cuentas**.

Objetivos SOM orientativos:
- `Prudente`: 50 clientes
- `Base`: 90 clientes
- `Ambicioso`: 150 clientes

Penetracion estimada sobre SAM:
- 50 clientes: 1.25%-2.5%
- 90 clientes: 2.25%-4.5%
- 150 clientes: 3.75%-7.5%

## 5. Viabilidad economica (con costes estimados)

## 5.1 ARPU ajustado usado

Mix de referencia de tiers:
- 70% Corrector, 25% Profesional, 5% Editorial.

ARPU neto:
- Mix con mayor peso mensual: **~35.62 EUR/mes**
- Sensibilidad con 40% de clientes en anual: **~32.29 EUR/mes**
- Sensibilidad con 60% de clientes en anual: **~30.62 EUR/mes**

## 5.2 Clientes necesarios (N_eq)

Recuperacion de C0 en 12 meses:

| Escenario | C0 | OPEX_m | N_eq (mix mensual) | N_eq (40% anual) | N_eq (60% anual) |
|---|---:|---:|---:|---:|---:|
| Prudente | 6.000 | 1.200 | 48 | 53 | 56 |
| Base | 9.700 | 1.876 | 76 | 84 | 88 |
| Exigente | 16.700 | 3.200 | 129 | 143 | 150 |

Recuperacion de C0 en 18 meses:

| Escenario | N_eq (mix mensual) | N_eq (40% anual) | N_eq (60% anual) |
|---|---:|---:|---:|
| Prudente | 44 | 48 | 51 |
| Base | 68 | 75 | 79 |
| Exigente | 116 | 128 | 135 |

Lectura:
- El negocio es viable, pero la referencia realista no es "24 clientes".
- Con costes completos de operacion, el umbral razonable suele estar en **75-90 clientes** (escenario base, 12-18 meses).

## 5.3 Escenario recomendado para planificacion

Para gestion real del proyecto, usar `Base` como caso principal:
- C0 ~9.700 EUR
- OPEX_m ~1.876 EUR/mes
- Objetivo de equilibrio:
  - 12 meses: 84-88 clientes (si anual tiene peso alto)
  - 18 meses: 75-79 clientes

## 5.4 Viabilidad en bootstrap (sin C0 de caja)

Con `C0_cash = 0`, el equilibrio depende solo de OPEX mensual de caja.

| OPEX caja mensual | Clientes eq (ARPU 35.62) | Clientes eq (ARPU 30.62) |
|---:|---:|---:|
| 300 EUR | 9 | 10 |
| 600 EUR | 17 | 20 |
| 800 EUR | 23 | 27 |
| 1.200 EUR | 34 | 40 |
| 1.700 EUR | 48 | 56 |
| 2.500 EUR | 71 | 82 |

Lectura:
- si arrancas muy lean (300-600 EUR/mes), el break-even de caja llega con ~10-20 clientes.
- si subes comercial/operacion pronto (1.200-1.700 EUR/mes), necesitas ~34-56 clientes.

## 5.5 Tu coste/hora (60-80) con transicion gradual

Bajar temporalmente tu coste/hora para reinvertir es valido, pero debe ser una fase
deliberada con escalado claro.

Propuesta por tramos:
- 0-20 clientes: 0-20 EUR/h efectivo.
- 20-50 clientes: 20-35 EUR/h.
- 50-90 clientes: 35-50 EUR/h.
- 90-120 clientes: 50-60 EUR/h.
- 120+ clientes: objetivo 60-80 EUR/h.

Ejemplo rapido (mix 70/25/5):
- 90 clientes -> MRR neto ~2.756-3.206 EUR/mes.
- Si OPEX caja = 1.000 y reservas 20%, quedan ~1.205-1.565 EUR/mes para founder draw.
- 150 clientes -> MRR neto ~4.593-5.344 EUR/mes.
- Si OPEX caja = 1.600 y reservas 20%, quedan ~2.074-2.675 EUR/mes para founder draw.

## 6. Conversion Corrector -> Profesional

## 6.1 Facilidad de conversion

La conversion es razonable por dos motivos:
- `Profesional` duplica cuota de paginas (1.500 -> 3.000).
- `Profesional` aporta valor funcional adicional (no solo volumen).

## 6.2 Rango de conversion factible

Estimacion sobre cartera activa de Corrector:
- sin palancas de upsell bien ejecutadas: **6%-10% anual**
- con S16A (alertas de cuota + comparativa de tiers + mensajes por valor): **12%-18% anual**

Caso base recomendado para plan financiero:
- **12%-15% anual**

## 6.3 Packs y riesgo de canibalizacion

El pack de paginas (BK-29) puede canibalizar parcialmente solo en usuarios
de alto volumen que no perciben necesidad de features Pro.

Mitigaciones:
- posicionar pack como solucion puntual, no sustituto permanente de Pro,
- activar CTA de upgrade cuando hay repeticion de compra de packs,
- comunicar upgrade por valor funcional (no solo por "mas paginas").

## 7. Conclusiones

1. El coste de infraestructura es bajo, pero no representa el coste real del negocio.
2. Incluyendo tiempo, soporte, mantenimiento y comercial, el umbral de viabilidad sube de forma importante.
3. Con supuestos base, el objetivo razonable para sostenibilidad es **75-90 clientes**.
4. El mercado objetivo en Espana permite ese nivel de captacion con penetracion baja-moderada del SAM.
5. La conversion Corrector -> Pro es una palanca central y debe trabajarse como objetivo de producto/comercial.

## 8. Objetivo recomendado (12 meses)

Objetivo operativo recomendado (bootstrap):
- **Fase 1**: 20 clientes (estabilizar caja minima).
- **Fase 2**: 50 clientes (financiar soporte/comercial basico).
- **Fase 3**: 90 clientes (sostenibilidad operativa robusta).

Distribucion orientativa:
- 59 Corrector / 23 Profesional / 8 Editorial.

Objetivo minimo aceptable:
- **75 clientes** (si se acepta recuperacion a 18 meses y control estricto de OPEX).

Objetivo para converger a tarifa completa (60-80 EUR/h):
- **120-150 clientes**, segun mezcla de anual, OPEX y horas efectivas dedicadas.

## 9. Politica de reinversion (si priorizas crecimiento a largo plazo)

Si aceptas cobrar menos o cero al inicio, la estrategia recomendada es:

- Modo `Reinversion total` hasta validacion comercial:
  - founder draw = 0 o minimo simbolico,
  - reinvertir el margen en producto, onboarding y captacion.

Reglas por fase:
- Fase A (0-30 clientes):
  - 70%-80% del margen libre a producto/comercial,
  - 20%-30% a reserva de caja.
- Fase B (30-70 clientes):
  - 50%-60% reinversion,
  - founder draw limitado (10%-20% del margen libre),
  - objetivo: estabilizar retencion y conversion.
- Fase C (70-120 clientes):
  - 30%-40% reinversion,
  - founder draw 25%-35% del margen libre.
- Fase D (120+ clientes):
  - converger progresivamente a tarifa objetivo 60-80 EUR/h,
  - mantener 20%-30% de reinversion para crecimiento.

Guardarrailes recomendados:
- mantener reserva de caja minima: 3 meses de OPEX de caja,
- no subir founder draw si cae retencion o sube churn,
- revisar trimestralmente pricing y conversion Corrector -> Profesional.

Interpretacion:
- esta estrategia acelera adopcion y mejora producto,
- pero aplaza retribucion personal; requiere disciplina financiera y umbrales claros.

## 10. Plan trimestral (Q1-Q4) con objetivos operativos

Objetivo anual de referencia: **90 clientes** en 12 meses.

KPIs principales:
- clientes de pago activos,
- conversion `Corrector -> Profesional`,
- churn mensual,
- tiempo de soporte por cliente,
- margen libre para reinversion.

### Q1 (meses 1-3) - Validacion comercial inicial

Meta fin Q1:
- **20 clientes** activos.
- Mix objetivo: ~16 Corrector / 3 Profesional / 1 Editorial.

Objetivos KPI:
- churn mensual <= 8%.
- conversion Corrector -> Profesional >= 2% trimestral.
- tiempo medio de onboarding <= 60 min por cliente nuevo.

Presupuesto orientativo:
- comercial: **300-500 EUR/mes**.
- soporte + mantenimiento: **6-12 h/mes**.

Foco:
- cerrar friccion de onboarding,
- convertir feedback en mejoras visibles cada 2 semanas,
- construir 3-5 casos de uso reales para ventas.

### Q2 (meses 4-6) - Traccion y repetibilidad

Meta fin Q2:
- **45 clientes** activos acumulados.
- Mix objetivo: ~33 Corrector / 10 Profesional / 2 Editorial.

Objetivos KPI:
- churn mensual <= 6%.
- conversion Corrector -> Profesional >= 3%-4% trimestral.
- NPS cualitativo (entrevistas) >= 30.

Presupuesto orientativo:
- comercial: **500-800 EUR/mes**.
- soporte + mantenimiento: **12-20 h/mes**.

Foco:
- estandarizar demo y argumentario por tipo de cliente,
- mejorar paywall/upsell de valor funcional (no solo cuota),
- lanzar 1 iniciativa de referral o partners editoriales.

### Q3 (meses 7-9) - Escalado controlado

Meta fin Q3:
- **70 clientes** activos acumulados.
- Mix objetivo: ~50 Corrector / 16 Profesional / 4 Editorial.

Objetivos KPI:
- churn mensual <= 5%.
- conversion Corrector -> Profesional >= 4%-5% trimestral.
- tiempo de primera respuesta soporte <= 24h laboral.

Presupuesto orientativo:
- comercial: **800-1.100 EUR/mes**.
- soporte + mantenimiento: **20-35 h/mes**.

Foco:
- mejorar eficiencia de soporte (FAQ, plantillas, base de conocimiento),
- acelerar roadmap que impacta retencion (S16A/S16B segun estado),
- monitorizar cohortes para detectar donde se pierde conversion.

### Q4 (meses 10-12) - Consolidacion y optimizacion de margen

Meta fin Q4:
- **90 clientes** activos acumulados.
- Mix objetivo: **59 Corrector / 23 Profesional / 8 Editorial**.

Objetivos KPI:
- churn mensual <= 4%.
- conversion Corrector -> Profesional >= 5%-6% trimestral.
- ratio reinversion sostenible: 30%-40% del margen libre.

Presupuesto orientativo:
- comercial: **1.000-1.500 EUR/mes**.
- soporte + mantenimiento: **30-45 h/mes**.

Foco:
- optimizacion de pricing/packaging con datos reales,
- formalizar playbook de ventas y retencion,
- empezar convergencia gradual a retribucion fundador objetivo.

## 11. Reglas de ajuste trimestral

Recalibrar cada trimestre:
- Si clientes reales < 85% del objetivo trimestral:
  - subir reinversion comercial +10%-20%,
  - congelar subida de founder draw.
- Si churn > objetivo trimestral:
  - priorizar producto/soporte sobre adquisicion.
- Si conversion Corrector -> Pro < objetivo:
  - revisar onboarding y mensajeria de valor Pro,
  - ajustar trigger de upgrade y pricing de packs.
- Si se supera objetivo trimestral > 110%:
  - aumentar reserva de caja antes de subir gasto fijo.

## 12. Documentos operativos relacionados

- Casos de uso de ventas adaptados al producto:
  - `docs/CASOS_USO_VENTAS_NARRATIVE_ASSISTANT.md`
- Tablero operativo mensual (ejecucion y seguimiento):
  - `docs/TABLERO_OPERATIVO_MENSUAL_2026.md`
  - `docs/TABLERO_OPERATIVO_MENSUAL_2026.xlsx`
