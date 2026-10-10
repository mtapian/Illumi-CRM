# Plan 005 — Producción

Estado: borrador

Spec: `./spec.md` · Base técnica: `../000-arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/production`. Usa `CatalogoQuery` (recetas, presentaciones, materiales), `InventarioService` (consumos, granel, envasado) y `PedidosPort` (transiciones de pedidos, implementado por spec 006).

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/production/domain/receta.py` | Agregado `Receta`: insumos válidos, escalado, versionado | RF-PRD-01 a 03, 05 |
| `src/production/domain/orden.py` | Agregado `OrdenProduccion`: máquina de estados, consumos, terminar, anular, cerrar | RF-PRD-08 a 19, 30 a 33 |
| `src/production/domain/envasado.py` | `CalculadoraEnvasado`: litros, materiales, costo por presentación con ajuste de redondeo | RF-PRD-20 a 26 |
| `src/production/domain/sugerencia.py` | Litros sugeridos para un pedido | RF-PRD-07 |
| `src/production/domain/lote.py` | Código de lote sugerido y vencimientos | RF-PRD-13, 20, 25 |
| `src/production/domain/errores.py` | `TransicionInvalida`, `StockInsuficiente`, `GranelInsuficiente`, `PresentacionDeOtroGranel`, `OpTerminadaNoAnulable`… | todos los `SI … ENTONCES` |
| `src/production/application/recetas.py` | `CrearReceta`, `EditarReceta` | RF-PRD-01 a 03 |
| `src/production/application/ordenes.py` | `PlanificarOP`, `IniciarOP`, `RegistrarConsumoAdicional`, `TerminarOP`, `AnularOP`, `CerrarOP` | RF-PRD-04 a 19, 30 a 33 |
| `src/production/application/envasado.py` | `RegistrarEnvasado` | RF-PRD-20 a 29 |
| `src/production/application/reportes.py` | `ReporteLote(op_id)` | RF-PRD-34 |
| `src/production/application/fachada.py` | `ProduccionService.desvincular_pedido()`, `granel_disponible()`, `ops_en_proceso()` | (spec 006, RF-VEN-37, 41) |
| `src/production/application/puertos.py` | `PedidosPort`: `marcar_en_produccion`, `evaluar_tras_op`, `evaluar_listos` | RF-PRD-11, 19, 27, 32 |
| `src/production/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/production/interfaces/views/*.py` + `templates/production/*.html` | Pantallas de §5 (uso en tablet) | RF-PRD-01 a 34 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `production_receta` | empresa_id, granel_id, nombre, version, volumen_base_l, activa | UNIQUE(empresa_id, granel_id, version); una activa por granel | RF-PRD-01 a 03 |
| `production_receta_insumo` | receta_id, insumo_id, cantidad | UNIQUE(receta_id, insumo_id); `CHECK > 0` | RF-PRD-01, 05 |
| `production_op` | empresa_id, numero, receta_id, litros_planificados, litros_reales null, estado, fecha_prevista, fecha_inicio, fecha_fin `DATE`, almacen_origen_id, almacen_destino_id, lote_id null, costo_insumos, costo_indirecto, costo_total, costo_por_litro `NUMERIC(14,6)`, perdida_produccion, motivo, anulado_por, anulado_en | UNIQUE(empresa_id, numero) | RF-PRD-04 a 19, 30 a 33 |
| `production_op_pedido` | op_id, pedido_id | UNIQUE(op_id, pedido_id); varias OP por pedido y varios pedidos por OP | RF-PRD-04, 11, 19 |
| `production_op_consumo` | op_id, insumo_id, cantidad_teorica null, cantidad_real, costo_unitario, costo_total, movimiento_id | — | RF-PRD-08, 10, 17 |
| `production_envasado` | empresa_id, numero, op_id, lote_granel_id, fecha, almacen_id, litros_envasados, litros_merma, costo_granel, costo_por_litro_efectivo | UNIQUE(empresa_id, numero); inmutable | RF-PRD-20 a 29 |
| `production_envasado_salida` | envasado_id, presentacion_id, unidades, costo_unitario, costo_total, lote_id | `CHECK unidades >= 0 AND unidades = trunc(unidades)` | RF-PRD-20, 24 |
| `production_envasado_material` | envasado_id, material_id, cantidad, costo_unitario, costo_total | — | RF-PRD-20, 23 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `escalar(receta, litros) -> dict` | `cantidad × litros / volumen_base`, 4 decimales | RF-PRD-05 |
| `faltantes_de_insumos(teoricos, stock) -> list` | Para advertir al planificar y bloquear al iniciar | RF-PRD-06, 09 |
| `litros_sugeridos(lineas_pedido, stock_por_presentacion, contenido, granel_libre) -> Decimal` | `Σ max(0, faltante_i) × contenido_i − granel_libre` | RF-PRD-07 |
| `transicion(estado, accion, litros=None) -> estado` | Máquina de estados de la spec; `TransicionInvalida` en cualquier otro caso | RF-PRD-18, 33 |
| `costo_por_litro(costo_consumos, indirecto, litros_reales) -> UnitCost` | 6 decimales | RF-PRD-13 |
| `rendimiento(litros_reales, planificados) -> Decimal` | y si supera 100 % | RF-PRD-14 |
| `codigo_lote_sugerido(prefijo, correlativo) -> str` | `IPA-0020` | RF-PRD-13 |
| `vencimiento(fecha_base, vida_util) -> date \| None` | `None` si no hay vida útil | RF-PRD-13, 20 |
| `calcular_envasado(lineas, merma, granel_disp, promedio_granel, costos_materiales) -> Resultado` | Litros, materiales, costo unitario por presentación con ajuste ≤ 0,01 en la última; `GranelInsuficiente` | RF-PRD-20, 21, 24 |
| `es_descarte(lineas) -> bool` | Todas las unidades en 0 ⇒ salida de granel como `MERMA` | RF-PRD-26 |
| `vencimiento_al_sumar(actual, nuevo) -> date` | El más próximo | RF-PRD-25 |
| `pedidos_a_revertir(pedidos, ops_en_proceso) -> list` | Solo `EN_PRODUCCION` sin otra OP en proceso | RF-PRD-19 |

## 4. Algoritmos clave

**Costo del lote y del envasado** (ejemplo de la spec):
```
Iniciar OP-000020 (500 L): consumos reales = 798,00
Terminar: 425 L + indirecto 52,00 → costo_por_litro = 850,00 / 425 = 2,000000         # RF-PRD-13
Envasar: 1000 × 0,33 + 3 × 20 = 390 L + 19,5 L de merma = 409,5 L ≤ 425                # RF-PRD-21
  costo_granel = round(409,5 × 2,000000, 2) = 819,00
  efectivo = 819,00 / 390 = 2,100000
  botella = 0,33 × 2,10 + 0,85 + 0,05 + 0,20 + 0,0417 × 2,40 = 1,893080
  barril  = 20 × 2,10 + 1,50 = 43,500000
  ajuste = (819,00 + materiales) − Σ totales → se suma a la última presentación         # RF-PRD-24
```

**Registrar envasado** (RF-PRD-20 a 29):
```
RegistrarEnvasado(op, lineas, merma):
  actor.exige(produccion.envasado.registrar); op = select_for_update(op); exigir TERMINADA
  por línea: si presentacion.granel ≠ op.granel → PresentacionDeOtroGranel              # RF-PRD-22
  numerar envasado (y lote del terminado si hace falta)
  InventarioService.bloquear(granel + materiales + presentaciones)                        # RF-PRD-28
  r = calcular_envasado(…)
  si es_descarte(lineas): registrar_salida(granel, motivo=MERMA)                          # RF-PRD-26
  si no:
    registrar_salida(granel, CONSUMO_ENVASADO); registrar_salida(materiales)              # RF-PRD-23
    por presentación: crear o sumar al lote (mismo código, vencimiento_al_sumar)          # RF-PRD-20, 25
                      registrar_entrada(ENVASADO, costo_unitario)
  PedidosPort.evaluar_listos(op)                                                          # RF-PRD-27
  si granel del lote = 0: CerrarOP(op)                                                    # RF-PRD-30
```

**Anular OP** (RF-PRD-16 a 19):
```
AnularOP(op, motivo):
  op = select_for_update(op); transicion(op.estado, ANULAR)          # TERMINADA/CERRADA → error
  si EN_PROCESO: InventarioService.revertir('OP', op.id)             # incluye consumos adicionales
  por p en pedidos_a_revertir(pedidos(op), ops_en_proceso): PedidosPort.revertir_a_confirmado(p)
```

## 5. Interfaz

Pensada para tablet en planta: botones grandes y una acción principal por pantalla (RNF-PRD-02).

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/produccion/recetas/` | Listado por granel con versiones; formset de insumos; aviso "se creará la versión N" si ya se usó | RF-PRD-01 a 03 |
| `/produccion/op/` | Tablero kanban por estado (HTMX) | RF-PRD-04, 33 |
| `/produccion/op/nueva` | Receta, litros (sugeridos si viene de un pedido), insumos teóricos con disponibilidad y advertencia de faltantes | RF-PRD-04 a 07 |
| `/produccion/op/<id>` | Acciones según el estado: iniciar (cantidades reales precargadas), consumo adicional, terminar (litros, indirecto, lote sugerido; advertencia > 100 %), anular, cerrar | RF-PRD-08 a 19, 30 a 33 |
| `/produccion/op/<id>/envasar` | Una fila por presentación del granel + campo de merma; litros y saldo calculados en vivo; errores con litros requeridos vs. disponibles | RF-PRD-20 a 29 |
| `/produccion/op/<id>/reporte` | Teórico vs. real, rendimiento, costo por litro, envasados, merma (L y %), saldo | RF-PRD-34 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| El granel sale al costo promedio del producto | Costeo específico por lote | Un solo método de costeo (art. 4.2); pendiente de Q12 |
| La merma de envasado se absorbe en el costo de las unidades | Llevarla a resultados | Es parte del costo de producir la botella |
| Una OP terminada o un envasado no se anulan; se corrigen con ajustes | Anulación que revierta el envasado | Constitución art. 4.5 (v1.1.0): revertirlos falsearía el inventario ya vendido |
| Ajuste de redondeo en la última presentación | Repartirlo proporcionalmente | Determinista y verificable al céntimo (RF-PRD-24) |
| La OP actualiza los pedidos a través de `PedidosPort` | Escribir en las tablas de ventas | Independencia de contextos (art. 7.2) |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/production tests/acceptance -k "E05"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/production/unit/test_receta.py` | Escalado, insumos válidos, versionado | RF-PRD-01 a 03, 05 |
| Unitario | `tests/production/unit/test_maquina_estados.py` | Todas las transiciones válidas e inválidas (parametrizado) | RF-PRD-18, 33 |
| Unitario | `tests/production/unit/test_envasado.py` | Ejemplo completo de la spec (1,893080 / 43,500000); descarte; granel insuficiente | RF-PRD-20, 21, 24, 26 |
| Property-based | `tests/production/unit/test_conservacion.py` | Σ entradas = granel + materiales (exacto a 0,01) con 3+ presentaciones | RF-PRD-24 |
| Unitario | `tests/production/unit/test_sugerencia.py` | Faltante por presentación; 95,84 L del escenario de la spec 006 | RF-PRD-07 |
| Caso de uso | `tests/production/usecases/test_ordenes.py` | Planificar con advertencia, iniciar sin insumos, consumo adicional sin stock, terminar, lote perdido, anular (pedidos) | RF-PRD-04, 06, 08 a 19 |
| Caso de uso | `tests/production/usecases/test_envasado_pedidos.py` | Pedidos a `LISTO` tras envasar y cerrar; otra OP en proceso | RF-PRD-27, 29 a 32 |
| Integración | `tests/production/integration/test_concurrencia.py` | Doble inicio de OP; dos envasados del mismo lote | RF-PRD-12, 28 |
| Integración | `tests/production/integration/test_reporte.py` | Reporte del lote | RF-PRD-34 |
| Aceptación | `features/recetas_y_op.feature`, `features/envasado.feature` | Escenarios de la spec (los `@pendiente-q10` se omiten) | todos |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-PRD-01, RF-PRD-02, RF-PRD-03 | §1 `receta.py`, `recetas.py` · §2 recetas · §5 `/produccion/recetas/` · §7 `test_receta.py` |
| RF-PRD-04, RF-PRD-05, RF-PRD-06, RF-PRD-07 | §1 `ordenes.py`, `sugerencia.py` · §3 `escalar`, `faltantes_de_insumos`, `litros_sugeridos` · §5 nueva OP · §7 |
| RF-PRD-08, RF-PRD-09, RF-PRD-10, RF-PRD-11, RF-PRD-12 | §1 `orden.py`, `puertos.py` · §3 `faltantes_de_insumos`, `transicion` · §5 detalle OP · §7 |
| RF-PRD-13, RF-PRD-14, RF-PRD-15 | §3 `costo_por_litro`, `rendimiento`, `codigo_lote_sugerido`, `vencimiento` · §4 costo del lote · §7 |
| RF-PRD-16, RF-PRD-17, RF-PRD-18, RF-PRD-19 | §3 `transicion`, `pedidos_a_revertir` · §4 anular OP · §7 `test_ordenes.py` |
| RF-PRD-20, RF-PRD-21, RF-PRD-22, RF-PRD-23, RF-PRD-24, RF-PRD-25, RF-PRD-26, RF-PRD-27, RF-PRD-28, RF-PRD-29 | §1 `envasado.py` · §3 `calcular_envasado`, `es_descarte`, `vencimiento_al_sumar` · §4 registrar envasado · §5 `/envasar` · §7 |
| RF-PRD-30, RF-PRD-31, RF-PRD-32, RF-PRD-33 | §1 `ordenes.py` · §3 `transicion` · §4 registrar envasado (cierre) · §7 |
| RF-PRD-34 | §1 `reportes.py` · §5 `/reporte` · §7 `test_reporte.py` |

## 9. Dependencias de dudas abiertas

- **Q10 (lote perdido):** RF-PRD-15 y la transición `EN_PROCESO → CERRADA`; los tests correspondientes quedan marcados como omitidos hasta la aprobación.
- **Q12 (costeo del granel por lote / costo indirecto):** cambiaría `calcular_envasado` y `TerminarOP`.
- **Wireframes de OP y envasado:** necesarios antes de implementar §5.
