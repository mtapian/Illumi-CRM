# Plan 0003b — Inventario: ajustes

Estado: implementado (2026-10-10; alineado con 0003a)

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/inventory`. Es el núcleo transaccional: compras, producción y ventas **solo** cambian stock a través de su fachada `InventarioService` (constitución art. 4). Requiere: 0003a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/inventory/domain/ajuste.py` | Tipos, costo por tipo, diferencia del conteo, validaciones del ajuste (motivo, saldo inicial, transferencia) | RF-INV-08 a 12, 27 |
| `src/inventory/domain/errores.py` | Se agrega `AjusteInvalido` (motivo, saldo inicial, transferencia, ya anulado); se reusan `CostoRequerido` y los de 0003a | todos los `SI … ENTONCES` |
| `src/inventory/domain/lotes.py` | `validar_salida_de_lote` acepta `CONTEO` y `TRANSFERENCIA` además de `MERMA` | RF-INV-29 |
| `src/inventory/application/servicio.py` | Se agrega `transferir(lineas, origen, destino)`: mueve stock y registra salida + entrada con el mismo `costo_total`, sin tocar `costo_producto`; `revertir` reconoce el par y lo revierte igual. El motivo de los inversos pasa a `ANULACION` | RF-INV-12, 13 |
| `src/inventory/application/ajustes.py` | `RegistrarAjuste` y `AnularAjuste` (casos de uso con permiso): numeran con `SequencePort` y llaman al `InventarioService` con `ref_tipo = AJUSTE` | RF-INV-08 a 13, 28 |
| `src/inventory/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios con locks en el orden de 0000 §5 | §2 |
| `src/inventory/interfaces/views/*.py` + `templates/inventory/*.html` | Pantallas de §5 | RF-INV-08 a 13 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `inventory_ajuste` | empresa_id, numero, fecha, tipo (`SALDO_INICIAL`/`CONTEO`/`MERMA`/`CORRECCION`/`TRANSFERENCIA`), motivo, almacen_id, almacen_destino_id null, estado (`REGISTRADO`/`ANULADO`), usuario_id, anulado_por, anulado_en, motivo_anulacion | UNIQUE(empresa_id, numero); CHECK destino solo y distinto en `TRANSFERENCIA`; CHECK motivo no vacío; el lote se usa de 0003a | RF-INV-08 a 13 |
| `inventory_ajuste_linea` | ajuste_id, producto_id, lote_codigo, vencimiento null, sentido (`ENTRADA`/`SALIDA`, en `CORRECCION`), cantidad (en `CONTEO`, lo contado), cantidad_sistema null (solo `CONTEO`; diferencia = cantidad − sistema), costo_unitario null | CHECK cantidad ≥ 0; trigger de inmutabilidad; la línea guarda lo pedido y los movimientos (ref `AJUSTE`, id del ajuste) lo aplicado | RF-INV-08 a 11 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `diferencia_conteo(sistema, contado) -> Decimal` | `contado − sistema`; 0 ⇒ sin movimiento | RF-INV-11 |
| `costo_de_entrada_ajuste(tipo, costo_ingresado, promedio, nunca_tuvo_costo)` | Aplica la tabla de costos por tipo; exige costo si nunca tuvo costo | RF-INV-08, 25 |
| `validar_saldo_inicial(costo, tiene_movimientos)` | Costo > 0 y producto sin movimientos | RF-INV-09 |
| `validar_ajuste(tipo, motivo, origen, destino)` | Motivo obligatorio; destino solo en transferencia y distinto del origen | RF-INV-08, 12 |
| (reusa `inversos_de` de 0003a) | Movimientos opuestos al costo original | RF-INV-13 |

## 4. Algoritmos clave

Sin algoritmos no triviales: la lógica está en las funciones puras de §3.

## 5. Interfaz

**Referencia visual del PO (2026-10-10):** "Ajustes de stock" en dos tarjetas: a la izquierda "Nuevo ajuste" (producto con su stock actual, tipo de ajuste —p. ej. fijar stock exacto por conteo físico—, cantidad y motivo; botón "Aplicar ajuste"); a la derecha "Últimos ajustes" (fecha, producto, motivo, antes, después).

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/inventario/ajustes/` (menú "Ajustes de stock") | "Nuevo ajuste" y "Últimos ajustes" en dos tarjetas (referencia visual); formulario por tipo: costo obligatorio en saldo inicial; cantidad contada en conteo (muestra el stock del sistema); almacén destino en transferencia; lote opcional | RF-INV-08 a 12, 27 |
| `/inventario/ajustes/<id>/` | Detalle (líneas y movimientos) y botón "Anular" con motivo; ruta agregada a la prueba de aislamiento | RF-INV-13 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Transferencia como un solo ajuste | Dos ajustes de corrección | Atómica, al mismo costo, sin efecto en resultados |
| `transferir` no toca `costo_producto` | Salida al promedio + entrada a ese costo | El costo es por producto: mover entre almacenes no cambia el total; así una transferencia que vacía el origen tampoco altera el promedio por redondeo |
| Sin pantalla HTMX de líneas dinámicas en el MVP | Líneas dinámicas | Un formulario con hasta 10 líneas fijas cubre los conteos del piloto; HTMX cuando haga falta (art. 7.6) |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/inventory tests/acceptance -k "E03b"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/inventory/unit/test_ajuste.py` | Costos por tipo, conteo 0, saldo inicial con movimientos, costo requerido, motivo, transferencia al mismo almacén, lote vencido en conteo y transferencia | RF-INV-08 a 12, 27, 29 |
| Caso de uso | `tests/inventory/usecases/test_ajustes.py` | Transferencia atómica y sin cambio de costo; anular merma, conteo y transferencia; no anular dos veces; numeración | RF-INV-12, 13, 28 |
| Integración | `tests/inventory/integration/test_pantallas.py` | Pantalla de ajustes, permisos, detalle de otra empresa da 404 | RF-INV-08, 13 |
| Aceptación | `features/ajustes_lotes_alertas.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-INV-08 a 13, 27 a 29 | §1 `ajuste.py`, `ajustes.py`, `servicio.transferir`, `lotes.py` · §3 `costo_de_entrada_ajuste`, `validar_saldo_inicial`, `diferencia_conteo`, `validar_ajuste` · §5 ajustes · §7 |

## 9. Dependencias de dudas abiertas

- **Q12 (sustento de mermas):** MVP solo con motivo (propuesta al PO). Si el contador exige documentos, `inventory_ajuste` agrega adjuntos con una enmienda.
- **"Mermas y ajustes" del estado de resultados (RF-FIN-09):** lo construye 0008b; el escenario de transferencia deja ese paso como parcial con motivo.
