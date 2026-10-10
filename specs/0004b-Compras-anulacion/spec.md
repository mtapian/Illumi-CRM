# Spec 0004b — Compras: anulación

Estado: borrador

Épica E04 (Compras), parte 2 de 2. Depende de: 0004a, 0003a.

## Contexto y objetivo

El costo de producción nace en la compra de insumos y envases, y el costo de la mercadería de reventa nace en su compra. El sistema de referencia sobrescribe el precio de compra del producto y no distingue el IGV recuperable.

**Objetivo:** que cada compra sume stock al costo real sin IGV recuperable y que se pueda anular sin descuadrar el inventario.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Almacén | Gestiona proveedores y registra compras |
| Gerente / Administrador | Además anula compras |

## Historias de usuario

- H1: Como gerente, quiero anular una compra mal registrada sin descuadrar el inventario.

## Definiciones

- **Compra activa:** compra en estado `REGISTRADA` (no anulada).

- **Documento del proveedor y costo de la línea:** ver spec 0004a.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-COM-03 Anular compra

- RF-COM-15: CUANDO un usuario con `compras.compra.anular` anula una compra con motivo, EL SISTEMA revierte sus entradas al mismo costo, recalcula el costo promedio y deja la compra `ANULADA` con usuario, fecha y motivo (épica 0003, RF-INV-20).
- RF-COM-16: SI algún producto de la compra tuvo salidas posteriores a la compra, ENTONCES EL SISTEMA rechaza la anulación, indica el producto y propone corregir con un ajuste (épica 0003, RF-INV-21).
- RF-COM-17: SI dos usuarios anulan la misma compra a la vez, ENTONCES EL SISTEMA anula una sola vez y al otro le responde "La compra ya está anulada".
- RF-COM-18: CUANDO una compra se anula, EL SISTEMA permite registrar de nuevo su documento de proveedor.

## Requisitos no funcionales

- Ninguno propio.

## Casos límite

- Ver los de las otras partes de la épica.

## Fuera de alcance

Órdenes de compra, recepción parcial, cuentas por pagar, prorrateo de flete o importación en el costo, compras en dólares, conversión de unidad de compra.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- Ninguna.
