# Spec 0003c — Inventario: stock, kardex y alertas

Estado: implementada (2026-10-10; aprobada por el PO): se alinea con 0003a y 0003b implementadas y con las enmiendas 4 y 5 de 0002a (bien o servicio, casillas, categorías)

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

- **Stock, movimiento, kardex, costo promedio y lote vencido:** ver spec 0003a. Solo los bienes llevan stock (RF-CAT-37).
- **Stock bajo:** stock total del producto (todos los almacenes y lotes) menor o igual a su stock mínimo, solo en productos con stock mínimo mayor a 0.
- **Por vencer:** lote con stock cuyo vencimiento cae entre hoy y hoy + N días, ambos inclusive; N = 30 por defecto, configurable por empresa.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-INV-02 Consultar stock

- RF-INV-04: CUANDO un usuario con `inventario.stock.ver` consulta el stock, EL SISTEMA muestra por producto el stock total, el detalle por almacén y por lote (con vencimiento; el stock sin lote aparte), el costo promedio y el valor total, y la valorización total por categoría ("Sin categoría" aparte) y general. MIENTRAS el usuario no tenga `inventario.costo.ver`, EL SISTEMA oculta costo y valor (RF-TEN-51).
- RF-INV-05: EL SISTEMA permite buscar por SKU o nombre y filtrar el stock por casilla (se compra, se fabrica, se vende), almacén, categoría, solo stock bajo y solo con stock.

### UC-INV-03 Consultar kardex

- RF-INV-06: CUANDO un usuario con `inventario.kardex.ver` consulta el kardex de un producto, EL SISTEMA muestra cada movimiento con fecha, tipo, motivo, documento de origen (enlazado cuando su pantalla existe: hoy, los ajustes), almacén, lote, cantidad, costo unitario, costo total, saldo y promedio resultantes, y usuario. Sin `inventario.costo.ver`, sin costos ni promedio (RF-TEN-51).
- RF-INV-07: EL SISTEMA permite filtrar el kardex por producto, almacén, lote, motivo y rango de fechas (hora de Lima), y exportarlo a CSV con los mismos filtros y la misma regla de costos. Los saldos solo se muestran con un producto elegido, porque son del producto.

### UC-INV-05 Alertar stock bajo mínimo

- RF-INV-14: MIENTRAS un producto esté en stock bajo (Definiciones), EL SISTEMA lo muestra en el aviso "Stock bajo" del dashboard (stock y mínimo) y en el filtro "stock bajo" del listado de stock y del de productos (0002a, RF-CAT-14, que pasa de "menor que" a "menor o igual que").

### UC-INV-06 Alertar lotes próximos a vencer

- RF-INV-15: MIENTRAS un lote con stock esté por vencer (Definiciones), EL SISTEMA lo muestra en el aviso "Por vencer" del dashboard con los días que le quedan; los lotes vencidos con stock aparecen en el mismo aviso como "Vencido". CUANDO un usuario con `inventario.almacen.gestionar` cambia N (entero de 1 a 365), EL SISTEMA lo guarda para su empresa.
- RF-INV-16: EL SISTEMA marca en rojo los lotes vencidos en el stock, el kardex y el aviso.
- RF-INV-30: MIENTRAS un usuario no tenga `inventario.stock.ver`, EL SISTEMA no le muestra los avisos de inventario del dashboard.

## Requisitos no funcionales

- RNF-INV-02: El listado de stock y el kardex responden en menos de 800 ms (p95) con 100 000 movimientos por empresa (PRD §7).

## Casos límite

- Ver los de las otras partes de la épica.
- Producto con stock mínimo 0: nunca aparece en "Stock bajo".
- Lote sin vencimiento o sin stock: nunca aparece en "Por vencer".
- Kardex sin producto elegido: lista movimientos de todos los productos, sin saldos.

## Fuera de alcance

Transferencias como documento con estados, ubicaciones o bins, conteo cíclico planificado, PEPS como método alternativo, integración con WMS o handhelds, avisos por correo o notificaciones (los avisos son solo del dashboard), stock a una fecha pasada.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- Ninguna.
