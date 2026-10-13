# Spec 0008c — Reportes: dashboard, exportación e indicadores de los listados

Estado: **aprobada** (PO: "ok", 2026-10-13; decisiones Q1–Q7)

Épica E08 (Finanzas y reportes), parte 3. Se separa de 0008b (PO, 2026-10-13) el dashboard (UC-FIN-04) y la exportación (UC-FIN-05), que no dependen de gastos ni del contador; 0008b se queda con el estado de resultados. Depende de: 0002a, 0003c, 0006a, 0006b.

## Contexto y objetivo

El dueño quiere ver de un vistazo cómo van las ventas y qué requiere atención, y llevar los listados a Excel para trabajarlos o enviarlos al contador.

**Objetivo:** un inicio con las cifras del día y del mes, sus tendencias y los avisos, siguiendo las imágenes de referencia del PO; exportar a XLSX y CSV las grillas de productos, kardex, pedidos y cobranzas; y ver en los listados de pedidos y cobranzas cuántos hay en cada estado.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Todos los roles | Ven el dashboard, con lo que su permiso habilita |
| Quien tenga `reportes.exportar` | Exporta las grillas que puede ver |
| Ventas, Gerente, Administrador | Ven los indicadores por estado de pedidos y cobranzas |

## Historias de usuario

- H1: Como dueño, quiero ver al entrar las ventas de hoy y del mes, su tendencia, cómo me pagan y qué se vende más.
- H2: Como usuario, quiero que el inicio me avise lo que requiere atención según mi rol.
- H3: Como contador o gerente, quiero exportar a Excel las grillas con los filtros que apliqué.
- H4: Como vendedor, quiero ver cuántos pedidos y cobranzas hay en cada estado y filtrarlos con un clic.

## Definiciones

- **Venta (para el dashboard):** un pedido Facturado o Entregado, ubicado por su **fecha de emisión** (0006b). Los cancelados no cuentan; cuando exista la anulación (0006c), una venta anulada deja de contar. **Importe: el total con impuestos** (lo que paga el cliente; PO, Q1), rotulado "con impuestos". El valor sin impuestos es del estado de resultados (0008b).
- **Cobrado:** Σ pagos vigentes (no anulados) por la **fecha del pago** (0006b).
- **Mes:** el mes calendario en curso, en hora de Lima (art. 7.5).

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-FIN-04 Dashboard

- RF-FIN-14 (reescrito): CUANDO un usuario abre el inicio, EL SISTEMA muestra, cada una solo con su permiso, las tarjetas **Ventas de hoy** y **Ventas del mes** (`ventas.venta.ver`), **Productos activos** (`catalogo.producto.ver`) y **Clientes activos** (`ventas.cliente.ver`), con la fecha de hoy en las migas.
- RF-FIN-17: EL SISTEMA reúne bajo las tarjetas los avisos que ya existen, cada uno con su permiso y un "Ver detalle" que lleva al listado filtrado: productos con stock bajo o agotado y lotes por vencer (`inventario.stock.ver`), pedidos con quiebre de stock (`ventas.pedido.ver`) y cobranzas vencidas (`ventas.cobranza.ver`). Sin nada que avisar, no muestra la barra.
- RF-FIN-18: EL SISTEMA muestra el gráfico **Ventas de los últimos 14 días** (un punto por día, incluidos los días sin ventas en 0) con `ventas.venta.ver`.
- RF-FIN-19: EL SISTEMA muestra el gráfico **Ventas por mes** del año en curso (12 meses, enero a diciembre) con `ventas.venta.ver`.
- RF-FIN-20: EL SISTEMA muestra el gráfico **Cobrado por método de pago** del mes (dona con monto y porcentaje por método; PO, Q3) con `ventas.cobranza.ver`.
- RF-FIN-21: EL SISTEMA muestra el gráfico **Ventas por categoría** del mes (barras horizontales, de mayor a menor, con "Sin categoría" para los productos sin ella) con `ventas.venta.ver`.
- RF-FIN-22: EL SISTEMA muestra **Productos más vendidos** del mes: los 5 de mayor total, con producto, unidades y total, con `ventas.venta.ver`.
- RF-FIN-23: EL SISTEMA muestra **Últimas ventas**: las 6 más recientes por fecha y hora de facturación, con número de pedido (enlace), cliente, total y estado, con `ventas.venta.ver`.
- RF-FIN-24: EL SISTEMA dibuja los gráficos en el servidor (SVG, sin dependencias externas; PO, Q5) con sus valores visibles en etiquetas; sin datos, muestra los ejes en 0 o "Aún no hay ventas", nunca un error.

### UC-FIN-05 Exportar grillas

- RF-FIN-15 (reescrito): CUANDO un usuario con `reportes.exportar` y permiso para ver la grilla exporta **productos** (catálogo), **kardex**, **pedidos** o **cobranzas**, EL SISTEMA genera un archivo **XLSX** o **CSV** (UTF-8 con BOM, separador coma, punto decimal; PO, Q6) con las mismas columnas de la grilla y los filtros aplicados. Los pedidos van **una fila por línea (SKU)**, con los datos del pedido repetidos en cada fila.
- RF-FIN-16 (se mantiene): MIENTRAS el usuario no tenga `inventario.costo.ver`, EL SISTEMA omite los costos y la valorización en las exportaciones (RF-TEN-51).
- RF-FIN-25: SI la exportación supera las 50 000 filas, ENTONCES EL SISTEMA no la genera e indica "Hay más de 50 000 filas: agrega filtros para exportar".

### UC-FIN-06 Indicadores por estado en los listados

- RF-FIN-26: EL SISTEMA muestra sobre el listado de pedidos una tarjeta por estado (**Creados, Aprobados, Facturados, Entregados**) con su cantidad, y sobre el de cobranzas (**Pendientes, Parciales, Pagadas, Vencidas**) con su cantidad y su saldo; los conteos respetan los filtros aplicados salvo el de estado, y al pulsar una tarjeta se filtra por ese estado (como la bandeja de comprobantes de referencia).

## Requisitos no funcionales

- RNF-FIN-04: El inicio responde en menos de 800 ms (p95) con el volumen del PRD §7: cada cifra sale de una consulta agregada en la base, nunca de recorrer las ventas en Python.
- RNF-FIN-05: Una exportación de 50 000 filas se genera en menos de 10 s, por streaming, sin cargar todo en memoria.

## Casos límite

- Venta del 30 a las 23:30 (hora de Lima): cuenta en ese día y ese mes.
- Un pago anulado deja de contar como cobrado.
- Un producto sin categoría cuenta en "Sin categoría".
- Usuario sin `ventas.venta.ver`: no ve tarjetas ni gráficos de ventas, solo lo que su permiso habilita.
- Exportar sin `inventario.costo.ver`: sin las columnas de costo.

## Fuera de alcance

Estado de resultados y utilidad (0008b), comparar períodos en el dashboard, elegir el período del dashboard, gráficos interactivos, exportar a PDF, programar envíos por correo, otras grillas (se agregan con la misma pieza cuando se pidan).

## Criterios de finalización

- Cada RF con un escenario o un test.
- Revisión visual del PO contra sus imágenes de referencia.

## Dudas abiertas

- Ninguna: Q1–Q7 respondidas por el PO el 2026-10-13.
