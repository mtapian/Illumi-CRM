# Spec 0006a — Ventas: clientes y pedidos

Estado: borrador

Épica E06 (Ventas y pedidos), parte 1 de 3. Depende de: 0002a, 0003a. La usan: 0005a, 0005b, 0006b.

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

## Definiciones

- **Producto vendible:** `TERMINADO` (presentación propia) o `MERCADERIA` (reventa), activo.

- **Cliente genérico "Clientes varios":** cliente sin documento para ventas al público. Existe uno por empresa.

- **Precio de lista:** precio final con IGV e ISC.

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
- RF-VEN-09: CUANDO hay faltante de presentaciones propias, EL SISTEMA ofrece planificar producción con los litros sugeridos (épica 0005, RF-PRD-07).
- RF-VEN-10: CUANDO hay faltante de mercadería, EL SISTEMA lo muestra como "por comprar" y no ofrece producir.
- RF-VEN-11: SI se intenta cambiar precios o cantidades de un pedido confirmado, ENTONCES EL SISTEMA lo rechaza; para cambiarlos se cancela y se crea otro (RN-VEN-06).

### UC-VEN-04 Avanzar estado del pedido

- RF-VEN-12: CUANDO se inicia una OP vinculada, EL SISTEMA pasa el pedido a `EN_PRODUCCION`.
- RF-VEN-13: CUANDO se registra un envasado o se cierra una OP vinculada y el stock disponible cubre el pedido completo, EL SISTEMA pasa el pedido a `LISTO`. También se puede marcar `LISTO` manualmente si el stock alcanza.
- RF-VEN-14: CUANDO se registra la venta del pedido, EL SISTEMA lo pasa a `ENTREGADO`.
- RF-VEN-15: MIENTRAS la fecha comprometida de un pedido esté vencida y el pedido no esté `ENTREGADO` ni `CANCELADO`, EL SISTEMA lo marca como atrasado en el tablero.
- RF-VEN-16: SI se intenta una transición que no está en la tabla de transiciones del pedido, ENTONCES EL SISTEMA la rechaza.

### UC-VEN-07 Cancelar pedido

- RF-VEN-37: CUANDO un usuario con `ventas.pedido.cancelar` cancela con motivo un pedido en `BORRADOR`, `CONFIRMADO`, `EN_PRODUCCION` o `LISTO`, EL SISTEMA lo pasa a `CANCELADO`, desvincula sus OP sin anularlas y avisa al usuario.

### Reglas del pedido con varias OP

- RF-VEN-41: MIENTRAS un pedido esté `EN_PRODUCCION`, todas sus OP vinculadas estén cerradas o anuladas y el stock no cubra el pedido, EL SISTEMA lo devuelve a `CONFIRMADO` y muestra su faltante.
- RF-VEN-42: EL SISTEMA permite vincular un pedido a varias OP y una OP a varios pedidos. Los eventos de producción no cambian el estado de los pedidos `ENTREGADO` o `CANCELADO`.

## Requisitos no funcionales

- Ninguno propio.

## Casos límite

- **Sin reserva de stock:** dos pedidos confirmados pueden competir por el mismo stock; la venta valida el stock al confirmarse y el tablero muestra el faltante en tiempo real.
- **Pedido que se vuelve imposible** (su stock se vendió a otro): vuelve a mostrar faltante y se puede planificar otra OP.

## Fuera de alcance

Leads y oportunidades, cotizaciones formales, reserva de stock, entregas parciales, listas de precios por cliente, descuentos por volumen, cuentas por cobrar y cobranza, guía de remisión, POS offline, NC parciales.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] Wireframe del tablero de pedidos.
