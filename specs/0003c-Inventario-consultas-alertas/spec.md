# Spec 0003c — Inventario: stock, kardex y alertas

Estado: borrador

Épica E03 (Inventario), parte 3 de 3. Depende de: 0003a.

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

- H1: Como gerente, quiero ver el stock por almacén y lote con su costo y su valor para saber cuánto tengo invertido.
- H2: Como contador, quiero un kardex por producto que explique cada entrada y salida con su costo para cuadrar el inventario.
- H3: Como gerente, quiero que me avisen del stock bajo y de los lotes por vencer para reponer y vender a tiempo.

## Definiciones

- **Stock, movimiento, kardex, costo promedio y lote vencido:** ver spec 0003a.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-INV-02 Consultar stock

- RF-INV-04: CUANDO un usuario con `inventario.stock.ver` consulta el stock, EL SISTEMA muestra por producto el stock total, por almacén y por lote (con vencimiento), el costo promedio y el valor total, y la valorización total por tipo de producto.
- RF-INV-05: EL SISTEMA permite filtrar el stock por tipo, almacén, familia, solo stock bajo y solo con stock.

### UC-INV-03 Consultar kardex

- RF-INV-06: CUANDO un usuario con `inventario.kardex.ver` consulta el kardex de un producto, EL SISTEMA muestra cada movimiento con fecha, tipo, motivo, documento de origen (enlazado), almacén, lote, cantidad, costo unitario, costo total, saldo y promedio resultantes, y usuario.
- RF-INV-07: EL SISTEMA permite filtrar el kardex por producto, almacén, lote, motivo y rango de fechas, y exportarlo a CSV. Los saldos solo se muestran con un producto elegido.

### UC-INV-05 Alertar stock bajo mínimo

- RF-INV-14: MIENTRAS el stock total de un producto sea menor o igual a su stock mínimo, EL SISTEMA lo muestra en el aviso "Stock bajo" del dashboard y en el filtro del listado.

### UC-INV-06 Alertar lotes próximos a vencer

- RF-INV-15: MIENTRAS un lote con stock venza dentro de N días (30 por defecto, configurable por empresa), EL SISTEMA lo muestra en el aviso "Por vencer".
- RF-INV-16: EL SISTEMA marca en rojo los lotes vencidos.

## Requisitos no funcionales

- RNF-INV-02: El listado de stock y el kardex responden en menos de 800 ms (p95) con 100 000 movimientos por empresa (PRD §7).

## Casos límite

- Ver los de las otras partes de la épica.

## Fuera de alcance

Transferencias como documento con estados, lotes en insumos, ubicaciones o bins, conteo cíclico planificado, PEPS como método alternativo, integración con WMS o handhelds.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- Ninguna.
