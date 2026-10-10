# Spec 0008b — Finanzas: estado de resultados, dashboard y exportación

Estado: borrador

Épica E08 (Finanzas), parte 2 de 2. Depende de: 0008a, 0006b, 0006c, 0003a, 0005b.

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

- H1: Como dueño, quiero ver el estado de resultados de cualquier período, compararlo con el anterior y abrir el detalle de cada línea.
- H2: Como usuario, quiero un dashboard con los indicadores que me tocan según mi rol.
- H3: Como contador, quiero exportar los reportes a CSV para trabajarlos en Excel.

## Definiciones

**Estado de resultados** (importes sin IGV ni ISC, RN-FIN-01):

| Línea | Cálculo |
|---|---|
| **Ventas netas** | Σ valor de venta de las ventas registradas en el período (con cualquier estado de su comprobante, incluido el interno) − Σ valor de venta de las ventas **anuladas en el período** |
| (−) **Costo de ventas** | Σ costo congelado de las líneas no gratuitas de las ventas emitidas en el período − Σ costo de las ventas anuladas en el período **con reingreso de mercadería** |
| (−) **Mermas y ajustes de inventario** | Σ costo de las salidas por ajuste (`MERMA`, `CONTEO`, `CORRECCION`), por cierre de OP con saldo y por envasado de descarte − Σ costo de las entradas por ajuste (excepto `SALDO_INICIAL` y `TRANSFERENCIA`), incluidas sus anulaciones |
| (−) **Pérdidas de producción** | Σ costo de las OP terminadas con 0 L en el período (lote perdido, pendiente PRD Q10) |
| = **Utilidad bruta** | |
| (−) **Gastos operativos** | Σ gastos del período por categoría + **Gastos de venta: entregas gratuitas** (costo del producto entregado + ISC e IGV asumidos, neto de anulaciones) |
| = **Utilidad operativa** | |

**Indicadores:** margen bruto % = utilidad bruta / ventas netas · margen operativo % = utilidad operativa / ventas netas · litros producidos · costo promedio por litro · unidades vendidas por producto · margen por tipo (cerveza propia vs. mercadería).

**Fecha que ubica cada importe en un período:** ventas, por su fecha de emisión; anulaciones de ventas y de gastos, por su fecha de anulación; mermas y ajustes, por la fecha del movimiento; pérdidas de producción, por la fecha de fin de la OP; gastos, por la fecha del documento; entregas gratuitas, por su fecha de emisión.

**Período:** rango de fechas en hora de Lima, con ambos extremos incluidos (RN-FIN-06).

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-FIN-03 Ver estado de resultados

- RF-FIN-06: CUANDO un usuario con `finanzas.resultados.ver` elige un período (por defecto, el mes actual), EL SISTEMA calcula el estado de resultados según Definiciones, con los indicadores, y opcionalmente lo compara con el período anterior.
- RF-FIN-07: EL SISTEMA usa siempre el costo congelado de cada venta, nunca el costo actual (RN-FIN-02).
- RF-FIN-08: CUANDO se anula una venta, EL SISTEMA la resta en el período en que se anula, no en el de la venta original (RN-FIN-03).
- RF-FIN-09: EL SISTEMA excluye del resultado los ajustes `SALDO_INICIAL` y sus anulaciones (RN-FIN-04), y las transferencias entre almacenes.
- RF-FIN-10: EL SISTEMA trata las entregas gratuitas como gastos de venta, no como venta ni costo de ventas (RN-FIN-07).
- RF-FIN-11: CUANDO el usuario abre una línea del estado de resultados, EL SISTEMA muestra las ventas, movimientos, OP o gastos que la componen, y su suma es exactamente la de la línea.
- RF-FIN-12: EL SISTEMA lista aparte las ventas anuladas cuya nota de crédito todavía no fue aceptada y las ventas cuyo comprobante está `RECHAZADO` sin reemitir.
- RF-FIN-13: SI el período no tiene ventas, ENTONCES EL SISTEMA muestra los márgenes como "—" en lugar de dividir por cero.

### UC-FIN-04 Ver dashboard de indicadores

- RF-FIN-14: CUANDO un usuario con `core.dashboard.ver` abre el dashboard, EL SISTEMA le muestra solo los avisos de su permiso. Las cifras de ventas son valor de venta sin IGV ni ISC, como en el estado de resultados:

| Aviso | Permiso |
|---|---|
| Ventas de hoy, ventas del mes, ventas por día (30 días) | `ventas.venta.ver` |
| Utilidad bruta, margen bruto, top 5 productos por utilidad | `finanzas.resultados.ver` |
| Stock bajo, lotes por vencer | `inventario.stock.ver` |
| Pedidos atrasados | `ventas.pedido.ver` |
| Comprobantes que requieren atención, % aceptados en 24 h | `facturacion.comprobante.ver` |

### UC-FIN-05 Exportar reportes a CSV

- RF-FIN-15: CUANDO un usuario con `reportes.exportar` y permiso para ver el reporte exporta el estado de resultados, las ventas detalladas (con costo y utilidad por línea), el kardex, el stock valorizado, los gastos o la bandeja de comprobantes, EL SISTEMA genera un CSV en UTF-8 con BOM, separador coma y punto decimal, que respeta los filtros aplicados.
- RF-FIN-16: MIENTRAS el usuario no tenga `inventario.costo.ver`, EL SISTEMA omite los costos unitarios y la valorización del inventario en las exportaciones (épica 0001, RF-TEN-51). El estado de resultados se exporta con sus totales a quien tenga `finanzas.resultados.ver`.

## Requisitos no funcionales

- RNF-FIN-01: El estado de resultados, su exportación CSV y la API dan exactamente las mismas cifras (una sola fuente de cálculo).
- RNF-FIN-02: El estado de resultados de un mes responde en menos de 800 ms (p95) con el volumen del PRD §7.
- RNF-FIN-03: El estado de resultados de una empresa nunca incluye datos de otra.

## Casos límite

- Venta de octubre anulada en noviembre: suma en octubre y resta en noviembre.
- Venta del 30-nov a las 23:30 (hora de Lima): cae en noviembre.
- Anulación de una venta sin reingreso de mercadería: resta ventas, pero no costo.
- Corrección del cliente de una venta (NC motivo `02` + comprobante nuevo): no cambia ventas ni costo.
- Entrega gratuita de 5 barriles de 20 L con valor referencial 500.00 y costo 300.00: ventas 0, costo de ventas 0, gastos de venta 686.18 (ISC 251.00 + IGV 135.18 + costo 300.00).

## Fuera de alcance

Cuentas por cobrar y por pagar, caja y bancos, flujo de caja, cierre de períodos, presupuestos, gastos financieros, impuesto a la renta, utilidad neta, plan contable y asientos, PLE.

## Criterios de finalización

- El estado de resultados del mes del piloto cuadra con la conciliación manual del contador (diferencia por redondeo ≤ S/ 1.00).
- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **PRD Q10:** la línea "Pérdidas de producción" depende de que se apruebe el lote perdido.
