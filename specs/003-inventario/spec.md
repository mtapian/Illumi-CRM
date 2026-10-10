# Spec 003 — Inventario

Estado: borrador

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
- H2: Como gerente, quiero ver el stock por almacén y lote con su costo y su valor para saber cuánto tengo invertido.
- H3: Como contador, quiero un kardex por producto que explique cada entrada y salida con su costo para cuadrar el inventario.
- H4: Como encargado de almacén, quiero registrar el saldo inicial, los conteos, las mermas, las correcciones y las transferencias para que el sistema refleje lo que hay físicamente.
- H5: Como gerente, quiero que me avisen del stock bajo y de los lotes por vencer para reponer y vender a tiempo.

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

| Tipo de ajuste | Efecto | Costo |
|---|---|---|
| `SALDO_INICIAL` | Entrada | Costo unitario obligatorio, mayor a 0 |
| `CONTEO` | Fija la cantidad contada; el sistema calcula la diferencia | Promedio vigente |
| `MERMA` | Salida (rotura, vencimiento, derrame, contaminación) | Promedio vigente |
| `CORRECCION` | Entrada o salida manual | Entrada: costo ingresado o promedio vigente · Salida: promedio vigente |
| `TRANSFERENCIA` | Salida del almacén origen + entrada en el destino (mismo producto, lote y cantidad) | La entrada usa el costo de la salida; el promedio no cambia; no afecta resultados |

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-INV-01 Gestionar almacenes

- RF-INV-01: CUANDO se registra una empresa, EL SISTEMA le crea el almacén "Principal".
- RF-INV-02: CUANDO un usuario con `inventario.almacen.gestionar` crea un almacén con un nombre que no existe en la empresa, EL SISTEMA lo guarda.
- RF-INV-03: SI se intenta desactivar un almacén con stock, ENTONCES EL SISTEMA lo rechaza.

### UC-INV-02 Consultar stock

- RF-INV-04: CUANDO un usuario con `inventario.stock.ver` consulta el stock, EL SISTEMA muestra por producto el stock total, por almacén y por lote (con vencimiento), el costo promedio y el valor total, y la valorización total por tipo de producto.
- RF-INV-05: EL SISTEMA permite filtrar el stock por tipo, almacén, familia, solo stock bajo y solo con stock.

### UC-INV-03 Consultar kardex

- RF-INV-06: CUANDO un usuario con `inventario.kardex.ver` consulta el kardex de un producto, EL SISTEMA muestra cada movimiento con fecha, tipo, motivo, documento de origen (enlazado), almacén, lote, cantidad, costo unitario, costo total, saldo y promedio resultantes, y usuario.
- RF-INV-07: EL SISTEMA permite filtrar el kardex por producto, almacén, lote, motivo y rango de fechas, y exportarlo a CSV. Los saldos solo se muestran con un producto elegido.

### UC-INV-04 Registrar ajuste de inventario

- RF-INV-08: CUANDO un usuario con `inventario.ajuste.registrar` registra un ajuste, EL SISTEMA exige un motivo, admite varias líneas y aplica el costo que corresponde a cada tipo de ajuste.
- RF-INV-09: SI un `SALDO_INICIAL` no tiene costo unitario mayor a 0, o el producto ya tiene movimientos, ENTONCES EL SISTEMA lo rechaza: el saldo inicial solo sirve para la apertura de cada producto (RN-INV-08).
- RF-INV-10: CUANDO un `SALDO_INICIAL` es de un producto con lote, EL SISTEMA crea el lote con el código y el vencimiento ingresados.
- RF-INV-11: CUANDO se registra un `CONTEO` igual al stock del sistema, EL SISTEMA guarda el ajuste con diferencia 0 como evidencia y no genera movimiento.
- RF-INV-12: CUANDO se registra una `TRANSFERENCIA`, EL SISTEMA registra la salida y la entrada juntas o ninguna, al mismo costo.
- RF-INV-13: CUANDO un usuario con `inventario.ajuste.anular` anula un ajuste, EL SISTEMA registra los movimientos inversos al costo original: en un `CONTEO` revierte la diferencia; en una `TRANSFERENCIA` revierte la salida y la entrada juntas. Si el stock no lo permite, lo rechaza.

### UC-INV-05 Alertar stock bajo mínimo

- RF-INV-14: MIENTRAS el stock total de un producto sea menor o igual a su stock mínimo, EL SISTEMA lo muestra en el aviso "Stock bajo" del dashboard y en el filtro del listado.

### UC-INV-06 Alertar lotes próximos a vencer

- RF-INV-15: MIENTRAS un lote con stock venza dentro de N días (30 por defecto, configurable por empresa), EL SISTEMA lo muestra en el aviso "Por vencer".
- RF-INV-16: EL SISTEMA marca en rojo los lotes vencidos.

### Reglas que aplican a todo movimiento (las usan compras, producción y ventas)

- RF-INV-17: CUANDO se registra cualquier entrada o salida, EL SISTEMA genera exactamente un movimiento con su costo y saldo, y ese movimiento no se puede modificar ni borrar (RN-INV-03, RN-GEN-03).
- RF-INV-18: CUANDO entra stock, EL SISTEMA recalcula el costo promedio según la fórmula de Definiciones (RN-INV-01).
- RF-INV-19: SI una salida dejaría stock negativo en el almacén y lote afectados, ENTONCES EL SISTEMA la rechaza con "Stock insuficiente", también cuando dos usuarios toman el último stock a la vez: solo uno tiene éxito (RN-INV-02, RN-GEN-02).
- RF-INV-20: CUANDO se revierte un movimiento por una anulación, EL SISTEMA usa el costo original del movimiento revertido y ajusta el valor total; un mismo movimiento no se revierte dos veces (RN-INV-04).
- RF-INV-21: SI se anula una entrada de un producto que tuvo salidas posteriores a esa entrada, en cualquier almacén o lote, ENTONCES EL SISTEMA rechaza la anulación e indica corregir con un ajuste `CORRECCION` (RN-INV-04).
- RF-INV-22: CUANDO una operación de un producto con lote no indica el lote y la operación lo permite, EL SISTEMA lo asigna por FEFO y puede repartir la cantidad entre varios lotes (RN-INV-05, RN-INV-06).
- RF-INV-23: SI se intenta sacar stock de un lote vencido por un motivo distinto de `MERMA` (venta, envasado, corrección), ENTONCES EL SISTEMA lo rechaza (RN-INV-07).
- RF-INV-24: CUANDO una salida deja el producto en cantidad 0, EL SISTEMA le asigna el valor restante, de modo que el valor total quede en 0.00.
- RF-INV-25: SI una entrada al promedio vigente (`CONTEO` con diferencia positiva o `CORRECCION` sin costo) es de un producto que nunca tuvo costo, ENTONCES EL SISTEMA exige ingresar el costo unitario.

## Requisitos no funcionales

- RNF-INV-01: El kardex de cualquier producto reproduce exactamente su stock y su valor actuales (prueba de reconciliación con secuencias aleatorias de operaciones).
- RNF-INV-02: El listado de stock y el kardex responden en menos de 800 ms (p95) con 100 000 movimientos por empresa (PRD §7).
- RNF-INV-03: Cantidades con 4 decimales, costos unitarios con 6 e importes con 2, con redondeo *half-up* (RN-GEN-09).

## Casos límite

- Dos usuarios consumen el último stock a la vez: uno tiene éxito y el otro recibe "Stock insuficiente".
- Una transferencia con el registro de origen y de destino en meses distintos no puede ocurrir: es un solo ajuste.
- Stock en cero: el valor queda en 0.00 y el promedio se conserva como referencia hasta la siguiente entrada.
- Un lote que vence hoy todavía se vende; mañana solo sale por merma.
- **Diferencias de conteo (métrica PRD §8):** el reporte de ajustes `CONTEO` del mes muestra la diferencia valorizada frente al valor del inventario, para medir la meta < 2 %.

## Fuera de alcance

Transferencias como documento con estados, lotes en insumos, ubicaciones o bins, conteo cíclico planificado, PEPS como método alternativo, integración con WMS o handhelds.

## Criterios de finalización

- Prueba de reconciliación en verde (RNF-INV-01).
- Escenarios `@critico` en verde.
- Cada RF-INV tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Contador (PRD Q12):** ¿se confirma que una compra ya consumida en parte no se anula y se corrige con un ajuste (RF-INV-21), o se prefiere revertir al promedio y llevar la diferencia a resultados?
- [NECESITA ACLARACIÓN] **Contador (PRD Q12):** sustento de mermas y desmedros para que sean deducibles (informe técnico, destrucción ante notario, aviso a SUNAT). Hoy solo se pide un motivo.
