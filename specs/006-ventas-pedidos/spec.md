# Spec 006 — Ventas y pedidos (CRM mínimo)

Estado: borrador

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

- H1: Como vendedor, quiero registrar a mis clientes con su documento validado para facturarles sin errores.
- H2: Como vendedor, quiero crear un pedido con fecha de entrega y saber al confirmarlo qué falta producir o comprar.
- H3: Como vendedor, quiero ver el tablero de pedidos por estado con los atrasos para cumplir lo comprometido.
- H4: Como vendedor, quiero registrar una venta (desde un pedido o directa en mostrador) que descuente el lote correcto y emita su comprobante.
- H5: Como vendedor, quiero vender a crédito en cuotas a clientes con RUC.
- H6: Como gerente, quiero anular una venta con el motivo SUNAT correcto y decidir si la mercadería vuelve al almacén.
- H7: Como vendedor, quiero registrar degustaciones y regalos como entregas gratuitas, con sus impuestos correctos.

## Definiciones

- **Producto vendible:** `TERMINADO` (presentación propia) o `MERCADERIA` (reventa), activo.
- **Cliente genérico "Clientes varios":** cliente sin documento para ventas al público. Existe uno por empresa.
- **Línea comercial:** producto + precio dentro de una venta. Los impuestos se calculan por línea comercial, aunque FEFO la reparta entre varios lotes.
- **Precio de lista:** precio final con IGV e ISC.
- **Valor referencial:** valor de mercado sin impuestos de una entrega gratuita (por defecto se deriva del precio de lista; editable).

**Estados del pedido** (`BORRADOR`, `CONFIRMADO`, `EN_PRODUCCION`, `LISTO`, `ENTREGADO`, `CANCELADO`). Solo valen estas transiciones:

| Desde | Hacia | Cuándo |
|---|---|---|
| `BORRADOR` | `CONFIRMADO` | El usuario confirma el pedido |
| `CONFIRMADO` | `EN_PRODUCCION` | Se inicia una OP vinculada |
| `CONFIRMADO`, `EN_PRODUCCION` | `LISTO` | El stock disponible cubre el pedido completo (tras un envasado, un cierre de OP o manualmente) |
| `EN_PRODUCCION` | `CONFIRMADO` | Se anulan o cierran todas sus OP vinculadas sin que el stock cubra el pedido |
| `CONFIRMADO`, `EN_PRODUCCION`, `LISTO` | `ENTREGADO` | Se registra la venta del pedido |
| `ENTREGADO` | `LISTO` | Se anula la venta y la mercadería vuelve al almacén |
| `ENTREGADO` | `CONFIRMADO` | Se anula la venta y la mercadería no vuelve al almacén |
| `BORRADOR`, `CONFIRMADO`, `EN_PRODUCCION`, `LISTO` | `CANCELADO` | El usuario cancela el pedido |

`LISTO` indica que el stock cubría el pedido al marcarlo; como no hay reserva, la venta vuelve a validar el stock.

**Desglose de impuestos por línea comercial** (precio de lista con impuestos incluidos):
- Sin ISC: `valor = round(total / (1 + IGV%), 2)`; `IGV = total − valor`.
- Con ISC (producto con categoría de ISC de Sistema Específico, spec 002): `ISC = round(cantidad × contenido_L × tarifa vigente, 2)`; `valor = round(total / (1 + IGV%) − ISC, 2)`; `IGV = total − valor − ISC`. Base del IGV = valor + ISC.
- Ejemplo: 24 botellas de 330 ml a 12.00 sin ISC → valor 244.07 + IGV 43.93 = 288.00. Con ISC de S/ 2.51/L → 7.92 L, ISC 19.88, valor 224.19, IGV 43.93, total 288.00.

**Motivos de nota de crédito (catálogo 09 de SUNAT) usados en el MVP:** `01` Anulación de la operación y `06` Devolución total, al anular una venta (UC-VEN-06); `02` Anulación por error en el RUC, al corregir el cliente de una venta (UC-VEN-08).

**Fecha de emisión de una venta:** la fecha de registro de la venta, en hora de Lima. No se registran ventas con fecha pasada ni futura.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-VEN-01 Gestionar clientes

- RF-VEN-01: CUANDO un usuario con `ventas.cliente.gestionar` registra un cliente con tipo de documento (`DNI`, `RUC`, `CE`, `SIN_DOC`), número, nombre o razón social, contacto, canal (`B2B`/`B2C`) y notas, EL SISTEMA lo guarda si el documento es válido y no existe en la empresa.
- RF-VEN-02: SI el DNI no tiene 8 dígitos, el RUC no pasa el dígito verificador o el CE tiene más de 12 caracteres alfanuméricos, ENTONCES EL SISTEMA rechaza el cliente e indica el motivo.
- RF-VEN-03: CUANDO se registra una empresa, EL SISTEMA le crea el cliente genérico "Clientes varios".
- RF-VEN-04: CUANDO se abre la ficha de un cliente, EL SISTEMA muestra sus pedidos, sus ventas, el total comprado en los últimos 90 días y la fecha de su última compra.
- RF-VEN-05: SI se intenta eliminar un cliente con documentos, ENTONCES EL SISTEMA lo rechaza y ofrece desactivarlo.

### UC-VEN-02 Crear pedido

- RF-VEN-06: CUANDO un usuario con `ventas.pedido.gestionar` crea un pedido con cliente, fecha de entrega comprometida, líneas (producto vendible, cantidad, precio precargado con el de lista) y notas, EL SISTEMA lo guarda como `BORRADOR`.
- RF-VEN-07: MIENTRAS el pedido esté en `BORRADOR`, EL SISTEMA permite editarlo libremente.

### UC-VEN-03 Confirmar pedido

- RF-VEN-08: CUANDO se confirma un pedido con al menos una línea, EL SISTEMA lo pasa a `CONFIRMADO`, congela precios y cantidades, y muestra por línea el stock disponible sin vencer (sumando todos los almacenes) y el faltante.
- RF-VEN-09: CUANDO hay faltante de presentaciones propias, EL SISTEMA ofrece planificar producción con los litros sugeridos (spec 005, RF-PRD-07).
- RF-VEN-10: CUANDO hay faltante de mercadería, EL SISTEMA lo muestra como "por comprar" y no ofrece producir.
- RF-VEN-11: SI se intenta cambiar precios o cantidades de un pedido confirmado, ENTONCES EL SISTEMA lo rechaza; para cambiarlos se cancela y se crea otro (RN-VEN-06).

### UC-VEN-04 Avanzar estado del pedido

- RF-VEN-12: CUANDO se inicia una OP vinculada, EL SISTEMA pasa el pedido a `EN_PRODUCCION`.
- RF-VEN-13: CUANDO se registra un envasado o se cierra una OP vinculada y el stock disponible cubre el pedido completo, EL SISTEMA pasa el pedido a `LISTO`. También se puede marcar `LISTO` manualmente si el stock alcanza.
- RF-VEN-14: CUANDO se registra la venta del pedido, EL SISTEMA lo pasa a `ENTREGADO`.
- RF-VEN-15: MIENTRAS la fecha comprometida de un pedido esté vencida y el pedido no esté `ENTREGADO` ni `CANCELADO`, EL SISTEMA lo marca como atrasado en el tablero.
- RF-VEN-16: SI se intenta una transición que no está en la tabla de transiciones del pedido, ENTONCES EL SISTEMA la rechaza.

### UC-VEN-05 Registrar venta

- RF-VEN-17: CUANDO un usuario con `ventas.venta.registrar` registra una venta desde un pedido `CONFIRMADO`, `EN_PRODUCCION` o `LISTO`, EL SISTEMA precarga el cliente, las líneas y los precios, y entrega el pedido completo.
- RF-VEN-18: CUANDO se registra una venta directa, EL SISTEMA propone el cliente "Clientes varios" y permite buscar productos vendibles (presentaciones y mercadería, mezclados).
- RF-VEN-19: CUANDO se registra una venta, EL SISTEMA pide tipo de comprobante (`FACTURA`/`BOLETA`), almacén y forma de pago (`CONTADO` o `CREDITO`). Solo en ventas al contado pide además el método de pago (`EFECTIVO`, `TARJETA`, `TRANSFERENCIA`, `YAPE`, `PLIN`) y, si es efectivo, el monto recibido, y calcula el vuelto.
- RF-VEN-20: CUANDO un producto de la venta tiene lote y el usuario no elige uno, EL SISTEMA asigna los lotes por FEFO (spec 003). La mercadería sin lote sale solo por almacén.
- RF-VEN-21: CUANDO se confirma la venta, EL SISTEMA saca el stock, **congela el costo** de cada línea, la numera `V-000001` por empresa y emite su comprobante electrónico (spec 007). Un cambio posterior del costo promedio no altera el costo de la venta (RN-VEN-04).
- RF-VEN-38: EL SISTEMA usa como fecha de emisión de la venta la fecha en que se registra (hora de Lima); no permite registrar ventas con fecha pasada ni futura.
- RF-VEN-22: EL SISTEMA calcula los impuestos por línea comercial según el desglose de Definiciones, con el IGV y la tarifa de ISC vigentes a la fecha de emisión. Si FEFO reparte una línea entre lotes, el comprobante sigue teniendo una sola línea. En una venta desde pedido se mantiene el precio congelado (con impuestos) y se recalcula su desglose (RN-VEN-07).
- RF-VEN-23: SI se intenta vender un producto que no es vendible o está inactivo, ENTONCES EL SISTEMA lo rechaza con "Solo se pueden vender presentaciones y mercadería activas" (RN-VEN-01).
- RF-VEN-24: SI el comprobante es `FACTURA` y el cliente no tiene RUC, ENTONCES EL SISTEMA rechaza la venta (RN-VEN-02).
- RF-VEN-25: SI el comprobante es `BOLETA`, el total supera el umbral vigente (S/ 700.00, configurable por la plataforma con fecha de vigencia) y el cliente es "Clientes varios", ENTONCES EL SISTEMA exige identificar al cliente (RN-VEN-03).
- RF-VEN-26: SI el stock disponible sin vencer en el almacén de la venta no alcanza, ENTONCES EL SISTEMA rechaza la venta indicando cuánto hay disponible, también si dos ventas toman el último stock a la vez (RN-VEN-05).
- RF-VEN-27: CUANDO la forma de pago es `CREDITO`, EL SISTEMA exige que el comprobante sea `FACTURA` y al menos una cuota (por defecto, una por el total) con monto y vencimiento. SI la suma de las cuotas no es igual al monto pendiente de pago (en el MVP, el total del comprobante, porque no hay detracciones ni retenciones) o algún vencimiento no es posterior a la emisión, ENTONCES rechaza la venta (RN-VEN-08).
- RF-VEN-28: SI en una línea pagada el ISC deja el valor de venta en 0 o menos, ENTONCES EL SISTEMA rechaza la línea. No aplica a las entregas gratuitas.
- RF-VEN-29: SI el mismo formulario de venta se envía dos veces, ENTONCES EL SISTEMA registra una sola venta.
- RF-VEN-30: CUANDO se registra una entrega gratuita (precio 0) con motivo, EL SISTEMA calcula ISC (litros × tarifa vigente) e IGV sobre el valor referencial, la informa como transferencia gratuita y el cliente paga 0 (spec 007, RN-FAC-11). La línea gratuita puede ir sola o junto a líneas pagadas, en el comprobante que corresponda al cliente (factura si tiene RUC, boleta en otro caso).
- RF-VEN-31: CUANDO se registra una venta, EL SISTEMA permite imprimir el comprobante en A4 o ticket de 80 mm.

### UC-VEN-06 Anular venta

- RF-VEN-32: CUANDO un usuario con `ventas.venta.anular` anula una venta con el motivo `01` o `06`, EL SISTEMA la pasa a `ANULADA` de inmediato, sin esperar a SUNAT, y registra su nota de crédito en la misma operación (RN-VEN-09). *Regla pendiente de validación del contador (constitución, art. 5.5).*
- RF-VEN-33: CUANDO se anula una venta, EL SISTEMA pregunta si la mercadería vuelve al almacén (por defecto sí); si vuelve, la reingresa a los mismos lotes y al costo original.
- RF-VEN-34: CUANDO la mercadería de una venta anulada no vuelve al almacén, EL SISTEMA mantiene su costo de ventas.
- RF-VEN-35: CUANDO se anula una venta que venía de un pedido, EL SISTEMA devuelve el pedido a `LISTO` si la mercadería volvió al almacén, o a `CONFIRMADO` si no volvió.
- RF-VEN-36: SI dos usuarios anulan la misma venta a la vez, ENTONCES EL SISTEMA la anula una sola vez.

### UC-VEN-07 Cancelar pedido

- RF-VEN-37: CUANDO un usuario con `ventas.pedido.cancelar` cancela con motivo un pedido en `BORRADOR`, `CONFIRMADO`, `EN_PRODUCCION` o `LISTO`, EL SISTEMA lo pasa a `CANCELADO`, desvincula sus OP sin anularlas y avisa al usuario.

### UC-VEN-08 Corregir el cliente de una venta

- RF-VEN-39: CUANDO un usuario con `ventas.venta.anular` corrige el cliente de una venta cuyo comprobante fue aceptado (p. ej. por un RUC errado), EL SISTEMA emite una nota de crédito con motivo `02` sobre el comprobante original y un comprobante nuevo para el cliente correcto, con las mismas líneas e importes. La venta sigue `EMITIDA`, sin movimiento de stock y sin cambio en su costo.
- RF-VEN-40: SI el comprobante original todavía no fue aceptado, ENTONCES EL SISTEMA rechaza la corrección hasta que lo sea.

### Reglas del pedido con varias OP

- RF-VEN-41: MIENTRAS un pedido esté `EN_PRODUCCION`, todas sus OP vinculadas estén cerradas o anuladas y el stock no cubra el pedido, EL SISTEMA lo devuelve a `CONFIRMADO` y muestra su faltante.
- RF-VEN-42: EL SISTEMA permite vincular un pedido a varias OP y una OP a varios pedidos. Los eventos de producción no cambian el estado de los pedidos `ENTREGADO` o `CANCELADO`.

## Requisitos no funcionales

- RNF-VEN-01: La caída del PSE o de SUNAT nunca impide registrar una venta (PRD §7).
- RNF-VEN-02: La pantalla de venta directa permite registrar una venta de 3 productos en menos de 1 minuto.

## Casos límite

- **Devolución parcial** (p. ej. 2 de 24 botellas): las NC parciales están fuera del MVP. Se anula la venta completa con reingreso y se registra una venta nueva por lo que el cliente se queda.
- **Cambio de IGV o de tarifa de ISC entre el pedido y la venta:** el precio congelado del pedido (con impuestos) se mantiene; cambia el desglose (RF-VEN-22).
- **Sin reserva de stock:** dos pedidos confirmados pueden competir por el mismo stock; la venta valida el stock al confirmarse y el tablero muestra el faltante en tiempo real.
- **Pedido que se vuelve imposible** (su stock se vendió a otro): vuelve a mostrar faltante y se puede planificar otra OP.
- **Entrega gratuita en resultados** (criterio del contador): no es venta ni costo de ventas; su costo y los impuestos asumidos van a gastos de venta (spec 008). Ejemplo: 100 L con valor referencial 5.00/L y costo 3.00/L → ISC 251.00 + IGV 135.18 + costo 300.00 = 686.18.
- Una venta anulada cuyo comprobante aún no fue aceptado: la venta queda anulada y la NC espera (spec 007).

## Fuera de alcance

Leads y oportunidades, cotizaciones formales, reserva de stock, entregas parciales, listas de precios por cliente, descuentos por volumen, cuentas por cobrar y cobranza, guía de remisión, POS offline, NC parciales.

## Criterios de finalización

- El costo de ventas de un período coincide con Σ salidas `VENTA` del kardex − entradas por anulación de venta.
- Escenarios `@critico` en verde.
- Cada RF-VEN tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **PRD Q3:** ¿el piloto vende en taproom (B2C)? De eso dependen la boleta a "Clientes varios", YAPE/PLIN y el ticket de 80 mm.
- [NECESITA ACLARACIÓN] **PO y contador:** confirmar que la venta se anula de inmediato y la NC espera a que se acepte el comprobante original (RF-VEN-32).
- [NECESITA ACLARACIÓN] **Contador:** vigencia del umbral de S/ 700.00 de la boleta y si se compara con el total con impuestos.
- [NECESITA ACLARACIÓN] Wireframe del tablero de pedidos.
