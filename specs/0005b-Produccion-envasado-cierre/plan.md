# Plan 0005b — Producción: envasado, cierre y costo del lote

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/production`. Usa `CatalogoQuery` (recetas, presentaciones, materiales), `InventarioService` (consumos, granel, envasado) y `PedidosPort` (transiciones de pedidos, implementado por épica 0006). Requiere: 0005a, 0002b.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/production/domain/orden.py` | Agregado `OrdenProduccion`: máquina de estados, consumos, terminar, anular, cerrar | RF-PRD-30 a 33 |
| `src/production/domain/envasado.py` | `CalculadoraEnvasado`: litros, materiales, costo por presentación con ajuste de redondeo | RF-PRD-20 a 26 |
| `src/production/domain/lote.py` | Código de lote sugerido y vencimientos | RF-PRD-20, 25 |
| `src/production/domain/errores.py` | `TransicionInvalida`, `StockInsuficiente`, `GranelInsuficiente`, `PresentacionDeOtroGranel`, `OpTerminadaNoAnulable`… | todos los `SI … ENTONCES` |
| `src/production/application/ordenes.py` | `PlanificarOP`, `IniciarOP`, `RegistrarConsumoAdicional`, `TerminarOP`, `AnularOP`, `CerrarOP` | RF-PRD-30 a 33 |
| `src/production/application/envasado.py` | `RegistrarEnvasado` | RF-PRD-20 a 29 |
| `src/production/application/reportes.py` | `ReporteLote(op_id)` | RF-PRD-34 |
| `src/production/application/puertos.py` | `PedidosPort`: `marcar_en_produccion`, `evaluar_tras_op`, `evaluar_listos` | RF-PRD-27, 32 |
| `src/production/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/production/interfaces/views/*.py` + `templates/production/*.html` | Pantallas de §5 (uso en tablet) | RF-PRD-20 a 34 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `production_op` | empresa_id, numero, receta_id, litros_planificados, litros_reales null, estado, fecha_prevista, fecha_inicio, fecha_fin `DATE`, almacen_origen_id, almacen_destino_id, lote_id null, costo_insumos, costo_indirecto, costo_total, costo_por_litro `NUMERIC(14,6)`, perdida_produccion, motivo, anulado_por, anulado_en | UNIQUE(empresa_id, numero) | RF-PRD-30 a 33 |
| `production_envasado` | empresa_id, numero, op_id, lote_granel_id, fecha, almacen_id, litros_envasados, litros_merma, costo_granel, costo_por_litro_efectivo | UNIQUE(empresa_id, numero); inmutable | RF-PRD-20 a 29 |
| `production_envasado_salida` | envasado_id, presentacion_id, unidades, costo_unitario, costo_total, lote_id | `CHECK unidades >= 0 AND unidades = trunc(unidades)` | RF-PRD-20, 24 |
| `production_envasado_material` | envasado_id, material_id, cantidad, costo_unitario, costo_total | — | RF-PRD-20, 23 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `transicion(estado, accion, litros=None) -> estado` | Máquina de estados de la spec; `TransicionInvalida` en cualquier otro caso | RF-PRD-33 |
| `vencimiento(fecha_base, vida_util) -> date \| None` | `None` si no hay vida útil | RF-PRD-20 |
| `calcular_envasado(lineas, merma, granel_disp, promedio_granel, costos_materiales) -> Resultado` | Litros, materiales, costo unitario por presentación con ajuste ≤ 0,01 en la última; `GranelInsuficiente` | RF-PRD-20, 21, 24 |
| `es_descarte(lineas) -> bool` | Todas las unidades en 0 ⇒ salida de granel como `MERMA` | RF-PRD-26 |
| `vencimiento_al_sumar(actual, nuevo) -> date` | El más próximo | RF-PRD-25 |

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

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/produccion/op/` | Tablero kanban por estado (HTMX) | RF-PRD-33 |
| `/produccion/op/<id>` | Acciones según el estado: iniciar (cantidades reales precargadas), consumo adicional, terminar (litros, indirecto, lote sugerido; advertencia > 100 %), anular, cerrar | RF-PRD-30 a 33 |
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

Comando: `pytest tests/production tests/acceptance -k "E05b"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/production/unit/test_maquina_estados.py` | Todas las transiciones válidas e inválidas (parametrizado) | RF-PRD-18, 33 |
| Unitario | `tests/production/unit/test_envasado.py` | Ejemplo completo de la spec (1,893080 / 43,500000); descarte; granel insuficiente | RF-PRD-20, 21, 24, 26 |
| Property-based | `tests/production/unit/test_conservacion.py` | Σ entradas = granel + materiales (exacto a 0,01) con 3+ presentaciones | RF-PRD-24 |
| Caso de uso | `tests/production/usecases/test_envasado_pedidos.py` | Pedidos a `LISTO` tras envasar y cerrar; otra OP en proceso | RF-PRD-27, 29 a 32 |
| Integración | `tests/production/integration/test_concurrencia.py` | Doble inicio de OP; dos envasados del mismo lote | RF-PRD-12, 28 |
| Integración | `tests/production/integration/test_reporte.py` | Reporte del lote | RF-PRD-34 |
| Aceptación | `features/envasado.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-PRD-20, RF-PRD-21, RF-PRD-22, RF-PRD-23, RF-PRD-24, RF-PRD-25, RF-PRD-26, RF-PRD-27, RF-PRD-28, RF-PRD-29 | §1 `envasado.py` · §3 `calcular_envasado`, `es_descarte`, `vencimiento_al_sumar` · §4 registrar envasado · §5 `/envasar` · §7 |
| RF-PRD-30, RF-PRD-31, RF-PRD-32, RF-PRD-33 | §1 `ordenes.py` · §3 `transicion` · §4 registrar envasado (cierre) · §7 |
| RF-PRD-34 | §1 `reportes.py` · §5 `/reporte` · §7 `test_reporte.py` |

## 9. Dependencias de dudas abiertas

- **Q12 (costeo del granel por lote / costo indirecto):** cambiaría `calcular_envasado` y `TerminarOP`.

- **Wireframes de OP y envasado:** necesarios antes de implementar §5.
