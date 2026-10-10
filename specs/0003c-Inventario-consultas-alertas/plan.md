# Plan 0003c — Inventario: stock, kardex y alertas

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/inventory`. Es el núcleo transaccional: compras, producción y ventas **solo** cambian stock a través de su fachada `InventarioService` (constitución art. 4). Requiere: 0003a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/inventory/domain/lotes.py` | `lote_vencido`, `lotes_por_vencer` con `hoy` | RF-INV-15, 16 |
| `src/inventory/domain/errores.py` | `StockInsuficiente`, `LoteVencido`, `AnulacionConConsumoPosterior`, `CostoRequerido`, `SaldoInicialNoPermitido`… | todos los `SI … ENTONCES` |
| `src/inventory/application/consultas.py` | `ConsultarStock`, `ConsultarKardex`, `ProductosBajoMinimo`, `LotesPorVencer`, `DiferenciasDeConteo` | RF-INV-04 a 07, 14 a 16 |
| `src/inventory/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios con locks en el orden de 0000 §5 | §2 |
| `src/inventory/infrastructure/sql/*.sql` | `trg_movimiento_inmutable`, `vw_kardex`, `vw_stock_valorizado` | RF-INV-04, 06 |
| `src/inventory/interfaces/views/*.py` + `templates/inventory/*.html` | Pantallas de §5 | RF-INV-04 a 07, 14 a 16 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `inventory_lote` | empresa_id, producto_id, codigo, fecha_produccion, fecha_vencimiento null, origen_tipo, origen_id | UNIQUE(empresa_id, producto_id, codigo) | RF-INV-15 |
| `inventory_stock` | empresa_id, producto_id, almacen_id, lote_id null, cantidad `NUMERIC(14,4)` | UNIQUE NULLS NOT DISTINCT (…); `CHECK cantidad >= 0` | RF-INV-04 |
| `inventory_movimiento` | empresa_id, fecha `timestamptz`, tipo, motivo, producto_id, almacen_id, lote_id, cantidad, costo_unitario `NUMERIC(14,6)`, costo_total `NUMERIC(14,2)`, saldo_cantidad, saldo_promedio, ref_tipo (`COMPRA`, `AJUSTE`, `OP`, `ENVASADO`, `VENTA`), ref_id, revierte_id null, usuario_id | `UNIQUE(revierte_id) WHERE NOT NULL`; trigger de inmutabilidad | RF-INV-06 |
| `inventory_config` | empresa_id, dias_alerta_vencimiento (30) | UNIQUE(empresa_id) | RF-INV-15 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `lote_vencido(fecha_vencimiento, hoy) -> bool` | `fecha_vencimiento is not None and fecha_vencimiento < hoy` | RF-INV-16 |
| `lotes_por_vencer(lotes_con_stock, dias, hoy) -> list` | `hoy ≤ vencimiento ≤ hoy + dias` | RF-INV-15 |
| `bajo_minimo(stock_total, minimo) -> bool` | `stock_total ≤ minimo` | RF-INV-14 |

## 4. Algoritmos clave

Sin algoritmos no triviales: la lógica está en las funciones puras de §3.

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/inventario/stock` | Tabla por producto con desplegable por almacén y lote (vencimiento en rojo si vencido), costo y valor (ocultos sin `inventario.costo.ver`); totales por tipo; filtros | RF-INV-04, 05, 16 |
| `/inventario/kardex?producto=` | Tabla paginada por cursor con enlace al documento; saldos solo con producto elegido; exportar CSV | RF-INV-06, 07 |
| Dashboard: avisos "Stock bajo" y "Por vencer" | Listas cortas con enlace al producto o lote | RF-INV-14, 15 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/inventory tests/acceptance -k "E03c"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Integración | `tests/inventory/integration/test_consultas.py` | Stock, kardex, bajo mínimo, por vencer; rendimiento con 100 000 movimientos | RF-INV-04 a 07, 14 a 16, RNF-INV-02 |
| Aceptación | `features/ajustes_lotes_alertas.feature`, `features/costo_y_kardex.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-INV-04, RF-INV-05, RF-INV-06, RF-INV-07 | §1 `consultas.py`, vistas SQL · §5 stock y kardex · §7 `test_consultas.py` |
| RF-INV-14, RF-INV-15, RF-INV-16 | §1 `lotes.py`, `consultas.py` · §3 `bajo_minimo`, `lotes_por_vencer`, `lote_vencido` · §5 avisos · §7 |

## 9. Dependencias de dudas abiertas

- Ninguna.
