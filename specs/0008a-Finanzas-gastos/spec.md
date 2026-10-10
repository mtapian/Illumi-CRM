# Spec 0008a — Finanzas: gastos operativos

Estado: borrador

Épica E08 (Finanzas), parte 1 de 2. Depende de: 0001a, 0004a. La usan: 0008b.

## Contexto y objetivo

El dueño necesita saber cuánto ganó en el mes. El sistema de referencia calcula una "utilidad" con el costo **actual** del producto (no el histórico) y sin gastos operativos, así que no refleja la realidad.

**Objetivo:** un estado de resultados mensual hasta la utilidad operativa que cuadre con la conciliación del contador (diferencia ≤ S/ 1.00), sin planillas externas.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Administrador / Gerente | Registran y anulan gastos, ven el estado de resultados, exportan |
| Todos los roles | Ven el dashboard, con los avisos que su permiso habilita |
| Contador | Recibe las exportaciones CSV (fuera del sistema) |

## Historias de usuario

- H1: Como administrador, quiero registrar los gastos operativos del mes con su documento para que entren en la utilidad.

## Definiciones

**Gasto del período de un documento:** con `FACTURA`, la base (el IGV es crédito fiscal); con `BOLETA` o `SIN_DOCUMENTO`, el total; con `RECIBO_HONORARIOS`, el monto bruto (incluye la retención de cuarta categoría).

**Fecha que ubica cada importe en un período:** ventas, por su fecha de emisión; anulaciones de ventas y de gastos, por su fecha de anulación; mermas y ajustes, por la fecha del movimiento; pérdidas de producción, por la fecha de fin de la OP; gastos, por la fecha del documento; entregas gratuitas, por su fecha de emisión.

**Período:** rango de fechas en hora de Lima, con ambos extremos incluidos (RN-FIN-06).

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-FIN-01 Registrar gasto operativo

- RF-FIN-01: CUANDO un usuario con `finanzas.gasto.registrar` registra un gasto con fecha, categoría, descripción, proveedor (opcional), tipo y número de documento e importes, EL SISTEMA lo guarda y calcula el gasto del período según el tipo de documento.
- RF-FIN-02: SI la fecha es posterior a hoy o el importe no es mayor a 0, ENTONCES EL SISTEMA rechaza el gasto.
- RF-FIN-03: CUANDO se registra una empresa, EL SISTEMA le crea las categorías Planilla, Alquiler, Servicios, Marketing, Transporte y distribución, Mantenimiento y Otros; el administrador puede crear más.
- RF-FIN-04: CUANDO se registra un gasto de una categoría marcada "de planta", EL SISTEMA advierte que no debe duplicar un costo indirecto ya cargado a una OP (RN-FIN-05).

### UC-FIN-02 Anular gasto

- RF-FIN-05: CUANDO un usuario con `finanzas.gasto.anular` anula un gasto con motivo, EL SISTEMA resta su importe en el período en que se anula; si es el mismo período del gasto, el efecto neto es cero (RN-FIN-03).

## Requisitos no funcionales

- Ninguno propio.

## Casos límite

- Gasto con fecha en un período ya revisado: se permite y ese período cambia (el cierre de períodos es R2).

## Fuera de alcance

Cuentas por cobrar y por pagar, caja y bancos, flujo de caja, cierre de períodos, presupuestos, gastos financieros, impuesto a la renta, utilidad neta, plan contable y asientos, PLE.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Contador (PRD Q12):** el costo indirecto por OP frente a los gastos de planta: ¿se mantiene la advertencia (RF-FIN-04) o se vincula el gasto a la OP?
