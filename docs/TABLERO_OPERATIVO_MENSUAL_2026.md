# Tablero Operativo Mensual 2026 (Bootstrap)

Fecha base: 2026-02-13  
Objetivo anual: 90 clientes activos de pago

## 1. Como usar este tablero

Frecuencia:
- Actualizacion semanal de datos.
- Cierre mensual con decisiones.

Regla de lectura:
- `Delta < -10%` en clientes o MRR: activar plan de correccion del mes siguiente.
- `Churn > objetivo`: priorizar producto/soporte sobre captacion.
- `Conversion Corrector -> Pro` por debajo de objetivo: revisar messaging y triggers de upgrade.

## 2. KPI operativos mensuales

Definiciones:
- `Clientes activos`: clientes de pago activos al cierre de mes.
- `MRR neto`: clientes activos x ARPU neto de referencia (35.62 EUR) como aproximacion.
- `Conversion C->P`: % de Corrector que suben a Pro en el mes.
- `Churn`: % de clientes que cancelan en el mes.

## 3. Metas por mes (plan base a 90 clientes)

| Mes | Clientes activos objetivo | MRR neto objetivo (EUR, aprox) | Conversion C->P objetivo | Churn objetivo |
|---|---:|---:|---:|---:|
| M1 | 5 | 180 | 0.5% | <= 10% |
| M2 | 12 | 427 | 0.7% | <= 9% |
| M3 | 20 | 712 | 0.8% | <= 8% |
| M4 | 28 | 997 | 1.0% | <= 7% |
| M5 | 36 | 1.282 | 1.1% | <= 6.5% |
| M6 | 45 | 1.603 | 1.3% | <= 6% |
| M7 | 53 | 1.888 | 1.4% | <= 5.5% |
| M8 | 61 | 2.173 | 1.5% | <= 5.2% |
| M9 | 70 | 2.493 | 1.6% | <= 5% |
| M10 | 77 | 2.743 | 1.7% | <= 4.7% |
| M11 | 84 | 2.992 | 1.8% | <= 4.4% |
| M12 | 90 | 3.206 | 2.0% | <= 4% |

## 4. Plantilla de seguimiento mensual (copiar/pegar)

## Mes: M__

### Resultado
- Clientes activos: objetivo __ / real __ / delta __%
- MRR neto: objetivo __ / real __ / delta __%
- Conversion C->P: objetivo __ / real __
- Churn: objetivo __ / real __
- Soporte (h/mes): objetivo __ / real __
- Comercial (EUR/mes): objetivo __ / real __

### Diagnostico
- Que funciono:
- Que no funciono:
- Bloqueadores:

### Decisiones para el mes siguiente
- Producto:
- Comercial:
- Soporte/operaciones:
- Riesgos y mitigaciones:

## 5. Tabla anual de control (rellenable)

| Mes | Clientes obj | Clientes real | Delta % | MRR obj | MRR real | Delta % | Conv C->P obj | Conv C->P real | Churn obj | Churn real | Soporte h | Comercial EUR | Semaforo |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| M1 | 5 |  |  | 180 |  |  | 0.5% |  | <=10% |  |  |  |  |
| M2 | 12 |  |  | 427 |  |  | 0.7% |  | <=9% |  |  |  |  |
| M3 | 20 |  |  | 712 |  |  | 0.8% |  | <=8% |  |  |  |  |
| M4 | 28 |  |  | 997 |  |  | 1.0% |  | <=7% |  |  |  |  |
| M5 | 36 |  |  | 1.282 |  |  | 1.1% |  | <=6.5% |  |  |  |  |
| M6 | 45 |  |  | 1.603 |  |  | 1.3% |  | <=6% |  |  |  |  |
| M7 | 53 |  |  | 1.888 |  |  | 1.4% |  | <=5.5% |  |  |  |  |
| M8 | 61 |  |  | 2.173 |  |  | 1.5% |  | <=5.2% |  |  |  |  |
| M9 | 70 |  |  | 2.493 |  |  | 1.6% |  | <=5% |  |  |  |  |
| M10 | 77 |  |  | 2.743 |  |  | 1.7% |  | <=4.7% |  |  |  |  |
| M11 | 84 |  |  | 2.992 |  |  | 1.8% |  | <=4.4% |  |  |  |  |
| M12 | 90 |  |  | 3.206 |  |  | 2.0% |  | <=4% |  |  |  |  |

## 6. Reglas de semaforo

- Verde:
  - clientes y MRR >= 95% del objetivo mensual,
  - churn dentro de objetivo.
- Amarillo:
  - clientes o MRR entre 85% y 94%,
  - o churn hasta +1 punto sobre objetivo.
- Rojo:
  - clientes o MRR < 85%,
  - o churn > objetivo +1 punto.

Accion por color:
- Verde: mantener plan y optimizar conversion.
- Amarillo: ajuste tactico de captacion y onboarding.
- Rojo: plan de choque 30 dias (producto + retencion + comercial).
