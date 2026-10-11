# Spec 0004a — Compras: proveedores y registro de compras

Estado: implementada (aprobada por el PO el 2026-10-11). Se alinea con 0002d, 0003a–c y con la enmienda 4 de 0002a (casilla "Se compra", lote opcional)

Épica E04 (Compras), parte 1 de 2. Depende de: 0002a, **0002d (proveedores)**, 0003a. La usan: 0004b.

*(2026-10-10)* El maestro de proveedores (UC-COM-01, RF-COM-01 a 03) se movió a la spec **0002d** por decisión del PO; aquí quedan las compras.

## Contexto y objetivo

El costo de producción nace en la compra de insumos y envases, y el costo de la mercadería de reventa nace en su compra. El sistema de referencia sobrescribe el precio de compra del producto y no distingue el IGV recuperable.

**Objetivo:** que cada compra sume stock al costo real sin IGV recuperable y que se pueda anular sin descuadrar el inventario.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Almacén | Gestiona proveedores y registra compras |
| Gerente / Administrador | Además anula compras |

## Historias de usuario

- H2: Como encargado de almacén, quiero registrar la compra de los bienes que compro (insumos, envases, mercadería, cerveza de terceros) con su documento, para que el stock y el costo se actualicen solos.

## Definiciones

- **Documento del proveedor:** `FACTURA`, `BOLETA`, `NOTA_VENTA` (RUS) o `SIN_DOCUMENTO`, con su serie y número.

- **Costo unitario de la línea:** con `FACTURA`, es el valor sin IGV (el IGV es crédito fiscal). Con cualquier otro documento, es el precio total pagado por unidad, porque no hay IGV recuperable.

- **Bonificación:** unidades que el proveedor entrega sin costo. Es el único caso en que una línea tiene costo 0.

- **Estados de la compra** (PO, 2026-10-11; mismos estados que la orden de producción, 0005a): **Creada** ▸ **En proceso** ▸ **Finalizada**, y **Anulada** fuera de la barra. Creada: se está armando. En proceso: pedida al proveedor, a la espera de la entrega. Finalizada: recibida; recién aquí entra el stock. Mientras no está finalizada, la compra se edita y no toca el inventario.
- **Compra activa:** compra no anulada.
- **Bien comprable:** bien activo con la casilla "Se compra" (RF-CAT-38, 39). Un servicio no se registra como compra: va a gastos (0008a).
- **IGV de la compra:** el % de IGV vigente de la empresa a la fecha de la compra. Cuando se apruebe 0002e, saldrá de los impuestos de compra de cada producto.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-COM-01 Gestionar proveedores

Movido a la spec 0002d (RF-COM-01 a 03).

### UC-COM-02 Registrar compra

- RF-COM-04: CUANDO un usuario con `compras.compra.registrar` crea una compra con proveedor, fecha, almacén de destino, documento, observación y al menos una línea (producto, cantidad > 0 y costo unitario > 0, o costo 0 si la línea se marca como bonificación), EL SISTEMA la guarda en estado **Creada** con numeración correlativa `C-000001` por empresa, sin mover stock.
- RF-COM-25: MIENTRAS la compra está Creada o En proceso, EL SISTEMA permite editar su cabecera y sus líneas (agregar, quitar y cambiar) y pasarla de Creada a En proceso; ningún cambio mueve stock. Una compra no vuelve a un estado anterior.
- RF-COM-26: CUANDO un usuario con `compras.compra.registrar` **finaliza** la compra, EL SISTEMA vuelve a validar la compra completa (RF-COM-05, 11, 20, 23, 27) y, si es válida, la deja **Finalizada** y registra el ingreso de stock (RF-COM-10) en la misma operación; si no es válida, no cambia nada.
- RF-COM-05: SI una línea tiene un producto que no es un bien comprable (Definiciones), ENTONCES EL SISTEMA rechaza la compra con "Solo se pueden comprar bienes activos que se compran" (RN-COM-01).
- RF-COM-06: CUANDO una línea trae un código de lote, EL SISTEMA lo registra con el vencimiento indicado, que es opcional; si no se indica y el producto tiene vida útil, sugiere la fecha de recepción + vida útil (RF-CAT-40, RF-INV-26). El lote es opcional en cada línea.
- RF-COM-07: CUANDO una línea trae un código de lote que ya existe para ese producto con el mismo vencimiento, EL SISTEMA suma la cantidad a ese lote; si el código no existe, lo crea con el vencimiento indicado.
- RF-COM-19: SI una línea trae un código de lote que ya existe para ese producto con otro vencimiento, ENTONCES EL SISTEMA la rechaza.
- RF-COM-08: CUANDO el documento es `FACTURA`, EL SISTEMA calcula el IGV con el % de la empresa y deja el costo de inventario sin IGV. Con cualquier otro documento, el IGV es 0 y el costo de inventario es el total pagado.
- RF-COM-20: SI el documento es `FACTURA` y el proveedor no tiene RUC, ENTONCES EL SISTEMA rechaza la compra.
- RF-COM-09: EL SISTEMA calcula el total = subtotal + IGV, con redondeo *half-up* a 2 decimales por línea y en el total (RN-COM-05).
- RF-COM-10: CUANDO se finaliza la compra, EL SISTEMA registra una entrada de inventario por línea al costo indicado y recalcula el costo promedio (épica 0003, RN-INV-01). Una compra Creada o En proceso no tiene movimientos.
- RF-COM-11: SI el mismo documento de proveedor (proveedor + tipo + serie-número) ya existe en una compra activa, ENTONCES EL SISTEMA rechaza la compra (RN-COM-02). No aplica a `SIN_DOCUMENTO`.
- RF-COM-12: EL SISTEMA trata la fecha de la compra como referencia (fecha del documento o de la entrega esperada): acepta fechas pasadas o futuras en cualquier estado y no bloquea la finalización por esa fecha (PO, 2026-10-11).
- RF-COM-27: CUANDO un usuario confirma la recepción (finaliza la compra), EL SISTEMA pide: el **almacén de ingreso** (sugerido: el de la compra, editable; solo almacenes activos), la **fecha de recepción** (sugerida: hoy) y, opcionalmente, la **guía de remisión** del proveedor (serie-número). Guarda los tres en la compra; el stock entra a ese almacén y la fecha de recepción es la de los movimientos de kardex y del ingreso de los lotes. SI la fecha de recepción es posterior a hoy (hora de Lima), ENTONCES EL SISTEMA no finaliza ("La fecha de recepción no puede ser futura"). SI la guía no tiene el formato serie-número (4 caracteres, guion y hasta 8 dígitos), ENTONCES EL SISTEMA no finaliza ("Guía de remisión inválida"). La guía no se valida contra SUNAT ni como única (una guía puede cubrir varias compras). El orden del kardex y el costo promedio siguen el orden en que se finaliza (no se recalculan hacia atrás).
- RF-COM-13: EL SISTEMA no permite editar una compra Finalizada; para corregirla se anula (0004b) y se registra otra (RN-COM-03).
- RF-COM-14: CUANDO un usuario con `compras.compra.ver` consulta las compras, EL SISTEMA permite filtrar por proveedor, fecha, estado y número, y desde el detalle enlaza a sus movimientos de kardex. El kardex enlaza cada entrada `COMPRA` a su compra.
- RF-COM-23: SI el proveedor está desactivado, ENTONCES EL SISTEMA rechaza la compra con "El proveedor está desactivado" (RF-COM-03).
- RF-COM-24: CUANDO un proveedor tiene una compra no anulada (en cualquier estado), EL SISTEMA considera que tiene compras: ya no se puede eliminar, solo desactivar (RF-COM-02 de 0002d).

## Requisitos no funcionales

- RNF-COM-01: Registrar una compra de 10 líneas toma menos de 2 minutos de captura para un usuario entrenado.

## Casos límite

- Una compra con 2 líneas del mismo producto: se permite y genera dos movimientos; el promedio resultante es el mismo que con una línea combinada.
- Una compra recibida días atrás se finaliza con esa fecha de recepción: el kardex la muestra con esa fecha, pero en el orden en que se finalizó; el costo promedio no se recalcula hacia atrás (constitución, art. 4.3).
- Una compra Creada o En proceso con un producto que después se desactiva o deja de comprarse: se puede editar para quitarlo; no se finaliza mientras lo tenga.
- Anular una compra Creada o En proceso no mueve stock (0004b).
- El IGV que calcula el sistema puede diferir en céntimos del que figura en la factura del proveedor.

## Fuera de alcance

Órdenes de compra, recepción parcial, cuentas por pagar, prorrateo de flete o importación en el costo, compras en dólares, conversión de unidad de compra, compra de servicios (van a gastos, 0008a), sugerir el precio referencial del proveedor del producto.

## Criterios de finalización

- El costo promedio de los insumos del piloto coincide con su cálculo manual en 3 compras de prueba.
- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- Resuelto (PO, 2026-10-11): la fecha del kardex de una compra es la **fecha de recepción**, que se pide al finalizar (RF-COM-27). Falta el visto bueno del contador (PRD Q12).
- **Decidido por el PO (2026-10-11; IGV de la factura del proveedor):** en el MVP el IGV lo calcula el sistema (por línea, half-up); una diferencia de céntimos con la factura no se corrige. Ingresar el IGV del documento queda para una enmienda si el contador lo pide.
- **Resuelto por la enmienda 4 de 0002a (maquila / compra de granel):** cualquier bien se puede comprar si tiene la casilla "Se compra", incluida la cerveza a granel o terminada de otra cervecería. Sigue abierta, para el contador, si la reventa de cerveza de terceros paga ISC otra vez.
