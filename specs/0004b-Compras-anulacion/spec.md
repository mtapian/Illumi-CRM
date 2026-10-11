# Spec 0004b — Compras: anulación

Estado: implementada (aprobada por el PO el 2026-10-11)

Épica E04 (Compras), parte 2 de 2. Depende de: 0004a, 0003a.

## Contexto y objetivo

Una compra mal registrada (otro proveedor, otro precio, un documento equivocado) no se edita una vez finalizada: el kardex no se reescribe (constitución, art. 4.5). Se anula y se registra de nuevo.

**Objetivo:** anular una compra sin descuadrar el inventario: si ya entró stock, se revierte una sola vez al mismo costo; si ese stock ya se consumió, se corrige con un ajuste.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Gerente / Administrador | Anulan compras (`compras.compra.anular`) |
| Almacén | Registra compras, pero no las anula |

## Historias de usuario

- H1: Como gerente, quiero anular una compra mal registrada sin descuadrar el inventario.

## Definiciones

- **Compra activa:** compra no anulada, en cualquier estado (Creada, En proceso o Finalizada).
- **Estados de la compra:** ver 0004a (Creada ▸ En proceso ▸ Finalizada). Anulada queda fuera de la barra y es definitiva.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-COM-03 Anular compra

- RF-COM-15: CUANDO un usuario con `compras.compra.anular` anula una compra **Finalizada** con motivo, EL SISTEMA revierte sus entradas al mismo costo con que entraron (movimientos `ANULACION` que referencian la compra), recalcula el costo promedio y deja la compra **Anulada** con usuario, fecha y motivo, en una sola operación (épica 0003, RF-INV-20).
- RF-COM-28: CUANDO un usuario con `compras.compra.anular` anula una compra **Creada o En proceso** con motivo, EL SISTEMA la deja Anulada con usuario, fecha y motivo, sin movimientos de inventario (no entró stock).
- RF-COM-16: SI algún producto de una compra Finalizada tuvo salidas posteriores a su entrada, ENTONCES EL SISTEMA rechaza la anulación con "No se puede anular: <SKU> tuvo salidas posteriores a la compra. Corrígela con un ajuste CORRECCION" y no cambia nada (Q12 = A; constitución, art. 4.5; RF-INV-21).
- RF-COM-17: SI dos usuarios anulan la misma compra a la vez, ENTONCES EL SISTEMA la anula una sola vez y al otro le responde "La compra ya está anulada".
- RF-COM-18: CUANDO una compra se anula, EL SISTEMA permite registrar de nuevo su documento de proveedor (RF-COM-11 solo cuenta compras activas).
- RF-COM-29: SI la anulación no trae motivo, ENTONCES EL SISTEMA la rechaza con "El motivo es obligatorio". Una compra Anulada no se edita, no cambia de estado ni se anula otra vez.

## Requisitos no funcionales

- Ninguno propio.

## Casos límite

- Una compra con dos líneas del mismo producto: se revierten las dos entradas; el costo vuelve al valor previo a la compra si no hubo otros movimientos.
- Otra compra del mismo producto, posterior y aún no consumida, no impide anular la primera: solo cuentan las salidas (RF-INV-21).
- Si la anulación se rechaza por consumo, la compra sigue Finalizada y su stock intacto.
- El lote creado por la compra queda registrado aunque su stock vuelva a 0 (el lote es historia del ingreso).

## Fuera de alcance

Anulación parcial (de algunas líneas), nota de crédito del proveedor, devolución física al proveedor como documento propio, cuentas por pagar.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- Q12 (anulación de una compra consumida): el PO eligió la opción A (se corrige por ajuste); falta el visto bueno del contador.
