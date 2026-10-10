# Plan 0005a — Producción: recetas y órdenes de producción

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/production`. Usa `CatalogoQuery` (recetas, presentaciones, materiales), `InventarioService` (consumos, granel, envasado) y `PedidosPort` (transiciones de pedidos, implementado por épica 0006). Requiere: 0002a, 0003a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/production/domain/receta.py` | Agregado `Receta`: insumos válidos, escalado, versionado | RF-PRD-01 a 03, 05 |
| `src/production/domain/orden.py` | Agregado `OrdenProduccion`: máquina de estados, consumos, terminar, anular, cerrar | RF-PRD-08 a 19 |
| `src/production/domain/sugerencia.py` | Litros sugeridos para un pedido | RF-PRD-07 |
| `src/production/domain/lote.py` | Código de lote sugerido y vencimientos | RF-PRD-13 |
| `src/production/domain/errores.py` | `TransicionInvalida`, `StockInsuficiente`, `GranelInsuficiente`, `PresentacionDeOtroGranel`, `OpTerminadaNoAnulable`… | todos los `SI … ENTONCES` |
| `src/production/application/recetas.py` | `CrearReceta`, `EditarReceta` | RF-PRD-01 a 03 |
| `src/production/application/ordenes.py` | `PlanificarOP`, `IniciarOP`, `RegistrarConsumoAdicional`, `TerminarOP`, `AnularOP`, `CerrarOP` | RF-PRD-04 a 19 |
| `src/production/application/fachada.py` | `ProduccionService.desvincular_pedido()`, `granel_disponible()`, `ops_en_proceso()` | (épica 0006, RF-VEN-37, 41) |
| `src/production/application/puertos.py` | `PedidosPort`: `marcar_en_produccion`, `evaluar_tras_op`, `evaluar_listos` | RF-PRD-11, 19 |
| `src/production/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/production/interfaces/views/*.py` + `templates/production/*.html` | Pantallas de §5 (uso en tablet) | RF-PRD-01 a 19 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `production_receta` | empresa_id, granel_id, nombre, version, volumen_base_l, activa | UNIQUE(empresa_id, granel_id, version); una activa por granel | RF-PRD-01 a 03 |
| `production_receta_insumo` | receta_id, insumo_id, cantidad | UNIQUE(receta_id, insumo_id); `CHECK > 0` | RF-PRD-01, 05 |
| `production_op` | empresa_id, numero, receta_id, litros_planificados, litros_reales null, estado, fecha_prevista, fecha_inicio, fecha_fin `DATE`, almacen_origen_id, almacen_destino_id, lote_id null, costo_insumos, costo_indirecto, costo_total, costo_por_litro `NUMERIC(14,6)`, perdida_produccion, motivo, anulado_por, anulado_en | UNIQUE(empresa_id, numero) | RF-PRD-04 a 19 |
| `production_op_pedido` | op_id, pedido_id | UNIQUE(op_id, pedido_id); varias OP por pedido y varios pedidos por OP | RF-PRD-04, 11, 19 |
| `production_op_consumo` | op_id, insumo_id, cantidad_teorica null, cantidad_real, costo_unitario, costo_total, movimiento_id | — | RF-PRD-08, 10, 17 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `escalar(receta, litros) -> dict` | `cantidad × litros / volumen_base`, 4 decimales | RF-PRD-05 |
| `faltantes_de_insumos(teoricos, stock) -> list` | Para advertir al planificar y bloquear al iniciar | RF-PRD-06, 09 |
| `litros_sugeridos(lineas_pedido, stock_por_presentacion, contenido, granel_libre) -> Decimal` | `Σ max(0, faltante_i) × contenido_i − granel_libre` | RF-PRD-07 |
| `transicion(estado, accion, litros=None) -> estado` | Máquina de estados de la spec; `TransicionInvalida` en cualquier otro caso | RF-PRD-18 |
| `costo_por_litro(costo_consumos, indirecto, litros_reales) -> UnitCost` | 6 decimales | RF-PRD-13 |
| `rendimiento(litros_reales, planificados) -> Decimal` | y si supera 100 % | RF-PRD-14 |
| `codigo_lote_sugerido(prefijo, correlativo) -> str` | `IPA-0020` | RF-PRD-13 |
| `vencimiento(fecha_base, vida_util) -> date \| None` | `None` si no hay vida útil | RF-PRD-13 |
| `pedidos_a_revertir(pedidos, ops_en_proceso) -> list` | Solo `EN_PRODUCCION` sin otra OP en proceso | RF-PRD-19 |

## 4. Algoritmos clave

**Anular OP** (RF-PRD-16 a 19):

```
AnularOP(op, motivo):
  op = select_for_update(op); transicion(op.estado, ANULAR)          # TERMINADA/CERRADA → error
  si EN_PROCESO: InventarioService.revertir('OP', op.id)             # incluye consumos adicionales
  por p en pedidos_a_revertir(pedidos(op), ops_en_proceso): PedidosPort.revertir_a_confirmado(p)
```

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/produccion/recetas/` | Listado por granel con versiones; formset de insumos; aviso "se creará la versión N" si ya se usó | RF-PRD-01 a 03 |
| `/produccion/op/` | Tablero kanban por estado (HTMX) | RF-PRD-04 |
| `/produccion/op/nueva` | Receta, litros (sugeridos si viene de un pedido), insumos teóricos con disponibilidad y advertencia de faltantes | RF-PRD-04 a 07 |
| `/produccion/op/<id>` | Acciones según el estado: iniciar (cantidades reales precargadas), consumo adicional, terminar (litros, indirecto, lote sugerido; advertencia > 100 %), anular, cerrar | RF-PRD-08 a 19 |

Pensada para tablet en planta: botones grandes y una acción principal por pantalla (RNF-PRD-02).

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| El granel sale al costo promedio del producto | Costeo específico por lote | Un solo método de costeo (art. 4.2); pendiente de Q12 |
| Una OP terminada o un envasado no se anulan; se corrigen con ajustes | Anulación que revierta el envasado | Constitución art. 4.5 (v1.1.0): revertirlos falsearía el inventario ya vendido |
| La OP actualiza los pedidos a través de `PedidosPort` | Escribir en las tablas de ventas | Independencia de contextos (art. 7.2) |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/production tests/acceptance -k "E05a"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/production/unit/test_receta.py` | Escalado, insumos válidos, versionado | RF-PRD-01 a 03, 05 |
| Unitario | `tests/production/unit/test_maquina_estados.py` | Todas las transiciones válidas e inválidas (parametrizado) | RF-PRD-18, 33 |
| Unitario | `tests/production/unit/test_sugerencia.py` | Faltante por presentación; 95,84 L del escenario de la épica 0006 | RF-PRD-07 |
| Caso de uso | `tests/production/usecases/test_ordenes.py` | Planificar con advertencia, iniciar sin insumos, consumo adicional sin stock, terminar, lote perdido, anular (pedidos) | RF-PRD-04, 06, 08 a 19 |
| Integración | `tests/production/integration/test_concurrencia.py` | Doble inicio de OP; dos envasados del mismo lote | RF-PRD-12, 28 |
| Aceptación | `features/recetas_y_op.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-PRD-01, RF-PRD-02, RF-PRD-03 | §1 `receta.py`, `recetas.py` · §2 recetas · §5 `/produccion/recetas/` · §7 `test_receta.py` |
| RF-PRD-04, RF-PRD-05, RF-PRD-06, RF-PRD-07 | §1 `ordenes.py`, `sugerencia.py` · §3 `escalar`, `faltantes_de_insumos`, `litros_sugeridos` · §5 nueva OP · §7 |
| RF-PRD-08, RF-PRD-09, RF-PRD-10, RF-PRD-11, RF-PRD-12 | §1 `orden.py`, `puertos.py` · §3 `faltantes_de_insumos`, `transicion` · §5 detalle OP · §7 |
| RF-PRD-13, RF-PRD-14, RF-PRD-15 | §3 `costo_por_litro`, `rendimiento`, `codigo_lote_sugerido`, `vencimiento` · §4 costo del lote · §7 |
| RF-PRD-16, RF-PRD-17, RF-PRD-18, RF-PRD-19 | §3 `transicion`, `pedidos_a_revertir` · §4 anular OP · §7 `test_ordenes.py` |

## 9. Dependencias de dudas abiertas

- **Q10 (lote perdido):** RF-PRD-15 y la transición `EN_PROCESO → CERRADA`; los tests correspondientes quedan marcados como omitidos hasta la aprobación.

- **Q12 (costeo del granel por lote / costo indirecto):** cambiaría `calcular_envasado` y `TerminarOP`.

- **Wireframes de OP y envasado:** necesarios antes de implementar §5.
