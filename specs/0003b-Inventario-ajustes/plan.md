# Plan 0003b — Inventario: ajustes

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/inventory`. Es el núcleo transaccional: compras, producción y ventas **solo** cambian stock a través de su fachada `InventarioService` (constitución art. 4). Requiere: 0003a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/inventory/domain/ajuste.py` | Agregado `Ajuste`: tipos, costo por tipo, diferencia del conteo, transferencia, anulación | RF-INV-08 a 13, 25 |
| `src/inventory/domain/errores.py` | `StockInsuficiente`, `LoteVencido`, `AnulacionConConsumoPosterior`, `CostoRequerido`, `SaldoInicialNoPermitido`… | todos los `SI … ENTONCES` |
| `src/inventory/application/ajustes.py` | `RegistrarAjuste`, `AnularAjuste` | RF-INV-08 a 13 |
| `src/inventory/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios con locks en el orden de 0000 §5 | §2 |
| `src/inventory/interfaces/views/*.py` + `templates/inventory/*.html` | Pantallas de §5 | RF-INV-08 a 13 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `inventory_lote` | empresa_id, producto_id, codigo, fecha_produccion, fecha_vencimiento null, origen_tipo, origen_id | UNIQUE(empresa_id, producto_id, codigo) | RF-INV-10 |
| `inventory_ajuste` | empresa_id, numero, tipo (`SALDO_INICIAL`/`CONTEO`/`MERMA`/`CORRECCION`/`TRANSFERENCIA`), motivo, almacen_id, almacen_destino_id null, estado, anulado_por, anulado_en, motivo_anulacion | UNIQUE(empresa_id, numero) | RF-INV-08 a 13 |
| `inventory_ajuste_linea` | ajuste_id, producto_id, lote_id, cantidad_sistema, cantidad_contada null, diferencia, costo_unitario null | — | RF-INV-08 a 11 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `diferencia_conteo(sistema, contado) -> Decimal` | `contado − sistema`; 0 ⇒ sin movimiento | RF-INV-11 |
| `costo_de_entrada_ajuste(tipo, costo_ingresado, promedio, nunca_tuvo_costo)` | Aplica la tabla de costos por tipo; exige costo si nunca tuvo costo | RF-INV-08, 25 |
| `validar_saldo_inicial(costo, tiene_movimientos)` | Costo > 0 y producto sin movimientos | RF-INV-09 |
| `inversos_de(movimientos) -> list` | Movimientos opuestos al costo original; en transferencia, ambos | RF-INV-13 |

## 4. Algoritmos clave

Sin algoritmos no triviales: la lógica está en las funciones puras de §3.

## 5. Interfaz

**Referencia visual del PO (2026-10-10):** "Ajustes de stock" en dos tarjetas: a la izquierda "Nuevo ajuste" (producto con su stock actual, tipo de ajuste —p. ej. fijar stock exacto por conteo físico—, cantidad y motivo; botón "Aplicar ajuste"); a la derecha "Últimos ajustes" (fecha, producto, motivo, antes, después).

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/inventario/ajustes/nuevo` | Formulario por tipo: costo obligatorio en saldo inicial; cantidad contada en conteo; almacén destino en transferencia; lote si aplica | RF-INV-08 a 12, 25 |
| `/inventario/ajustes/<id>` | Detalle y botón "Anular" (con motivo) | RF-INV-13 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Transferencia como un solo ajuste | Dos ajustes de corrección | Atómica, al mismo costo, sin efecto en resultados |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/inventory tests/acceptance -k "E03b"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/inventory/unit/test_ajuste.py` | Costos por tipo, conteo 0, saldo inicial con movimientos, costo requerido | RF-INV-08 a 11, 25 |
| Caso de uso | `tests/inventory/usecases/test_ajustes.py` | Transferencia atómica; anular conteo y transferencia | RF-INV-12, 13 |
| Aceptación | `features/ajustes_lotes_alertas.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-INV-08, RF-INV-09, RF-INV-10, RF-INV-11, RF-INV-12, RF-INV-13, RF-INV-25 | §1 `ajuste.py`, `ajustes.py` · §3 `costo_de_entrada_ajuste`, `validar_saldo_inicial`, `diferencia_conteo`, `inversos_de` · §5 ajustes · §7 |

## 9. Dependencias de dudas abiertas

- **Q12 (sustento de mermas):** si exige documentos, `inventory_ajuste` agrega adjuntos.
