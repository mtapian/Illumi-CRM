# Plan 0003c — Inventario: stock, kardex y alertas

Estado: implementado (2026-10-10)

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/inventory`. Solo consultas: no cambia stock. Los datos ya existen (0003a).

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/inventory/domain/lotes.py` | Se agregan `por_vencer(vencimiento, dias, hoy)` y `dias_restantes(vencimiento, hoy)` | RF-INV-15, 16 |
| `src/inventory/domain/alertas.py` | `bajo_minimo(stock_total, minimo)`: `minimo > 0 and stock_total ≤ minimo` | RF-INV-14 |
| `src/inventory/infrastructure/consultas.py` | Consultas de lectura con el ORM: stock por producto con detalle por almacén y lote y valorización por categoría; kardex filtrado y paginado por cursor (`id`); productos bajo mínimo; lotes por vencer y vencidos con stock | RF-INV-04 a 07, 14 a 16 |
| `src/inventory/infrastructure/models.py` | `ConfigInventario` (días de alerta) | RF-INV-15 |
| `src/inventory/interfaces/views.py` + plantillas | `/inventario/stock/`, `/inventario/kardex/` (+ CSV), `/inventario/configuracion/` | RF-INV-04 a 07, 15, 16 |
| `src/shared/interfaces/avisos.py` | Registro de avisos del dashboard (mismo patrón que `menu.py` y `pestanas.py`): cada contexto agrega los suyos con permiso; tenancy los pinta sin conocer al inventario | RF-INV-14, 15, 30 |
| `src/inventory/interfaces/urls.py` | Registra "Stock bajo" y "Por vencer" (`inventario.stock.ver`) y las opciones de menú | RF-INV-14, 15, 30 |
| `src/tenancy/interfaces/views/inicio.py` + `dashboard.html` | Pinta `avisos.para(request)` | RF-INV-14, 15 |
| `src/catalog/interfaces/views.py` | El filtro "stock bajo" del listado de productos pasa a `≤`; conserva su recorrido por el puerto (el catálogo no conoce al inventario; se optimiza si la prueba de rendimiento lo pide) | RF-INV-14, RF-CAT-14 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `inventory_configinventario` | empresa_id, dias_alerta_vencimiento (30) | UNIQUE(empresa_id); CHECK 1 ≤ días ≤ 365; la fila se crea al guardar (sin fila = 30) | RF-INV-15 |
| índices | `inventory_movimiento (empresa_id, producto_id, id)` y `(empresa_id, fecha)`; el stock ya tiene el índice único `(empresa, producto, almacén, lote)` | para RNF-INV-02 | RNF-INV-02 |

Lote, stock y movimiento ya existen (0003a).

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `lote_vencido(vencimiento, hoy)` | Ya existe (0003a) | RF-INV-16 |
| `por_vencer(vencimiento, dias, hoy) -> bool` | `vencimiento is not None and hoy ≤ vencimiento ≤ hoy + dias` | RF-INV-15 |
| `dias_restantes(vencimiento, hoy) -> int` | `(vencimiento − hoy).days` | RF-INV-15 |
| `bajo_minimo(stock_total, minimo) -> bool` | `minimo > 0 and stock_total ≤ minimo` | RF-INV-14 |

## 4. Algoritmos clave

Sin algoritmos no triviales. El kardex pagina por cursor (`id > último`) para no contar 100 000 filas.

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/inventario/stock/` | Listado (buscador y filtros de RF-INV-05): producto, stock total, costo promedio, valor; detalle desplegable por almacén y lote (`<details>`, sin JS) con vencimiento en rojo si vencido; totales por categoría y general; costos ocultos sin `inventario.costo.ver` | RF-INV-04, 05, 16 |
| `/inventario/kardex/?producto=…` | Tabla con filtros de RF-INV-07, 50 filas por página por cursor, enlace al ajuste de origen, saldos solo con producto; "Exportar CSV" con los mismos filtros | RF-INV-06, 07 |
| `/inventario/configuracion/` | Días de alerta de vencimiento | RF-INV-15 |
| Dashboard | Tarjetas "Stock bajo" (producto, stock y mínimo) y "Por vencer" (lote, producto, días o "Vencido" en rojo), con enlace al stock o al kardex | RF-INV-14 a 16, 30 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Consultas con el ORM y dos índices | Vistas SQL `vw_kardex`, `vw_stock_valorizado` | Menos objetos que mantener; se pasa a vistas si la prueba de rendimiento lo pide (art. 7.6) |
| Registro de avisos en `shared/interfaces` | Que tenancy consulte al inventario | Tenancy no depende de los contextos de arriba (contratos de import-linter) |
| Días de alerta en una tabla del inventario | Ajuste de empresa de 0001b | Es un dato del inventario, sin vigencia; no hace falta su historial |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/inventory tests/acceptance -k "E03c"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/inventory/unit/test_alertas.py` | `por_vencer`, `dias_restantes`, `bajo_minimo` (mínimo 0, igual al mínimo) | RF-INV-14, 15 |
| Integración | `tests/inventory/integration/test_consultas.py` | Stock con detalle y valorización por categoría; filtros; kardex con filtros, cursor y CSV; costos ocultos sin permiso; rendimiento con 100 000 movimientos (p95 < 800 ms) | RF-INV-04 a 07, RNF-INV-02, RF-TEN-51 |
| Integración | `tests/inventory/integration/test_pantallas.py` | Dashboard con avisos y sin ellos para quien no ve stock; configuración de días | RF-INV-14 a 16, 30 |
| Aceptación | `features/ajustes_lotes_alertas.feature`, `features/costo_y_kardex.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-INV-04, 05 | §1 `consultas.py` · §5 stock · §7 |
| RF-INV-06, 07 | §1 `consultas.py` · §2 índices · §5 kardex · §7 |
| RF-INV-14 a 16, 30 | §1 `alertas.py`, `lotes.py`, `avisos.py` · §2 `ConfigInventario` · §5 dashboard y configuración · §7 |

## 9. Dependencias de dudas abiertas

- Ninguna.
