# Spec 0006c — Ventas: anulación y corrección de cliente

Estado: borrador

Épica E06 (Ventas y pedidos), parte 3 de 3. Depende de: 0006b. La usan: 0007c, 0008b.

## Contexto y objetivo

La cervecera vende sobre todo a pedido (bares, restaurantes, distribuidores) y en menor medida al público, donde también vende mercadería de reventa. Necesita registrar el pedido, saber si hay que producir o comprar, entregar con el lote correcto, facturar y conocer el costo real de lo vendido.

**Objetivo:** que cada venta salga del lote correcto, con su costo congelado y su comprobante, y que cada pedido muestre en todo momento qué falta para entregarlo.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Ventas | Gestiona clientes y pedidos, registra ventas |
| Gerente / Administrador | Además anula ventas y cancela pedidos |
| Producción | Ve los pedidos vinculados a sus OP (lectura) |

## Historias de usuario

- H1: Como gerente, quiero anular una venta con el motivo SUNAT correcto y decidir si la mercadería vuelve al almacén.

## Definiciones

**Motivos de nota de crédito (catálogo 09 de SUNAT) usados en el MVP:** `01` Anulación de la operación y `06` Devolución total, al anular una venta (UC-VEN-06); `02` Anulación por error en el RUC, al corregir el cliente de una venta (UC-VEN-08).

- **Línea comercial, desglose de impuestos y fecha de emisión:** ver spec 0006b.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-VEN-06 Anular venta

- RF-VEN-32: CUANDO un usuario con `ventas.venta.anular` anula una venta con el motivo `01` o `06`, EL SISTEMA la pasa a `ANULADA` de inmediato, sin esperar a SUNAT, y registra su nota de crédito en la misma operación (RN-VEN-09). *Regla pendiente de validación del contador (constitución, art. 5.5).*
- RF-VEN-33: CUANDO se anula una venta, EL SISTEMA pregunta si la mercadería vuelve al almacén (por defecto sí); si vuelve, la reingresa a los mismos lotes y al costo original.
- RF-VEN-34: CUANDO la mercadería de una venta anulada no vuelve al almacén, EL SISTEMA mantiene su costo de ventas.
- RF-VEN-35: CUANDO se anula una venta que venía de un pedido, EL SISTEMA devuelve el pedido a `LISTO` si la mercadería volvió al almacén, o a `CONFIRMADO` si no volvió.
- RF-VEN-36: SI dos usuarios anulan la misma venta a la vez, ENTONCES EL SISTEMA la anula una sola vez.

### UC-VEN-08 Corregir el cliente de una venta

- RF-VEN-39: CUANDO un usuario con `ventas.venta.anular` corrige el cliente de una venta cuyo comprobante fue aceptado (p. ej. por un RUC errado), EL SISTEMA emite una nota de crédito con motivo `02` sobre el comprobante original y un comprobante nuevo para el cliente correcto, con las mismas líneas e importes. La venta sigue `EMITIDA`, sin movimiento de stock y sin cambio en su costo.
- RF-VEN-40: SI el comprobante original todavía no fue aceptado, ENTONCES EL SISTEMA rechaza la corrección hasta que lo sea.

## Requisitos no funcionales

- Ninguno propio.

## Casos límite

- **Devolución parcial** (p. ej. 2 de 24 botellas): las NC parciales están fuera del MVP. Se anula la venta completa con reingreso y se registra una venta nueva por lo que el cliente se queda.
- Una venta anulada cuyo comprobante aún no fue aceptado: la venta queda anulada y la NC espera (épica 0007).

## Fuera de alcance

Leads y oportunidades, cotizaciones formales, reserva de stock, entregas parciales, listas de precios por cliente, descuentos por volumen, cuentas por cobrar y cobranza, guía de remisión, POS offline, NC parciales.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **PO y contador:** confirmar que la venta se anula de inmediato y la NC espera a que se acepte el comprobante original (RF-VEN-32).
