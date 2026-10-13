# Plan 0008c — Reportes: dashboard, exportación e indicadores de los listados

Estado: aprobado (PO: "go", 2026-10-13), para la spec aprobada el 2026-10-13 (PO: "ok")

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.2.0) · UX: `../../docs/ux.md`

Sin contexto nuevo. El inicio sigue siendo de tenancy, que pinta lo que **registran** los demás contextos (el mismo patrón que `menu.py` y `avisos.py`): tenancy no conoce a ventas ni al catálogo. Las piezas comunes (gráficos SVG y exportación) van en `shared/interfaces`, sin dependencias nuevas (art. 7.6).

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/shared/interfaces/graficos.py` | Funciones puras que devuelven SVG: `linea(puntos)`, `dona(segmentos)`, `barras(items)`; ejes, etiquetas con valores, vacío sin error | 18 a 21, 24 |
| `src/shared/interfaces/exportar.py` | `respuesta(nombre, columnas, filas, formato)`: XLSX escrito con `zipfile` (XML de hoja con cadenas en línea, una fila a la vez sobre un archivo temporal) o CSV (UTF-8 con BOM) por `StreamingHttpResponse`; tope de 50 000 filas | 15, 25 |
| `src/shared/interfaces/tablero.py` | Registro de **tarjetas** y **paneles** del inicio (clave, título, función `(request) -> contexto/HTML`, permiso, orden) | 14, 17 |
| `src/tenancy/interfaces/views/inicio.py` y `dashboard.html` | Pinta tarjetas, barra de avisos (los `avisos` existentes, solo los que tienen algo) y paneles en dos columnas, con la fecha de hoy en las migas | 14, 17 |
| `src/sales/infrastructure/reportes.py` | Consultas agregadas (una por cifra, en la base): ventas de un día y de un mes, por día (14), por mes (año), cobrado por método, por categoría, más vendidos, últimas ventas | 14, 18 a 23 |
| `src/sales/interfaces/tablero.py` | Registra tarjetas (ventas de hoy, del mes, clientes activos) y paneles (gráficos y tablas) con sus permisos | 14, 18 a 23 |
| `src/catalog/interfaces/urls.py` | Registra la tarjeta "Productos activos" | 14 |
| Vistas de productos, kardex, pedidos y cobranzas | `?formato=xlsx|csv` con las columnas de su grilla (definidas una vez para la grilla y la exportación); pedidos, una fila por línea | 15, 16, 25 |
| `sales/interfaces/views.py` y `cobranzas.py` | Conteos por estado (pedidos) y conteos y saldos (cobranzas) con los filtros salvo el estado; tarjetas que enlazan al filtro | 26 |

## 2. Modelo de datos

Sin tablas nuevas. Índices si hacen falta para RNF-FIN-04: `sales_pedido (empresa, fecha_emision)` y `sales_pago (empresa, fecha)`.

## 3. Funciones puras

- `graficos.linea(puntos: list[(etiqueta, valor)]) -> str`, `dona(segmentos: list[(etiqueta, valor)]) -> str`, `barras(items) -> str`: escala "redonda" del eje (1, 2, 5 × 10ⁿ), valores con 2 decimales, sin datos → ejes en 0.
- `exportar.hoja_xlsx(columnas, filas)`: escribe el XML de la hoja (`inlineStr` para textos, números como `n`); escapa `&<>"`.

## 4. Algoritmos clave

```
ventas_por_dia(desde, hasta):  Pedido.filter(estado ∈ {FACTURADO, ENTREGADO}, fecha_emision ∈ [desde, hasta])
                                .values("fecha_emision").annotate(Sum("total"))  → completa los días sin ventas con 0
cobrado_por_metodo(mes):        Pago.filter(anulado_en IS NULL, fecha ∈ mes).values("metodo__nombre").annotate(Sum("monto"))
por_categoria(mes):             PedidoLinea.filter(pedido facturado del mes).values("producto__categoria__nombre")
                                .annotate(Sum("subtotal")) → None = "Sin categoría"
exportar(qs, columnas, formato): if qs.count() > 50 000 → error; else iterar qs.iterator() fila a fila
```

## 5. Interfaz

- **Inicio:** tarjetas de colores con ícono SVG (como la referencia), barra de avisos, paneles en 2 columnas (1 en el celular).
- **Exportar:** en las grillas de productos, kardex, pedidos y cobranzas, "Exportar ▾" (XLSX, CSV) arriba a la derecha (`docs/ux.md` §3), con la consulta actual; solo con `reportes.exportar`.
- **Indicadores por estado:** fila de tarjetas sobre la grilla de pedidos y la de cobranzas; la activa se resalta.

## 6. Decisiones técnicas

- **Registro de tarjetas y paneles** (como `avisos`): tenancy no importa a ventas ni al catálogo (import-linter). Alternativa descartada: que el inicio consulte cada contexto directamente.
- **SVG en el servidor** (PO, Q5): sin JavaScript ni CDN; alternativa descartada: Chart.js.
- **XLSX con `zipfile`** (PO, Q6): lo mínimo que Excel abre (workbook, hoja, estilos básicos); alternativa descartada: `openpyxl` (dependencia nueva). Se pasa a `openpyxl` si algún día se piden formatos.
- **Columnas una sola vez:** cada grilla define su lista de columnas `(título, función)` y la usan la tabla y la exportación, así no se desalinean.
- La funcionalidad "Exportación CSV" del catálogo de accesos pasa a llamarse "Exportación (XLSX y CSV)" (mismo permiso `reportes.exportar`).

## 7. Estrategia de tests (pytest)

- Unitarios: escalas y SVG de los tres gráficos (con y sin datos); XLSX que se vuelve a leer con `zipfile` y su XML; CSV con BOM.
- Integración: cada consulta agregada con datos conocidos (incluye cancelados, pagos anulados, sin categoría, 23:30 de Lima); inicio por permiso; exportaciones con filtros, sin costos y con el tope; conteos por estado.
- Rendimiento: inicio con 10 000 ventas, p95 < 800 ms (como el de stock de 0003c).
- Aceptación: `tests/acceptance/test_e08c.py` con los 8 escenarios.

## 8. Cobertura de RF

| RF | Dónde |
|---|---|
| 14, 17 | `tablero.py`, `inicio.py`; escenarios de tarjetas y permisos |
| 18 a 21, 24 | `graficos.py`, `reportes.py`; escenario de gráficos y de empresa sin ventas |
| 22, 23 | `reportes.py`; escenario de tarjetas |
| 15, 16, 25 | `exportar.py` y las vistas; escenarios de exportación |
| 26 | vistas de pedidos y cobranzas; escenario de indicadores |
