# Spec 0006b — Ventas: registro de la venta

Estado: borrador

Épica E06 (Ventas y pedidos), parte 2 de 3. Depende de: 0006a, 0002c, 0003a. La usan: 0006c, 0007a, 0008b.

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

- H1: Como vendedor, quiero registrar una venta (desde un pedido o directa en mostrador) que descuente el lote correcto y emita su comprobante.
- H2: Como vendedor, quiero vender a crédito en cuotas a clientes con RUC.
- H3: Como vendedor, quiero registrar degustaciones y regalos como entregas gratuitas, con sus impuestos correctos.

## Definiciones

- **Línea comercial:** producto + precio dentro de una venta. Los impuestos se calculan por línea comercial, aunque FEFO la reparta entre varios lotes.

- **Valor referencial:** valor de mercado sin impuestos de una entrega gratuita (por defecto se deriva del precio de lista; editable).

**Desglose de impuestos por línea comercial** (precio de lista con impuestos incluidos):

- Sin ISC: `valor = round(total / (1 + IGV%), 2)`; `IGV = total − valor`.

- Con ISC (producto con categoría de ISC de Sistema Específico, épica 0002): `ISC = round(cantidad × contenido_L × tarifa vigente, 2)`; `valor = round(total / (1 + IGV%) − ISC, 2)`; `IGV = total − valor − ISC`. Base del IGV = valor + ISC.

- Ejemplo: 24 botellas de 330 ml a 12.00 sin ISC → valor 244.07 + IGV 43.93 = 288.00. Con ISC de S/ 2.51/L → 7.92 L, ISC 19.88, valor 224.19, IGV 43.93, total 288.00.

**Fecha de emisión de una venta:** la fecha de registro de la venta, en hora de Lima. No se registran ventas con fecha pasada ni futura.

- **Producto vendible, cliente genérico, precio de lista y estados del pedido:** ver spec 0006a.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-VEN-05 Registrar venta

- RF-VEN-17: CUANDO un usuario con `ventas.venta.registrar` registra una venta desde un pedido `CONFIRMADO`, `EN_PRODUCCION` o `LISTO`, EL SISTEMA precarga el cliente, las líneas y los precios, y entrega el pedido completo.
- RF-VEN-18: CUANDO se registra una venta directa, EL SISTEMA propone el cliente "Clientes varios" y permite buscar productos vendibles (presentaciones y mercadería, mezclados).
- RF-VEN-19: CUANDO se registra una venta, EL SISTEMA pide tipo de comprobante (`FACTURA`/`BOLETA`), almacén y forma de pago (`CONTADO` o `CREDITO`). Solo en ventas al contado pide además el método de pago (`EFECTIVO`, `TARJETA`, `TRANSFERENCIA`, `YAPE`, `PLIN`) y, si es efectivo, el monto recibido, y calcula el vuelto.
- RF-VEN-20: CUANDO un producto de la venta tiene lote y el usuario no elige uno, EL SISTEMA asigna los lotes por FEFO (épica 0003). *(0002a enmienda 6, aprobada 2026-10-12)* El usuario puede elegir el lote de cada línea; si no lo elige, EL SISTEMA aplica la estrategia de salida del producto (FEFO o FIFO). La mercadería sin lote sale solo por almacén.
- RF-VEN-21: CUANDO se confirma la venta, EL SISTEMA saca el stock, **congela el costo** de cada línea, la numera `V-000001` por empresa y emite su comprobante electrónico (épica 0007). Un cambio posterior del costo promedio no altera el costo de la venta (RN-VEN-04).
- RF-VEN-38: EL SISTEMA usa como fecha de emisión de la venta la fecha en que se registra (hora de Lima); no permite registrar ventas con fecha pasada ni futura.
- RF-VEN-22: EL SISTEMA calcula los impuestos por línea comercial según el desglose de Definiciones, con el IGV y la tarifa de ISC vigentes a la fecha de emisión. Si FEFO reparte una línea entre lotes, el comprobante sigue teniendo una sola línea. En una venta desde pedido se mantiene el precio congelado (con impuestos) y se recalcula su desglose (RN-VEN-07).
- RF-VEN-23: SI se intenta vender un producto que no es vendible o está inactivo, ENTONCES EL SISTEMA lo rechaza con "Solo se pueden vender presentaciones y mercadería activas" (RN-VEN-01).
- RF-VEN-24: SI el comprobante es `FACTURA` y el cliente no tiene RUC, ENTONCES EL SISTEMA rechaza la venta (RN-VEN-02).
- RF-VEN-25: SI el comprobante es `BOLETA`, el total supera el umbral vigente (S/ 700.00, configurable por la plataforma con fecha de vigencia) y el cliente es "Clientes varios", ENTONCES EL SISTEMA exige identificar al cliente (RN-VEN-03).
- RF-VEN-26: SI el stock disponible sin vencer en el almacén de la venta no alcanza, ENTONCES EL SISTEMA rechaza la venta indicando cuánto hay disponible, también si dos ventas toman el último stock a la vez (RN-VEN-05).
- RF-VEN-27: CUANDO la forma de pago es `CREDITO`, EL SISTEMA exige que el comprobante sea `FACTURA` y al menos una cuota (por defecto, una por el total) con monto y vencimiento. SI la suma de las cuotas no es igual al monto pendiente de pago (en el MVP, el total del comprobante, porque no hay detracciones ni retenciones) o algún vencimiento no es posterior a la emisión, ENTONCES rechaza la venta (RN-VEN-08).
- RF-VEN-28: SI en una línea pagada el ISC deja el valor de venta en 0 o menos, ENTONCES EL SISTEMA rechaza la línea. No aplica a las entregas gratuitas.
- RF-VEN-29: SI el mismo formulario de venta se envía dos veces, ENTONCES EL SISTEMA registra una sola venta.
- RF-VEN-30: CUANDO se registra una entrega gratuita (precio 0) con motivo, EL SISTEMA calcula ISC (litros × tarifa vigente) e IGV sobre el valor referencial, la informa como transferencia gratuita y el cliente paga 0 (épica 0007, RN-FAC-11). La línea gratuita puede ir sola o junto a líneas pagadas, en el comprobante que corresponda al cliente (factura si tiene RUC, boleta en otro caso).
  - *Ajuste pendiente por 0002e (borrador):* el motivo de la entrega gratuita se elige de una lista cerrada que define el código de afectación del comprobante: degustación o muestras (`14`), regalo vinculado a una venta (`15`), regalo a trabajadores (`16`) y retiro sin sustento (`13`); `21` si el producto es exonerado; si es inafecto (propuesta, a confirmar): degustación `36`, promoción `31`, trabajadores y retiro general `32`. El ISC se calcula con el impuesto ISC de venta del producto (0002e), ya no con litros × tarifa.
- RF-VEN-31: CUANDO se registra una venta, EL SISTEMA permite imprimir el comprobante en A4 o ticket de 80 mm.

## Requisitos no funcionales

- RNF-VEN-01: La caída del PSE o de SUNAT nunca impide registrar una venta (PRD §7).
- RNF-VEN-02: La pantalla de venta directa permite registrar una venta de 3 productos en menos de 1 minuto.

## Casos límite

- **Cambio de IGV o de tarifa de ISC entre el pedido y la venta:** el precio congelado del pedido (con impuestos) se mantiene; cambia el desglose (RF-VEN-22).
- **Entrega gratuita en resultados** (criterio del contador): no es venta ni costo de ventas; su costo y los impuestos asumidos van a gastos de venta (épica 0008). Ejemplo: 100 L con valor referencial 5.00/L y costo 3.00/L → ISC 251.00 + IGV 135.18 + costo 300.00 = 686.18.

## Fuera de alcance

Leads y oportunidades, cotizaciones formales, reserva de stock, entregas parciales, listas de precios por cliente, descuentos por volumen, cuentas por cobrar y cobranza, guía de remisión, POS offline, NC parciales.

## Criterios de finalización

- El costo de ventas de un período coincide con Σ salidas `VENTA` del kardex − entradas por anulación de venta.
- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **PRD Q3:** ¿el piloto vende en taproom (B2C)? De eso dependen la boleta a "Clientes varios", YAPE/PLIN y el ticket de 80 mm.
- [NECESITA ACLARACIÓN] **Contador:** códigos de las entregas gratuitas de productos inafectos (36, 31, 32; movida desde 0002e el 2026-10-11).
- [NECESITA ACLARACIÓN] **Contador:** vigencia del umbral de S/ 700.00 de la boleta y si se compara con el total con impuestos.
