# Spec 0003b — Inventario: ajustes

Estado: implementada (2026-10-10; aprobada por el PO con las tres decisiones de la propuesta): se alinea con 0003a implementada y con la enmienda 4 de 0002a (lote opcional en cualquier bien; RF-CAT-40)

Épica E03 (Inventario), parte 2 de 3. Depende de: 0003a.

## Contexto y objetivo

El inventario es la base del costo: si el stock o el costo están mal, la utilidad está mal. El sistema de referencia usa stock entero y un solo almacén, y sobrescribe el costo con el de la última compra.

**Objetivo:** que el stock por almacén y lote, y su valor, sean siempre exactos y se puedan explicar movimiento por movimiento.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Almacén | Consulta stock y kardex, registra ajustes y conteos |
| Gerente / Administrador | Además anula ajustes y gestiona almacenes |
| Producción, Ventas | Consultan stock (Ventas sin costos) |

## Historias de usuario

- H1: Como encargado de almacén, quiero registrar el saldo inicial, los conteos, las mermas, las correcciones y las transferencias para que el sistema refleje lo que hay físicamente.

## Definiciones

| Tipo de ajuste | Efecto | Costo |
|---|---|---|
| `SALDO_INICIAL` | Entrada | Costo unitario obligatorio, mayor a 0 |
| `CONTEO` | Fija la cantidad contada; el sistema calcula la diferencia | Promedio vigente |
| `MERMA` | Salida (rotura, vencimiento, derrame, contaminación) | Promedio vigente |
| `CORRECCION` | Entrada o salida manual | Entrada: costo ingresado o promedio vigente · Salida: promedio vigente |
| `TRANSFERENCIA` | Salida del almacén origen + entrada en el destino (mismo producto, lote y cantidad) | La entrada usa el costo de la salida; el costo total del producto no cambia (es por producto, no por almacén); no afecta resultados |

- **Stock, movimiento, costo promedio, lote, lote vencido y FEFO:** ver spec 0003a. El lote es opcional por línea en las entradas (RF-CAT-40); en las salidas, si no se indica, se asigna por FEFO (RF-INV-22).
- **Anulación:** los movimientos inversos llevan el motivo `ANULACION` (también en 0003a).

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-INV-04 Registrar ajuste de inventario

- RF-INV-08: CUANDO un usuario con `inventario.ajuste.registrar` registra un ajuste, EL SISTEMA exige un motivo, admite varias líneas y aplica el costo que corresponde a cada tipo de ajuste.
- RF-INV-09: SI un `SALDO_INICIAL` no tiene costo unitario mayor a 0, o el producto ya tiene movimientos, ENTONCES EL SISTEMA lo rechaza: el saldo inicial solo sirve para la apertura de cada producto (RN-INV-08).
- RF-INV-10: CUANDO una línea de entrada de un ajuste (`SALDO_INICIAL`, `CORRECCION` de entrada o `CONTEO` con diferencia positiva) trae un código de lote, EL SISTEMA crea el lote o usa el existente según RF-INV-26 (vencimiento opcional, sugerido por la vida útil). El lote es opcional.
- RF-INV-11: CUANDO se registra un `CONTEO` igual al stock del sistema, EL SISTEMA guarda el ajuste con diferencia 0 como evidencia y no genera movimiento.
- RF-INV-12: CUANDO se registra una `TRANSFERENCIA`, EL SISTEMA registra la salida y la entrada juntas o ninguna, al mismo costo y en el mismo lote; sin lote indicado, la salida se asigna por FEFO y el destino recibe los mismos lotes. El costo total y el promedio del producto no cambian.
- RF-INV-13: CUANDO un usuario con `inventario.ajuste.anular` anula un ajuste con un motivo, EL SISTEMA registra los movimientos inversos al costo original (RF-INV-20) y deja el ajuste `ANULADO`: en un `CONTEO` revierte la diferencia; en una `TRANSFERENCIA` revierte la salida y la entrada juntas, sin cambiar el costo del producto. SI el stock no lo permite o la entrada ya se consumió, ENTONCES EL SISTEMA lo rechaza (RF-INV-19, RF-INV-21). Un ajuste anulado no se vuelve a anular.
- RF-INV-28: EL SISTEMA numera los ajustes con un correlativo por empresa, sin huecos ni duplicados.
- RF-INV-29: SI una salida de `CONTEO` o `TRANSFERENCIA` es de un lote vencido, ENTONCES EL SISTEMA la permite (el conteo refleja lo que hay; la transferencia no consume). Un lote vencido sigue sin poder venderse ni consumirse (RF-INV-23). Ajusta RF-INV-23 de 0003a, que solo permitía `MERMA`.

- RF-INV-27: SI una entrada al promedio vigente (`CONTEO` con diferencia positiva o `CORRECCION` sin costo) es de un producto que nunca tuvo costo, ENTONCES EL SISTEMA exige ingresar el costo unitario. (Antes RF-INV-25: se renumera porque 0003a usó ese número.)

## Requisitos no funcionales

- Ninguno propio.

## Casos límite

- Una transferencia con el registro de origen y de destino en meses distintos no puede ocurrir: es un solo ajuste.
- Transferencia al mismo almacén: se rechaza.
- Un servicio no se ajusta (RF-INV-25).
- Ajuste de un producto con stock con lote y sin lote: cada línea indica su lote o "sin lote"; un `CONTEO` compara contra la existencia de esa línea.
- **Diferencias de conteo (métrica PRD §8):** el reporte de ajustes `CONTEO` del mes muestra la diferencia valorizada frente al valor del inventario, para medir la meta < 2 %.

## Fuera de alcance

Transferencias como documento con estados, ubicaciones o bins, conteo cíclico planificado, PEPS como método alternativo, integración con WMS o handhelds.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- **Decidido por el PO (2026-10-10; Q12, sustento de mermas):** en el MVP solo se exige el motivo; los adjuntos (informe técnico, acta de destrucción) quedan fuera de alcance hasta que responda el contador, y se agregan con una enmienda si los pide.
