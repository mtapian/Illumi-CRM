# Spec 0003b — Inventario: ajustes

Estado: borrador

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
| `TRANSFERENCIA` | Salida del almacén origen + entrada en el destino (mismo producto, lote y cantidad) | La entrada usa el costo de la salida; el promedio no cambia; no afecta resultados |

- **Stock, movimiento, costo promedio, lote vencido y FEFO:** ver spec 0003a.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-INV-04 Registrar ajuste de inventario

- RF-INV-08: CUANDO un usuario con `inventario.ajuste.registrar` registra un ajuste, EL SISTEMA exige un motivo, admite varias líneas y aplica el costo que corresponde a cada tipo de ajuste.
- RF-INV-09: SI un `SALDO_INICIAL` no tiene costo unitario mayor a 0, o el producto ya tiene movimientos, ENTONCES EL SISTEMA lo rechaza: el saldo inicial solo sirve para la apertura de cada producto (RN-INV-08).
- RF-INV-10: CUANDO un `SALDO_INICIAL` es de un producto con lote, EL SISTEMA crea el lote con el código y el vencimiento ingresados.
- RF-INV-11: CUANDO se registra un `CONTEO` igual al stock del sistema, EL SISTEMA guarda el ajuste con diferencia 0 como evidencia y no genera movimiento.
- RF-INV-12: CUANDO se registra una `TRANSFERENCIA`, EL SISTEMA registra la salida y la entrada juntas o ninguna, al mismo costo.
- RF-INV-13: CUANDO un usuario con `inventario.ajuste.anular` anula un ajuste, EL SISTEMA registra los movimientos inversos al costo original: en un `CONTEO` revierte la diferencia; en una `TRANSFERENCIA` revierte la salida y la entrada juntas. Si el stock no lo permite, lo rechaza.

- RF-INV-25: SI una entrada al promedio vigente (`CONTEO` con diferencia positiva o `CORRECCION` sin costo) es de un producto que nunca tuvo costo, ENTONCES EL SISTEMA exige ingresar el costo unitario.

## Requisitos no funcionales

- Ninguno propio.

## Casos límite

- Una transferencia con el registro de origen y de destino en meses distintos no puede ocurrir: es un solo ajuste.
- **Diferencias de conteo (métrica PRD §8):** el reporte de ajustes `CONTEO` del mes muestra la diferencia valorizada frente al valor del inventario, para medir la meta < 2 %.

## Fuera de alcance

Transferencias como documento con estados, lotes en insumos, ubicaciones o bins, conteo cíclico planificado, PEPS como método alternativo, integración con WMS o handhelds.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Contador (PRD Q12):** sustento de mermas y desmedros para que sean deducibles (informe técnico, destrucción ante notario, aviso a SUNAT). Hoy solo se pide un motivo.
