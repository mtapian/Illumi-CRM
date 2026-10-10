# Spec 0004a — Compras: proveedores y registro de compras

Estado: borrador

Épica E04 (Compras), parte 1 de 2. Depende de: 0002a, 0003a. La usan: 0004b.

## Contexto y objetivo

El costo de producción nace en la compra de insumos y envases, y el costo de la mercadería de reventa nace en su compra. El sistema de referencia sobrescribe el precio de compra del producto y no distingue el IGV recuperable.

**Objetivo:** que cada compra sume stock al costo real sin IGV recuperable y que se pueda anular sin descuadrar el inventario.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Almacén | Gestiona proveedores y registra compras |
| Gerente / Administrador | Además anula compras |

## Historias de usuario

- H1: Como encargado de almacén, quiero registrar a mis proveedores para asociarles las compras.
- H2: Como encargado de almacén, quiero registrar la compra de insumos, envases y mercadería con su documento, para que el stock y el costo se actualicen solos.

## Definiciones

- **Documento del proveedor:** `FACTURA`, `BOLETA`, `NOTA_VENTA` (RUS) o `SIN_DOCUMENTO`, con su serie y número.

- **Costo unitario de la línea:** con `FACTURA`, es el valor sin IGV (el IGV es crédito fiscal). Con cualquier otro documento, es el precio total pagado por unidad, porque no hay IGV recuperable.

- **Bonificación:** unidades que el proveedor entrega sin costo. Es el único caso en que una línea tiene costo 0.

- **Compra activa:** compra en estado `REGISTRADA` (no anulada).

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-COM-01 Gestionar proveedores

- RF-COM-01: CUANDO un usuario con `compras.proveedor.gestionar` registra un proveedor con tipo y número de documento (RUC o DNI), razón social y datos de contacto, EL SISTEMA lo guarda si el documento es válido y no existe en la empresa.
- RF-COM-02: SI se intenta eliminar un proveedor con compras, ENTONCES EL SISTEMA lo rechaza y ofrece desactivarlo.
- RF-COM-03: MIENTRAS un proveedor esté desactivado, EL SISTEMA no lo ofrece en compras nuevas.

### UC-COM-02 Registrar compra

- RF-COM-04: CUANDO un usuario con `compras.compra.registrar` registra una compra con proveedor, fecha, almacén de destino, documento, observación y al menos una línea (producto, cantidad > 0 y costo unitario > 0, o costo 0 si la línea se marca como bonificación), EL SISTEMA la guarda como `REGISTRADA` con numeración correlativa `C-000001` por empresa.
- RF-COM-05: SI una línea tiene un producto que no es `INSUMO`, `ENVASE` ni `MERCADERIA` activo, ENTONCES EL SISTEMA rechaza la compra con "Solo se pueden comprar insumos, envases y mercadería" (RN-COM-01).
- RF-COM-06: SI una línea es de un producto que controla lote y no trae código de lote y vencimiento, ENTONCES EL SISTEMA la rechaza. El vencimiento sugerido es la fecha de compra + vida útil (RN-COM-01).
- RF-COM-07: CUANDO una línea trae un código de lote que ya existe para ese producto con el mismo vencimiento, EL SISTEMA suma la cantidad a ese lote; si el código no existe, lo crea con el vencimiento indicado.
- RF-COM-19: SI una línea trae un código de lote que ya existe para ese producto con otro vencimiento, ENTONCES EL SISTEMA la rechaza.
- RF-COM-08: CUANDO el documento es `FACTURA`, EL SISTEMA calcula el IGV con el % de la empresa y deja el costo de inventario sin IGV. Con cualquier otro documento, el IGV es 0 y el costo de inventario es el total pagado.
- RF-COM-20: SI el documento es `FACTURA` y el proveedor no tiene RUC, ENTONCES EL SISTEMA rechaza la compra.
- RF-COM-09: EL SISTEMA calcula el total = subtotal + IGV, con redondeo *half-up* a 2 decimales por línea y en el total (RN-COM-05).
- RF-COM-10: CUANDO se guarda la compra, EL SISTEMA registra una entrada de inventario por línea al costo indicado y recalcula el costo promedio (épica 0003, RN-INV-01).
- RF-COM-11: SI el mismo documento de proveedor (proveedor + tipo + serie-número) ya existe en una compra activa, ENTONCES EL SISTEMA rechaza la compra (RN-COM-02). No aplica a `SIN_DOCUMENTO`.
- RF-COM-12: SI la fecha de la compra es posterior a hoy (hora de Lima), ENTONCES EL SISTEMA la rechaza (RN-COM-04).
- RF-COM-13: EL SISTEMA no permite editar una compra registrada; para corregirla se anula y se registra otra (RN-COM-03).
- RF-COM-14: CUANDO un usuario con `compras.compra.ver` consulta las compras, EL SISTEMA permite filtrar por proveedor, fecha, estado y número, y desde el detalle enlaza a sus movimientos de kardex.

## Requisitos no funcionales

- RNF-COM-01: Registrar una compra de 10 líneas toma menos de 2 minutos de captura para un usuario entrenado.

## Casos límite

- Una compra con 2 líneas del mismo producto: se permite y genera dos movimientos; el promedio resultante es el mismo que con una línea combinada.
- Una compra con fecha pasada se registra con esa fecha, pero el movimiento de kardex toma la fecha y hora reales de registro (el kardex no se reordena).
- El IGV que calcula el sistema puede diferir en céntimos del que figura en la factura del proveedor.

## Fuera de alcance

Órdenes de compra, recepción parcial, cuentas por pagar, prorrateo de flete o importación en el costo, compras en dólares, conversión de unidad de compra.

## Criterios de finalización

- El costo promedio de los insumos del piloto coincide con su cálculo manual en 3 compras de prueba.
- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Contador (PRD Q12):** fecha del kardex en compras con fecha pasada: ¿fecha del documento o fecha de registro? Hoy, la de registro.
- [NECESITA ACLARACIÓN] **IGV de la factura del proveedor:** ¿se permite ingresar el IGV del documento (con tolerancia de ±0.01 por línea), como ya se hace en gastos, para que cuadre con el registro de compras?
- [NECESITA ACLARACIÓN] **Maquila / compra de granel:** si el piloto compra cerveza a granel o terminada a otra cervecería, habría que permitir comprar `GRANEL` y `TERMINADO` (ver épica 0002).
