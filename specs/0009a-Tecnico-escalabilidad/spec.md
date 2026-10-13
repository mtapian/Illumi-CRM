# Spec 0009a — Técnico: escalabilidad y deuda técnica

Estado: **sin refinar** (backlog técnico; PO, 2026-10-13: "déjalo como spec para que sea visible, solo los features sin refinar"). No tiene RF en EARS, plan ni tareas: cada feature se refina (spec → plan → tareas) cuando se cumple su disparador.

Épica E09 (Técnico). Origen: revisión de ventas y barrido de todos los módulos del 2026-10-13 (PO: "considera cualquier entidad de crecimiento exponencial posible").

## Contexto y objetivo

Hoy varias pantallas cargan todos los registros de una entidad o calculan en Python lo que podría resolver la base. Con los volúmenes del piloto funciona, pero no escala. Estas features **no cambian lo que hace el sistema**: lo mantienen rápido cuando los datos crecen. Cada una lleva en el código un comentario `ponytail:` con su límite.

**Patrón de solución común (se construye una vez y se reutiliza):** un *selector con búsqueda en el servidor*, como la búsqueda de clientes de 0006a (RF-VEN-50): un endpoint `…/buscar/?q=` que devuelve hasta 10 coincidencias, resuelve un código exacto por índice y guarda el id oculto mostrando el elegido. Reemplaza a los `<select>` que listan todos los registros.

## Features (sin refinar)

| # | Feature | Hoy | Disparador | Idea de solución |
|---|---|---|---|---|
| F1 | **Búsqueda de productos en el servidor** | Las líneas del pedido, la venta directa (y su buscador, RF-VEN-65), la compra, el ajuste y la OP (componentes y salidas) cargan todos los productos en cada línea; también los filtros "Producto" del kardex y del listado de OP | Más de ~500 SKUs (p. ej. ropa con tallas y colores) o pantallas lentas | Selector con búsqueda en el servidor por nombre, SKU o código de barras; en las líneas, el elegido con su id oculto. Hoy el peso crece con productos × líneas |
| F2 | **Filtro de clientes en el servidor** | Filtro "Cliente" de pedidos y cobranzas con todos los clientes (elegirlo en el pedido ya busca en el servidor) | Más de ~500 clientes | Filtro con búsqueda en el servidor (ya existe `ventas/clientes/buscar/`) |
| F3 | **Proveedores en el servidor** | Selector de la compra, filtro de compras y pestaña "Compras" del producto con todos; el listado de proveedores no pagina | Más de ~300 proveedores | Selector con búsqueda en el servidor; paginar el listado |
| F4 | **Paginar empresas (plataforma)** | El listado del super admin no pagina | Más de ~200 empresas | Grilla estándar paginada en la base |
| F5 | **Pedidos paginados en la base** | `views.pedidos` (0006a) calcula disponibilidad, atrasados, quiebre y cobranza de todos los pedidos filtrados y pagina en Python; las tarjetas por estado (0008c) cuentan sobre todos; el aviso de quiebre del inicio recalcula todos los abiertos en cada carga | Miles de pedidos o listado/inicio lento | Disponibilidad solo de los abiertos de la página; paginar y contar en la base cuando no hay filtros calculados; un conteo agregado para el aviso |
| F6 | **Auditoría con paginación** | Muestra los últimos 200; lo anterior solo filtrando | Cuando haga falta revisar más atrás | Paginación por cursor, como el kardex |
| F7 | **Ordenar el código de ventas** | `sales/interfaces/views.py` (~600 líneas) y `pedido.html` (~230) | Al volver a tocar la facturación o el pedido | Separar la facturación en su propio módulo, como `interfaces/cobranzas.py` |
| F8 | **Doble envío simultáneo de la venta directa** | Dos envíos al mismo tiempo con el mismo token: el segundo choca con el índice único y da error (no duplica) | Si aparece en uso real | Capturar el choque y devolver la venta ya registrada |
| F9 | **Exportaciones grandes en segundo plano** | La exportación (0008c) se genera en la petición, con tope de 50 000 filas | Si se necesitan más filas o tarda más de lo razonable | Generarla con cron y avisar cuando esté lista |

**Acotadas (no requieren cambio):** almacenes, métodos de pago, unidades, categorías, marcas, impuestos, tipos de documento, roles y usuarios (limitados por el plan). **Ya resueltas:** kardex (cursor y exportación por iterador), stock, compras, OP, clientes y cobranzas (paginan en la base).

## Fuera de alcance

Cambios funcionales: cualquier feature que cambie lo que el usuario ve o puede hacer va a la spec de su módulo.
