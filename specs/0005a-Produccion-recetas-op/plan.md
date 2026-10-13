# Plan 0005a — Producción: órdenes de producción

Estado: implementado (2026-10-12; aprobado por el PO: "dale"), para la spec consolidada aprobada el 2026-10-12 ("procede")

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto nuevo: `src/production` (app `production`), con las mismas capas que compras. Usa la fachada del catálogo (`CatalogoQuery`: producto, receta), el `InventarioService` (0003a) para consumir componentes e ingresar el producto, y los almacenes del inventario. La OP sigue el patrón de la compra (0004a): estados Creada ▸ En proceso ▸ Finalizada, todo el stock se mueve en una sola transacción al finalizar, con la OP bloqueada (`FOR UPDATE`).

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/production/domain/op.py` | Estados y transiciones; `por_consumir`, `copiar_receta`, `validar_componentes`, `merma`, `costo_unitario`, `validar_finalizacion`, `rendimiento_excedido`, `sugerir_lote` (§3) | RF-PRD-33, 36 a 38, 41, 42, 44, 46, 47, 14, 15 |
| `src/production/domain/errores.py` | `OpInvalida` (con su campo, docs/ux.md §4) | todos los `SI … ENTONCES` |
| `src/production/application/ordenes.py` | `CrearOp`, `EditarOp` (`produccion.op.planificar`); `PasarAEnProceso`, `FinalizarOp` (`produccion.op.ejecutar`); `AnularOp` (`produccion.op.anular`) | RF-PRD-09, 12, 14 a 16, 18, 33, 35 a 38, 41, 44 a 47 |
| `src/production/application/puertos.py` | `UsuariosPort` (usuarios activos con `produccion.op.ejecutar`, para el responsable) | RF-PRD-35 |
| `src/production/infrastructure/models.py`, `repositorios.py`, `contenedor.py`, `apps.py` | `OrdenProduccion`, `OpComponente` (§2); `OrdenesOrm`; registro del contador de OP en curso (0001b, RF-TEN-32) | §2 |
| `src/production/interfaces/` | `/produccion/` (listado), `/produccion/nueva/`, `/produccion/<id>/` (ficha con componentes y pestaña Costos), menú "Producción" | RF-PRD-34, 36 a 39, 48 |
| `src/inventory/application/servicio.py` | `existencias_en_orden(producto, almacén, hoy)` (lectura, en el orden de la estrategia de salida del producto, FEFO o FIFO, sin vencidos; 0002a enmienda 6) para disponibilidad y lote sugerido; `consumido(ids)` (producto, lote, cantidad e importe de los movimientos); las salidas guardan `fecha=hoy` como ya lo hacen las entradas | RF-PRD-09, 39, 41, 46 |
| `src/catalog/application/productos.py` | `GuardarReceta(actor, producto_id, receta)` (`catalogo.producto.gestionar`): valida la receta como `EditarProducto` (ciclos, componentes activos) y registra el historial | RF-PRD-38 |
| `src/inventory/interfaces/templates/inventory/kardex.html` | Enlace de los movimientos `PRODUCCION` a `/produccion/<id>/` | RF-PRD-34 |
| `src/shared/domain/accesos.py`, `src/tenancy/domain/plantillas.py` | Se retiran `produccion.recetas` (`produccion.receta.*`) y `produccion.envasado` (`produccion.envasado.registrar`); la sincronización de `migrate` los borra de la base y de los roles | spec, Impacto |
| `pyproject.toml` | `production` en import-linter (§6) | — |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `production_ordenproduccion` | empresa_id, numero, producto_id (FK catálogo), cantidad `NUMERIC(14,4)`, fecha_programada, almacen_origen_id, almacen_destino_id, responsable_id, comentario, estado (`CREADA`/`EN_PROCESO`/`FINALIZADA`/`ANULADA`), creada_por, creada_en, en_proceso_por, en_proceso_en; al finalizar: fecha_fin, cantidad_producida `NUMERIC(14,4)`, costo_indirecto `NUMERIC(14,2)` (default 0), costo_total `NUMERIC(14,2)`, costo_unitario `NUMERIC(14,6)` null, lote_codigo, motivo_perdida, perdida `NUMERIC(14,2)` (default 0), finalizada_por, finalizada_en; anulada_por, anulada_en, motivo_anulacion | UNIQUE(empresa_id, numero); CHECK cantidad > 0, costo_indirecto ≥ 0; CHECK Finalizada ⇔ fecha_fin y cantidad_producida no nulas; CHECK cantidad_producida = 0 ⇔ motivo_perdida ≠ '' y perdida = costo_total (lote perdido) y, si es > 0, lote_codigo ≠ '' y costo_unitario no nulo; CHECK Anulada ⇔ motivo_anulacion ≠ '' | RF-PRD-15, 16, 36, 41 |
| `production_opcomponente` | empresa_id, op_id, producto_id, por_consumir `NUMERIC(14,4)`, costo_servicio `NUMERIC(14,2)` null (solo servicios); al finalizar: consumido `NUMERIC(14,4)`, lote_codigo, costo `NUMERIC(14,2)` | UNIQUE(op_id, producto_id); CHECK por_consumir ≥ 0, consumido ≥ 0, costo_servicio ≥ 0; trigger: los componentes de una OP Finalizada o Anulada no se cambian ni se borran (como las líneas de compra) | RF-PRD-37, 38, 41, 42, 44 |

Numeración con `SequencePort.siguiente("OP")` → `OP-000001`. Los movimientos llevan `ref_tipo = "OP"` y motivo `PRODUCCION` (salidas de componentes y entrada del producto).

## 3. Funciones puras (`production/domain/op.py`)

| Función | Qué hace | RF |
|---|---|---|
| `transicion(estado, accion)` | Tabla de Definiciones; cualquier otra → `OpInvalida` con el mensaje de la spec ("La OP debe estar en proceso para finalizarla", "La OP está finalizada: corrígela con un ajuste de inventario", "La OP está anulada") | RF-PRD-16, 18, 33, 45 |
| `copiar_receta(receta, cantidad)` | Componentes por consumir = cantidad por unidad × cantidad, half-up a 4 decimales | RF-PRD-37 |
| `validar_componentes(producto_id, componentes, estados)` | Sin el propio producto, sin repetidos, activos, cantidades ≥ 0; servicio con costo ≥ 0 y bien sin costo | RF-PRD-38, 44 |
| `receta_desde_op(componentes, cantidad)` | Por unidad = por consumir / cantidad (4 decimales), solo bienes y servicios con cantidad > 0 | RF-PRD-38 |
| `validar_finalizacion(producida, motivo, componentes, fecha_fin, hoy)` | Al menos un componente; producida ≥ 0; 0 exige motivo ("Indica el motivo del lote perdido"); fecha_fin ≤ hoy | RF-PRD-15, 41, 47 |
| `faltantes(requeridos, disponibles)` | Por componente bien: max(0, requerido − disponible); mensaje "Stock insuficiente: <SKU> faltan <n>; …" con todos | RF-PRD-09 |
| `costo_unitario(componentes, servicios, indirecto, producida)` | (Σ + indirecto) / producida, half-up a 6 decimales; None si producida = 0 | RF-PRD-41 |
| `merma(por_consumir, consumido)` | consumido − por_consumir, 4 decimales | RF-PRD-42 |
| `rendimiento(programada, producida)` y `excede(…)` | % con 2 decimales; advertencia si > 100 % | RF-PRD-14, 34 |
| `sugerir_lote(lotes_por_componente, sku, correlativo)` | Si exactamente un componente consume exactamente un lote, ese código; si no, `<SKU>-<correlativo de 4 dígitos>` | RF-PRD-46 |

## 4. Algoritmos clave

```
CrearOp / EditarOp(actor, cmd):                         # sin stock (RF-PRD-36 a 38)
  producto activo, bien, se fabrica; almacenes activos; responsable con produccion.op.ejecutar
  crear: si cmd.receta → copiar_receta(catálogo.receta(producto), cantidad)
         numero = SequencePort.siguiente("OP"); estado CREADA
  editar: transicion(estado, "editar") (Creada o En proceso); validar_componentes; reemplaza la lista

FinalizarOp(actor, op_id, cmd, hoy):                    # RF-PRD-41, 46, 09, 12, 14, 15, 47
  en una transacción, con la OP bloqueada (FOR UPDATE):   # la segunda espera y ve FINALIZADA
    transicion(estado, "finalizar")                     # solo desde EN_PROCESO
    producto activo y se fabrica; validar_finalizacion(...)
    disponibles = InventarioService.existencias_en_orden(...) por componente bien y lote indicado
    faltantes(...) → OpInvalida con todos, sin mover nada
    ids = InventarioService.registrar_salida("PRODUCCION", "OP", op_id, bienes con su lote o, si no, según la estrategia del producto, hoy=fecha_fin)
    consumido = InventarioService.consumido(ids)         # importe y lote de cada salida
    total = Σ importes + Σ costo de servicios + indirecto
    si producida > 0:
        lote = cmd.lote or sugerir_lote(lotes de consumido, sku, correlativo del producto)
        InventarioService.registrar_entrada("PRODUCCION", "OP", op_id,
            [Linea(producto, destino, producida, costo_unitario(...), lote, cmd.vencimiento)], hoy=fecha_fin)
    si no: perdida = total                              # lote perdido, para 0008b
    guarda consumido, lote y costo por componente; estado FINALIZADA
    advertencia si rendimiento > 100 %
```

El diálogo de "Finalizar" muestra el lote sugerido con el mismo `sugerir_lote` sobre la vista previa de esa estrategia (`existencias_en_orden`), y el vencimiento sugerido = fecha de fin + vida útil (lo resuelve `registrar_entrada` si no se indica).

## 5. Interfaz

Patrón de la compra (docs/ux.md: barra de acciones abajo, "Más acciones" con Anular al final y en rojo, confirmaciones que explican qué ocurre; grilla estándar §5). Pensada para tablet (RNF-PRD-02: 768 px sin scroll horizontal).

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/produccion/` | Listado: número, producto, cantidad programada y producida, fecha programada, responsable, estado; filtros por estado, producto, fechas y número | RF-PRD-48 |
| `/produccion/nueva/` | Producto (bienes que se fabrican), cantidad, fecha programada, almacenes, responsable, comentario y "Usar su receta" (marcado si el producto la tiene) | RF-PRD-35 a 37 |
| `/produccion/<id>/` (Creada o En proceso) | Barra **Creada ▸ En proceso ▸ Finalizada**; cabecera editable; pestaña Componentes con líneas dinámicas (`<template>` y script corto, como compras): producto, por consumir, unidad, disponibilidad (Disponible / No disponible; nada en servicios) y costo en servicios; "Guardar como receta del producto" solo con `catalogo.producto.gestionar`. Acción principal: "Pasar a en proceso" o "Finalizar" (diálogo: consumido real por componente, lote por componente con el lote sugerido por la estrategia del producto, cantidad producida, fecha de fin `max=hoy`, costo indirecto, lote y vencimiento del producto, motivo si la cantidad es 0) | RF-PRD-38, 39, 41, 44 a 46 |
| `/produccion/<id>/` (Finalizada o Anulada) | Solo lectura; pestaña Costos con `produccion.reporte.ver` (importes solo con `inventario.costo.ver`); movimientos de kardex de la OP; quién y cuándo en cada paso | RF-PRD-16, 34, 42 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Contexto nuevo `production`; su aplicación usa solo `catalog.application` (fachada y `GuardarReceta`) e `inventory.application.servicio` (contrato de import-linter como el de compras); nadie depende de producción | Producción dentro del inventario | Mismo patrón que compras; el inventario y el catálogo no conocen a producción |
| Validar faltantes de todos los componentes antes de mover stock | Dejar que `registrar_salida` falle en el primero | RF-PRD-09 pide indicar cada faltante; la transacción igual protege si cambia entre la lectura y la salida |
| El costo se toma de los movimientos (`InventarioService.consumido`) | Recalcular promedio × cantidad en producción | Un solo cálculo del costo de salida (art. 4.3), aunque la salida se reparta entre lotes |
| Lote perdido: la pérdida queda en la OP (`perdida`), sin movimiento aparte | Un ajuste MERMA automático | Las salidas ya están en el kardex con su costo; 0008b lee la pérdida de las OP finalizadas con 0 |
| "Guardar como receta" llama a `GuardarReceta` del catálogo desde la vista | Escribir la receta desde producción | La receta es del catálogo (0002a): su validación y su historial viven allí |
| Se retiran `produccion.recetas` y `produccion.envasado` del catálogo de accesos | Dejarlos sin uso | Art. 7.6; la sincronización de `migrate` (0001b) ya borra lo que sale del catálogo |
| La OP en curso cuenta para el aviso de 0001b (RF-TEN-32): `contadores.registrar` en `apps.py` | — | Lo esperaba 0001b ("falso hasta 0005") |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/production tests/acceptance -k "E05a"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/production/unit/test_op.py` | Transiciones, copia de receta, componentes inválidos, receta desde la OP, finalización (0 con y sin motivo, fecha futura), faltantes, costo unitario y merma con el ejemplo de la spec, lote sugerido | RF-PRD-14, 15, 33, 37, 38, 41, 42, 44, 46, 47 |
| Caso de uso | `tests/production/usecases/test_ordenes.py` | Crear con y sin receta, editar sin stock, responsable, en proceso, finalizar (salidas, entrada al costo, lote nuevo y heredado, servicios, indirecto), faltantes sin movimientos, lote perdido, anular, permisos | RF-PRD-09, 15, 16, 18, 35 a 38, 41, 44 a 47 |
| Integración | `tests/production/integration/test_concurrencia.py` | Dos finalizaciones simultáneas con dos hilos: un solo consumo | RF-PRD-12 |
| Integración | `tests/production/integration/test_reconciliacion.py` | OP encadenadas (granel → envasado) con semillas: el kardex reproduce stock y valor (art. 4.6) | criterios de finalización |
| Integración | `tests/production/integration/test_pantallas.py` | Listado y filtros, ficha, disponibilidad, diálogo de finalizar, costos ocultos, aislamiento (rutas en `tests/meta/test_aislamiento.py`) | RF-PRD-34, 39, 48 |
| Caso de uso | `tests/catalog/usecases/test_receta.py` | `GuardarReceta` (permiso, ciclos, historial) | RF-PRD-38 |
| Aceptación | `features/ordenes_produccion.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-PRD-35, 36, 37, 38, 44, 45 | §1 `ordenes.py` · §3 `copiar_receta`, `validar_componentes`, `receta_desde_op` · §5 · §7 |
| RF-PRD-39 | §1 `existencias_en_orden` · §5 ficha · §7 pantallas |
| RF-PRD-09, 12, 14, 15, 41, 42, 46, 47 | §3 · §4 `FinalizarOp` · §6 · §7 |
| RF-PRD-16, 18, 33 | §3 `transicion` · §7 |
| RF-PRD-34, 48 | §5 · §7 pantallas |

## 9. Dependencias de dudas abiertas

- **Contador (Q12):** costo indirecto manual y tratamiento de la pérdida de producción. No cambian el modelo: si el contador lo pide, el costo indirecto se puede ocultar y la pérdida se clasifica en 0008b.

## Enmienda 1: varios productos de salida (implementada, 2026-10-12)

| Parte | Cambio | RF |
|---|---|---|
| Modelo | Tabla nueva `production_opsalida` (op, producto, cantidad, factor `NUMERIC(10,4)` > 0, producida, lote_codigo, costo_total, costo_unitario; UNIQUE(op, producto)). `OpComponente.salida` (FK a la salida, nula = común), con UNIQUE(op, producto, salida) `NULLS NOT DISTINCT`. Se retiran de la OP `producto`, `cantidad`, `cantidad_producida`, `costo_unitario` y `lote_codigo`; la migración pasa cada OP existente a una salida (factor 1) y asigna sus componentes a ella. El CHECK de la OP finalizada pasa a la salida (producida > 0 ⇒ lote y costo unitario) | RF-PRD-49, 51 |
| Dominio | `repartir(salidas, directos, comunes, indirecto)`: costo por salida por producida × factor, directos de salidas con 0 a comunes, ajuste del redondeo en la última; `factor_sugerido(litros)`; `sugerir_lote` por salida | RF-PRD-52 |
| Casos de uso | `DatosOp.salidas` (producto, cantidad, factor) y `Componente.salida`; `CrearOp` copia la receta de cada salida; `FinalizarOp` recibe producida y lote por salida, una sola salida de componentes y una entrada por salida | RF-PRD-49 a 52 |
| Pantallas | Ficha: tabla "Productos de salida" (producto, cantidad, factor) y columna "Para" en componentes (salida o "Común"); diálogo de finalizar con producida y lote por salida; Costos por salida; listado con los productos | RF-PRD-53 |
| Decisión | El factor reparte solo lo común y el indirecto; lo asignado es costo directo | Repartir todo por factor | Los materiales de cada presentación (botella, barril) no deben cargarse a las otras |
| Tests | Unitario de `repartir` con el ejemplo de la spec (1.893080 y 43.500000), redondeo y salida con 0; caso de uso del envasado en dos presentaciones; migración de una OP existente; escenario nuevo | RF-PRD-49 a 53 |

