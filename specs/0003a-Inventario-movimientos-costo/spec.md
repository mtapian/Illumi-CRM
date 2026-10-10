# Spec 0003a — Inventario: almacenes, movimientos y costo promedio

Estado: borrador

Épica E03 (Inventario), parte 1 de 3. Depende de: 0001a, 0002a. La usan: 0003b, 0003c, 0004, 0005, 0006.

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

- H1: Como encargado de almacén, quiero tener varios almacenes (Principal, Cámara fría, Taproom) para saber dónde está cada cosa.

## Definiciones

- **Stock:** cantidad por producto × almacén × lote. El lote aplica a `GRANEL`, `TERMINADO` y a la `MERCADERIA` que controla lote.

- **Movimiento:** registro de cada entrada o salida, con su costo y el saldo resultante. El conjunto de movimientos de un producto es su **kardex**.

- **Costo promedio ponderado:** por producto (todos los almacenes y lotes), sin IGV. El sistema guarda por producto la **cantidad total** y el **valor total**; el promedio es `valor / cantidad`.

```
Entrada:              valor += cant × costo_entrada ;  cantidad += cant
Salida al promedio:   valor −= cant × promedio      ;  cantidad −= cant   (el promedio no cambia)
Reversión de entrada: valor −= cant × costo_original;  cantidad −= cant   (el promedio SÍ cambia)
Salida que deja cantidad = 0: sale por el valor restante (sin residuo de redondeo)
Si cantidad = 0, se conserva el último promedio como referencia
```

Ejemplo (malta, en KG):

| Operación | Cantidad | Costo unit. | Saldo | Promedio | Costo del movimiento |
|---|---:|---:|---:|---:|---:|
| Saldo inicial | +100 | 4.000000 | 100 | 4.000000 | 400.00 |
| Compra | +50 | 5.000000 | 150 | 4.333333 | 250.00 |
| Consumo OP | −30 | 4.333333 | 120 | 4.333333 | 130.00 |
| Merma | −20 | 4.333333 | 100 | 4.333333 | 86.67 |

Reversión de una entrada: anular la compra de 50 KG a 5.00 con saldo de 150 KG por 650.00 → sale a 5.000000 → queda 100 KG por 400.00 → promedio **4.000000**.

- **Lote vencido:** lote cuya fecha de vencimiento es anterior a hoy (hora de Lima). El día del vencimiento todavía se puede vender.

- **FEFO** (*first expired, first out*): primero sale el lote no vencido que vence antes; a igual vencimiento, el más antiguo. Los lotes sin fecha de vencimiento salen al final, del más antiguo al más nuevo.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-INV-01 Gestionar almacenes

- RF-INV-01: CUANDO se registra una empresa, EL SISTEMA le crea el almacén "Principal".
- RF-INV-02: CUANDO un usuario con `inventario.almacen.gestionar` crea un almacén con un nombre que no existe en la empresa, EL SISTEMA lo guarda.
- RF-INV-03: SI se intenta desactivar un almacén con stock, ENTONCES EL SISTEMA lo rechaza.

### Reglas que aplican a todo movimiento (las usan compras, producción y ventas)

- RF-INV-17: CUANDO se registra cualquier entrada o salida, EL SISTEMA genera exactamente un movimiento con su costo y saldo, y ese movimiento no se puede modificar ni borrar (RN-INV-03, RN-GEN-03).
- RF-INV-18: CUANDO entra stock, EL SISTEMA recalcula el costo promedio según la fórmula de Definiciones (RN-INV-01).
- RF-INV-19: SI una salida dejaría stock negativo en el almacén y lote afectados, ENTONCES EL SISTEMA la rechaza con "Stock insuficiente", también cuando dos usuarios toman el último stock a la vez: solo uno tiene éxito (RN-INV-02, RN-GEN-02).
- RF-INV-20: CUANDO se revierte un movimiento por una anulación, EL SISTEMA usa el costo original del movimiento revertido y ajusta el valor total; un mismo movimiento no se revierte dos veces (RN-INV-04).
- RF-INV-21: SI se anula una entrada de un producto que tuvo salidas posteriores a esa entrada, en cualquier almacén o lote, ENTONCES EL SISTEMA rechaza la anulación e indica corregir con un ajuste `CORRECCION` (RN-INV-04).
- RF-INV-22: CUANDO una operación de un producto con lote no indica el lote y la operación lo permite, EL SISTEMA lo asigna por FEFO y puede repartir la cantidad entre varios lotes (RN-INV-05, RN-INV-06).
- RF-INV-23: SI se intenta sacar stock de un lote vencido por un motivo distinto de `MERMA` (venta, envasado, corrección), ENTONCES EL SISTEMA lo rechaza (RN-INV-07).
- RF-INV-24: CUANDO una salida deja el producto en cantidad 0, EL SISTEMA le asigna el valor restante, de modo que el valor total quede en 0.00.

## Requisitos no funcionales

- RNF-INV-01: El kardex de cualquier producto reproduce exactamente su stock y su valor actuales (prueba de reconciliación con secuencias aleatorias de operaciones).
- RNF-INV-03: Cantidades con 4 decimales, costos unitarios con 6 e importes con 2, con redondeo *half-up* (RN-GEN-09).

## Casos límite

- Dos usuarios consumen el último stock a la vez: uno tiene éxito y el otro recibe "Stock insuficiente".
- Stock en cero: el valor queda en 0.00 y el promedio se conserva como referencia hasta la siguiente entrada.
- Un lote que vence hoy todavía se vende; mañana solo sale por merma.

## Fuera de alcance

Transferencias como documento con estados, lotes en insumos, ubicaciones o bins, conteo cíclico planificado, PEPS como método alternativo, integración con WMS o handhelds.

## Criterios de finalización

- Prueba de reconciliación en verde (RNF-INV-01).
- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Contador (PRD Q12):** ¿se confirma que una compra ya consumida en parte no se anula y se corrige con un ajuste (RF-INV-21), o se prefiere revertir al promedio y llevar la diferencia a resultados?
