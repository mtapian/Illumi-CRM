# Spec 0006b — Ventas: facturación, entrega y cobranza

Estado: **aprobada** (PO: "ok", 2026-10-13) · reescrita el 2026-10-13 con el modelo de venta del PO (pedido de venta y cobranza) y la constitución v1.2.0 (art. 10, ERP lite)

Épica E06 (Ventas y pedidos), parte 2 de 3. Depende de: 0006a (clientes y pedidos), 0002e (impuestos), 0003a (stock y lotes). La usan: 0006c (anulación), 0007a (emisión del comprobante), 0008b (resultados).

## Contexto y objetivo

La cervecera vende sobre todo a pedido (bares, restaurantes, distribuidores), con entrega y cobro posteriores, y en menor medida al público en mostrador, donde cobra en el acto. En los dos casos necesita descontar el stock del lote correcto, conocer el costo real de lo vendido, dejar listo el comprobante y saber qué le deben y quién.

**Objetivo:** que facturar un pedido descuente el stock con su costo congelado, deje el comprobante listo para emitir y genere una cobranza, y que cada cobranza muestre qué falta cobrar hasta quedar pagada.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Ventas, Gerente, Administrador | Facturan pedidos, confirman entregas, registran ventas directas, registran y anulan pagos |
| Administrador | Mantiene los métodos de pago de la empresa |
| Producción, Almacén | Consultan los pedidos facturados y entregados (lectura) |

## Historias de usuario

- H1: Como vendedor, quiero facturar un pedido aprobado para que salga el stock del lote correcto, quede el comprobante y se genere la cobranza.
- H2: Como vendedor, quiero confirmar la entrega de un pedido facturado.
- H3: Como vendedor de mostrador, quiero registrar una venta directa cobrada en el acto con uno o varios métodos de pago.
- H4: Como encargado de cobranzas, quiero ver lo que falta cobrar y registrar los pagos de cada cobranza hasta que quede pagada.
- H5: Como administrador, quiero mantener los métodos de pago que usa mi empresa.

## Definiciones

- **Venta:** un pedido facturado (0006a). No es un documento aparte.
- **Producto vendible, cliente genérico "Clientes varios", precio y estados del pedido:** ver 0006a.
- **Fecha de emisión:** el día en que se factura, en hora de Lima. No se factura con fecha pasada ni futura.
- **Desglose de una línea:** el precio de la línea incluye sus impuestos; el valor, el ISC y el IGV salen de los **impuestos de venta del producto** vigentes a la fecha de emisión (0002e, RF-CAT-59). Ejemplo: 24 unidades a 12.00 con "IGV 18%" → total 288.00 = valor 244.07 + IGV 43.93.
- **Comprobante pendiente:** el comprobante de la venta (factura o boleta) con su cliente, sus líneas y su desglose, listo para que la facturación electrónica (0007a) le asigne serie y correlativo y lo emita. En la prueba gratuita sin facturación es un comprobante interno (constitución, art. 5.2).
- **Forma de pago** (condición de pago; SUNAT la exige en toda factura al emitirla, PO 2026-10-13): **Contado** si el total se paga en la fecha de emisión; **Crédito** si se paga total o parcialmente después. Una factura a crédito declara el **monto neto pendiente de pago** y el **cronograma de cuotas** (monto y vencimiento de cada una), que la vuelven un título valor transable (factoring). Se registra en el pedido facturado y la informa el comprobante (0007a); **quien cobra es la cobranza**, no el comprobante (PO, 2026-10-13).
- **Monto neto pendiente de pago:** en el MVP, el total de la factura (sin detracciones, retenciones ni adelantos).
- **Cobranza:** con su **código** correlativo por empresa `COB-000001` (PO, 2026-10-13), lo que el cliente debe por un pedido facturado: total, cuotas (las de la factura a crédito; al contado, una sola por el total con vencimiento en la emisión), pagos y saldo. Los pagos se aplican al total, no a una cuota en particular. Estados **Pendiente ▸ Parcial ▸ Pagada** (Parcial: PO, 2026-10-13).
- **Monto vencido:** Σ cuotas con vencimiento anterior a hoy − Σ pagos vigentes (mínimo 0).
- **Saldo:** total de la cobranza − Σ pagos vigentes (no anulados).
- **Vencida:** una cobranza Pendiente o Parcial con monto vencido mayor a 0. Es un indicador, no un estado.
- **Método de pago:** un elemento del maestro de la empresa (p. ej. Efectivo, Yape, Plin, Tarjeta, Transferencia).

**Estados de la cobranza:**

| Desde | Hacia | Cuándo |
|---|---|---|
| — | Pendiente | Se factura el pedido (nada pagado) |
| Pendiente | Parcial | Un pago cubre parte del total (pagado > 0 y menor al total) |
| Pendiente, Parcial | Pagada | Sus pagos vigentes suman su total |
| Parcial, Pagada | Pendiente o Parcial | Se anula un pago: Pendiente si lo pagado vuelve a 0, Parcial si queda algo pagado |

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-VEN-05 Facturar y entregar un pedido

- RF-VEN-17: CUANDO un usuario con `ventas.venta.registrar` factura un pedido **Aprobado**, EL SISTEMA, en una sola operación: vuelve a validar el cliente, los productos y el stock (doble validación, constitución art. 10.3); saca el stock de cada línea; congela el costo; calcula el desglose de cada línea; crea el comprobante pendiente; crea la cobranza **Pendiente** por el total del pedido, con su código `COB-000001` (correlativo por empresa, sin huecos ni duplicados) y pasa el pedido a **Facturado**. Si algo falla, no hace nada de lo anterior.
- RF-VEN-19: CUANDO se factura, EL SISTEMA determina el comprobante por el cliente (RN-VEN-02; PO, 2026-10-13): **Factura si el cliente tiene RUC; Boleta en cualquier otro caso** (DNI, carné de extranjería, pasaporte o sin documento), y pide el almacén de salida (sugerido: el principal). **El tipo de documento del cliente define también la forma de pago posible** (PO, 2026-10-13): con RUC (Factura) el usuario elige Contado o Crédito (Contado por defecto); con cualquier otro documento (Boleta) es siempre Contado y la forma de pago no se ofrece. Con Crédito muestra el monto neto pendiente de pago y pide el cronograma de cuotas: cada cuota con su monto y su **plazo en días** desde la emisión, del que sale su vencimiento (ambos visibles; PO, 2026-10-13). Por defecto propone una cuota por el total a 30 días; el usuario cambia los días, el monto o agrega cuotas.
- RF-VEN-20: EL SISTEMA permite elegir el lote de cada línea de un bien al facturar. SI no se elige, ENTONCES saca según la estrategia de salida del producto (FEFO o FIFO; 0002a enmienda 6) y, después, el stock sin lote. Un servicio no saca stock.
- RF-VEN-21: CUANDO se saca el stock de una línea, EL SISTEMA guarda su costo (el promedio vigente en ese momento, por lote si sale de varios) y no lo recalcula aunque el costo promedio cambie después (RN-VEN-04; constitución art. 4.3).
- RF-VEN-22: EL SISTEMA calcula el desglose (valor, ISC, IGV) de cada línea con los impuestos de venta del producto vigentes a la fecha de emisión, sin cambiar el precio de la línea (RN-VEN-07). Si la línea sale de varios lotes, el comprobante sigue teniendo una sola línea.
- RF-VEN-38: EL SISTEMA usa como fecha de emisión el día en que se factura (hora de Lima).
- RF-VEN-23: SI alguna línea tiene un producto que ya no es vendible o está inactivo, ENTONCES EL SISTEMA no factura e indica "<SKU> ya no se vende" (RN-VEN-01).
- RF-VEN-24: EL SISTEMA no permite cambiar el comprobante que resulta del cliente: una factura siempre va a un cliente con RUC y una boleta nunca (RN-VEN-02). Para facturar a otro documento se cambia el cliente del pedido (mientras está Creado, 0006a).
- RF-VEN-25: SI el comprobante es Boleta, el total supera el umbral vigente de la plataforma (S/ 700.00) y el cliente es "Clientes varios", ENTONCES EL SISTEMA no factura e indica "Las boletas mayores a S/ 700.00 requieren identificar al cliente" (RN-VEN-03).
- RF-VEN-26: SI el stock sin vencer del almacén elegido (o del lote elegido) no alcanza para alguna línea, ENTONCES EL SISTEMA no factura e indica todos los faltantes ("Stock insuficiente: <SKU> faltan <n>; …"), también si dos usuarios facturan a la vez el último stock (RN-VEN-05). El pedido sigue Aprobado.
- RF-VEN-28: SI el ISC deja el valor de una línea en 0 o menos, ENTONCES EL SISTEMA no factura e indica la línea.
- RF-VEN-27: SI la forma de pago es Crédito y el cliente no tiene RUC (su comprobante no es Factura), no hay cuotas, alguna cuota no tiene monto mayor a 0, algún vencimiento no es posterior a la emisión o la suma de las cuotas no es igual al monto neto pendiente de pago, ENTONCES EL SISTEMA no factura (aunque la pantalla no ofrezca Crédito sin RUC, el servidor lo rechaza igual, art. 6.1) e indica, según el caso: "La venta a crédito requiere factura (cliente con RUC)", "Una venta a crédito requiere al menos una cuota", "Cada cuota debe tener un monto mayor a 0", "El vencimiento de cada cuota debe ser posterior a la emisión" o "La suma de las cuotas (<suma>) debe ser igual al monto pendiente (<total>)" (RN-VEN-08).
- RF-VEN-51: CUANDO un usuario con `ventas.venta.registrar` confirma la entrega de un pedido **Facturado**, EL SISTEMA lo pasa a **Entregado** y guarda quién y cuándo. La entrega no depende de la cobranza.
- RF-VEN-04 (completa 0006a): CUANDO se abre la ficha de un cliente, EL SISTEMA muestra además lo comprado en los últimos 90 días (Σ pedidos facturados), la fecha de su última compra y su saldo por cobrar.

### UC-VEN-07 Venta directa

- RF-VEN-18: CUANDO un usuario con `ventas.venta.registrar` registra una venta directa, EL SISTEMA propone el cliente "Clientes varios" (se puede buscar o registrar otro, RF-VEN-50), pide las líneas, el almacén y **uno o varios pagos** (método y monto), y en una sola operación crea el pedido, lo factura (RF-VEN-17 a 28), registra los pagos, deja la cobranza **Pagada** y el pedido **Entregado**.
- RF-VEN-52: SI los pagos de una venta directa no suman exactamente su total, ENTONCES EL SISTEMA no la registra e indica "Los pagos (<suma>) deben sumar el total (<total>)".
- RF-VEN-29: SI el mismo formulario de venta directa se envía dos veces, ENTONCES EL SISTEMA registra una sola venta.

### UC-VEN-09 Cobranzas y pagos

- RF-VEN-60 (PO, 2026-10-13): EL SISTEMA muestra la cobranza asociada a su pedido: la ficha del pedido facturado muestra su cobranza (código, estado, saldo y cuotas) con acceso a la ficha de la cobranza para registrar pagos, y la ficha de la cobranza muestra su código, su pedido (con enlace), cliente, cuotas y pagos.

- RF-VEN-53: EL SISTEMA lista las cobranzas (grilla estándar) con código, número de pedido (enlace a su pedido), cliente, forma de pago, emisión, próximo vencimiento (el de la primera cuota no cubierta por los pagos), total, pagado, saldo, monto vencido y estado, con el indicador **Vencida** y los filtros estado, cliente, fechas de vencimiento y "solo vencidas"; a quien tenga `ventas.cobranza.ver`.
- RF-VEN-54: CUANDO un usuario con `ventas.cobranza.gestionar` registra un pago en una cobranza Pendiente o Parcial (método activo, monto, fecha no futura ni anterior a la emisión de la cobranza y referencia opcional), EL SISTEMA lo guarda y pasa la cobranza a **Parcial** si aún queda saldo o a **Pagada** si el saldo llega a 0.
- RF-VEN-55: SI el monto del pago es 0 o menos, o mayor al saldo, ENTONCES EL SISTEMA lo rechaza e indica "El pago debe ser mayor a 0 y no superar el saldo (<saldo>)" (PO, 2026-10-13: nunca mayor al saldo; el vuelto se maneja fuera del sistema).
- RF-VEN-56: CUANDO un usuario con `ventas.cobranza.anular` (RF-VEN-61) anula un pago con motivo, EL SISTEMA lo marca anulado (no lo borra), guarda quién, cuándo y por qué, y recalcula el estado de la cobranza: **Pendiente** si lo pagado vuelve a 0, **Parcial** si queda algo pagado. Un pago anulado no se anula dos veces.
- RF-VEN-57: SI se intenta registrar un pago en una cobranza Pagada, ENTONCES EL SISTEMA lo rechaza e indica "La cobranza ya está pagada".

### UC-VEN-10 Métodos de pago

- RF-VEN-58: EL SISTEMA crea en cada empresa nueva, y en las existentes, los métodos de pago Efectivo, Yape, Plin, Tarjeta y Transferencia (constitución art. 10.4: lista del negocio, maestro de cada empresa).
- RF-VEN-59: CUANDO un usuario con `ventas.metodo_pago.gestionar` (RF-VEN-64) crea, renombra, activa o desactiva un método de pago, EL SISTEMA lo guarda; el nombre es único en la empresa sin distinguir mayúsculas. Un método no se elimina. Un método inactivo no se ofrece en pagos nuevos; los pagos que ya lo usan lo conservan.

### Enmienda 1 (PO, 2026-10-13): revisión de ventas — aprobada (PO: "ok a todo")

Tras la revisión de ventas el PO pidió segregar funciones en la cobranza (C1), un aviso de cobranzas vencidas en el inicio (U2) y el estado de cobro en los pedidos (U3). El plazo de crédito por cliente (U4) no se agrega: los días de cada cuota ya se editan al facturar (PO: "son editables").

- RF-VEN-61 (C1, segregación de funciones): EL SISTEMA exige el permiso `ventas.cobranza.anular`, distinto de `ventas.cobranza.gestionar`, para anular un pago. La plantilla de rol Gerente (y el Administrador) lo tienen; la de Ventas no: quien registra pagos no los anula. Ventas sigue registrando pagos (`ventas.cobranza.gestionar`); los roles son editables. Los roles existentes que ya anulan ventas (`ventas.venta.anular`) reciben `ventas.cobranza.anular` y `ventas.metodo_pago.gestionar`.
- RF-VEN-64 (Q3): EL SISTEMA exige `ventas.metodo_pago.gestionar` (Gerente y Administrador) para crear, renombrar, activar o desactivar métodos de pago (ajusta RF-VEN-59): el maestro lo administra quien administra, no quien opera.
- RF-VEN-62 (U2): MIENTRAS haya cobranzas vencidas (solo vencidas; sin aviso de próximas a vencer), EL SISTEMA muestra en el inicio, a quien tenga `ventas.cobranza.ver`, el aviso "N cobranzas vencidas", que lleva al listado de cobranzas filtrado por "solo vencidas". Sin cobranzas vencidas, no muestra el aviso.
- RF-VEN-63 (U3): EL SISTEMA muestra en la Lista y el Kanban de pedidos, para cada pedido Facturado o Entregado con saldo, su estado de cobro: **Por cobrar** (cobranza Pendiente) o **Cobro parcial** (Parcial), y además **Cobro vencido** si su cobranza está vencida. Un pedido pagado no lleva marca (las ventas directas no agregan ruido). Sin filtro nuevo: para eso está el listado de cobranzas.

## Requisitos no funcionales

- RNF-VEN-01: La caída del PSE o de SUNAT nunca impide facturar: el comprobante queda pendiente (constitución art. 5.2).
- RNF-VEN-02: Una venta directa de 3 productos con un pago se registra en menos de 1 minuto.

## Casos límite

- **Producto desactivado o stock consumido después de aprobar:** facturar lo detecta (doble validación) y el pedido sigue Aprobado hasta que el usuario lo corrija o lo cancele.
- **Venta a crédito e impuestos:** el IGV (y la renta) se devengan en la fecha de emisión, aunque el cliente aún no pague (PO, 2026-10-13). El desglose se calcula y queda fijo al facturar, y los reportes (0008b) toman la venta por su fecha de emisión, no por la de cobro.
- **Cambio de impuestos entre el pedido y la factura:** el precio del pedido se mantiene; cambia el desglose (RF-VEN-22).
- **Lote vencido elegido:** se rechaza como stock insuficiente (sin vencidos, 0003a).
- **Pedido con solo servicios:** se factura sin mover stock.
- **Dos pagos simultáneos por el último saldo:** solo uno entra; el otro se rechaza por superar el saldo.
- **Anular un pago de una venta directa:** la cobranza vuelve a Parcial o Pendiente; el pedido sigue Entregado.

## Fuera de alcance

- Asignar serie y correlativo, emitir a SUNAT e imprimir el comprobante (A4, ticket): 0007a.
- Anular una venta o corregir su cliente: 0006c.
- Entregas gratuitas (degustación, regalos, retiro de bienes): spec aparte, cuando responda el contador (PO, 2026-10-13).
- Leyenda "Venta al crédito" o cuotas informativas en la boleta.
- Aplicar un pago a una cuota en particular, adelantos en la emisión, vuelto, intereses, letras, factoring, detracciones y retenciones.
- Facturación o entrega parciales, reservas de stock, listas de precios por cliente, descuentos, POS sin conexión (constitución art. 10.1).

## Criterios de finalización

- Cada RF de esta spec tiene al menos un escenario o un test que lo cubre.
- Escenarios de `features/` en verde.
- El costo de ventas de un período coincide con Σ salidas `VENTA` del kardex.

## Retirados (2026-10-13)

RF-VEN-30 (entregas gratuitas) → spec aparte · RF-VEN-31 (impresión) → 0007a, RF-FAC-14 · numeración `V-000001` (la venta es el pedido `P-000001`; el comprobante lleva su serie y correlativo, 0007a) · métodos de pago fijos de RF-VEN-19 → maestro (RF-VEN-58, 59).

## Dudas abiertas

- ~~**Contador:** condición de pago de factura y boleta.~~ **Resuelto (PO, 2026-10-13):** la factura declara siempre la condición de pago y, a crédito, el monto neto pendiente y el cronograma de cuotas (RF-VEN-19, 27). La boleta es, para SUNAT, una operación al contado: se emite al contado aunque el cliente pague después; su cobranza puede quedar pendiente y recibir pagos posteriores, pero no lleva cuotas (RF-VEN-27). La leyenda "Venta al crédito" o las cuotas informativas en la boleta quedan fuera de alcance.
- [NECESITA ACLARACIÓN] **Contador:** vigencia del umbral de S/ 700.00 de la boleta y si se compara con el total con impuestos.
- [NECESITA ACLARACIÓN] **PRD Q3:** ¿el piloto vende en taproom (B2C)? La venta directa queda en el alcance igual; solo cambia su prioridad.
