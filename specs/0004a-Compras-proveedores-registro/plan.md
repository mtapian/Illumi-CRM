# Plan 0004a — Compras: registro de compras

> Los proveedores (`purchasing_proveedor`, `/compras/proveedores/`) los implementó 0002d; aquí se usan. 0004a implementa `ComprasPort.tiene_compras()` de 0002d.

Estado: implementado (aprobado por el PO el 2026-10-11)

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/purchasing`. Usa la fachada del catálogo (`CatalogoQuery`) para validar productos, el IGV vigente de tenancy (`tenancy_service().igv_vigente`) y el `InventarioService` (0003a) para las entradas. La anulación es de 0004b (sin efecto en stock si la compra no está Finalizada).

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/purchasing/domain/compra.py` | `LineaCompra`, `validar_linea`, `separa_igv`, `totales`, `validar_documento_compra`, `validar_guia` | RF-COM-04, 05, 08, 09, 20 |
| `src/purchasing/domain/errores.py` | Se agrega `CompraInvalida` (con los mensajes de la spec) | todos los `SI … ENTONCES` |
| `src/purchasing/application/compras.py` | `CrearCompra`, `EditarCompra`, `PasarAEnProceso` y `FinalizarCompra` (`compras.compra.registrar`). Crear y editar validan la compra y no mueven stock; finalizar vuelve a validar, cambia el estado y llama a `InventarioService.registrar_entrada` con `ref_tipo = COMPRA` y la fecha de recepción como fecha del movimiento y del ingreso del lote (la fecha de compra es solo referencia), en una transacción con la compra bloqueada (`FOR UPDATE`) | RF-COM-04 a 12, 19, 20, 23, 25, 26 |
| `src/purchasing/application/puertos.py` | Puerto `IgvPort` (el IGV vigente a una fecha) para no depender de tenancy | RF-COM-08 |
| `src/purchasing/infrastructure/models.py`, `repositorios.py` | `Compra` y `CompraLinea`; `ComprasOrm.tiene_compras` reemplaza al `SinCompras` de 0002d | §2, RF-COM-24 |
| `src/purchasing/interfaces/` | `/compras/` (listado), `/compras/nueva/` (líneas dinámicas), `/compras/<id>/` (detalle) | RF-COM-04, 14 |
| `src/inventory/interfaces/templates/inventory/kardex.html` | Enlace de la entrada `COMPRA` a `/compras/<id>/` | RF-COM-14 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `purchasing_compra` | empresa_id, numero, proveedor_id, fecha `DATE`, almacen_id, doc_tipo, doc_serie_numero, igv_pct (vigente a la fecha), subtotal, igv, total, estado (`CREADA`/`EN_PROCESO`/`FINALIZADA`/`ANULADA`), fecha_recepcion `DATE` y guia_remision (opcional), ambas al finalizar, observacion, usuario_id, creada_en, finalizada_por, finalizada_en (anulado_por, anulado_en y motivo_anulacion los agrega 0004b) | UNIQUE(empresa_id, numero); índice único parcial (empresa, proveedor, doc_tipo, doc_serie_numero) entre compras no anuladas salvo `SIN_DOCUMENTO`; CHECK total = subtotal + igv | RF-COM-04, 11, 13, 25, 26 |
| `purchasing_compra_linea` | compra_id, producto_id, cantidad, costo_unitario `NUMERIC(14,6)`, es_bonificacion, subtotal, lote_codigo, vencimiento null | `CHECK cantidad > 0`; `CHECK costo_unitario > 0 OR (es_bonificacion AND costo_unitario = 0)`; trigger que rechaza cambiar o borrar líneas de una compra Finalizada o Anulada | RF-COM-04, 06, 13, 25 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `validar_linea(cantidad, costo, bonificacion)` | Cantidad > 0; costo ≥ 0; costo 0 solo con bonificación (y bonificación con costo 0) | RF-COM-04 |
| `separa_igv(doc_tipo) -> bool` | Solo `FACTURA` | RF-COM-08 |
| `totales(lineas, doc_tipo, igv_pct) -> (subtotal, igv, total)` | Subtotal e IGV por línea con half-up a 2 decimales; total = subtotal + IGV | RF-COM-08, 09 |
| `validar_documento_compra(doc_tipo, serie_numero, tipo_doc_proveedor)` | Tipo válido; serie-número obligatorio salvo `SIN_DOCUMENTO`; `FACTURA` exige proveedor con RUC | RF-COM-20 |
| `validar_guia(guia)` | vacía o `^[A-Z0-9]{4}-\d{1,8}$` (en mayúsculas) | RF-COM-27 |

El lote (crear, sumar, otro vencimiento, vencimiento sugerido) ya lo resuelve el `InventarioService` (RF-INV-26): no se duplica aquí.

## 4. Algoritmos clave

```
CrearCompra / EditarCompra(actor, cmd):             # Creada o En proceso; sin stock (RF-COM-25)
  proveedor activo; validar_documento_compra; por línea: bien comprable; validar_linea
  igv_pct = IgvPort.vigente(cmd.fecha); totales(…)
  crear: numero = SequencePort.siguiente('COMPRA') → estado CREADA
  editar: solo si no está Finalizada ni Anulada; reemplaza las líneas

FinalizarCompra(actor, compra_id, almacen_id, recepcion, guia, hoy):  # RF-COM-26, 27
  en una transacción, con la compra bloqueada:
     si ya está Finalizada o Anulada → "La compra ya está finalizada" / "…anulada"
     si está Creada → "Pasa la compra a en proceso antes de finalizarla"   # RF-COM-30
     recepcion ≤ hoy, si no → "La fecha de recepción no puede ser futura"
     validar_guia(guia) si viene; almacén activo
     repetir las validaciones de Crear (proveedor, productos, documento duplicado)
     estado = FINALIZADA; almacen_id, fecha_recepcion, guia_remision = los confirmados
     InventarioService.registrar_entrada('COMPRA', 'COMPRA', compra_id, líneas con costo y lote, usuario, hoy=recepcion)
```

El costo de inventario de cada línea es su costo unitario (sin IGV con factura, el total pagado por unidad con otro documento; RF-COM-08); la bonificación entra a costo 0.

## 5. Interfaz

**Referencia visual del PO (2026-10-10):** "Nueva compra" en una tarjeta: proveedor y fecha en dos columnas, observación, filas de productos que se agregan con "+ Agregar" (producto, cantidad, costo, subtotal) y totales a la derecha (subtotal, IGV, total); "Registrar compra" (verde) y "Cancelar".

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/compras/<id>/` (Creada o En proceso) | La misma pantalla en edición, con la barra de estados **Creada ▸ En proceso ▸ Finalizada** (patrón de Odoo de la captura del PO) y los botones "Guardar", "Pasar a en proceso", "Finalizar" (abre la confirmación de recepción en un `<dialog>`: almacén de ingreso con el de la compra preseleccionado, fecha de recepción sugerida hoy con `<input type="date" max=hoy>` y guía de remisión opcional) y "Anular" (0004b) | RF-COM-25, 26, 27 |
| `/compras/nueva/` | Cabecera (proveedor activo, fecha, almacén, documento y serie-número, observación) + líneas dinámicas como en ajustes (`<template>` y un script corto, sin límite): producto, cantidad, costo unitario, bonificación, lote y vencimiento opcionales; totales en vivo informativos (el servidor recalcula); si se rechaza, las líneas vuelven | RF-COM-04 a 12, 19, 20, 23 |
| `/compras/` | Listado con filtros por proveedor, fechas, estado y número | RF-COM-14 |
| `/compras/<id>/` (Finalizada o Anulada) | Detalle de solo lectura con la barra de estados y sus movimientos de kardex (ruta en la prueba de aislamiento) | RF-COM-13, 14 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Estados Creada ▸ En proceso ▸ Finalizada; el stock entra al finalizar (PO, 2026-10-11) | Registrar y mover stock en un solo paso | La compra se arma y se ajusta hasta recibir la mercadería; una compra Finalizada es inmutable (art. 4.5) y se corrige anulándola (0004b) |
| Validar al crear y otra vez al finalizar | Validar solo al finalizar | El usuario ve los errores mientras arma la compra; al finalizar el catálogo o el proveedor pudieron cambiar |
| Costo 0 solo con bonificación marcada | Permitir cualquier costo ≥ 0 | Evita errores de digitación que bajan el promedio sin motivo |
| El IGV lo calcula el sistema | Ingresar el IGV del documento | Simplicidad en el MVP (propuesta al PO) |
| La fecha de la compra es referencia; al finalizar se pide la fecha de recepción (≤ hoy), que es la fecha del movimiento y del ingreso del lote (PO, 2026-10-11). El kardex sigue ordenado por registro y el costo no se recalcula | Rechazar fechas futuras de compra; usar la fecha del documento o la hora de finalización en el kardex | Refleja cuándo entró la mercadería sin reordenar el kardex ni recalcular costos (art. 4.3) |
| `InventarioService.registrar_entrada` usa `hoy` también como fecha del movimiento (`Movimiento.fecha` pasa de `auto_now_add` a `default=now`; con `hoy` distinto de la fecha actual, se guarda `hoy` a la hora actual de Lima) | Un campo nuevo de fecha de negocio en el movimiento | Un solo campo; los filtros por fecha del kardex ya funcionan sobre él |
| IGV por un puerto (`IgvPort`) | Importar tenancy desde la aplicación | Contratos de import-linter: la aplicación de compras usa otros contextos solo por puertos o fachadas |
| La aplicación de compras usa `inventory.application.servicio` (el `InventarioService` es la fachada del inventario); import-linter le prohíbe el dominio, la infraestructura y la interfaz del inventario, y el inventario sigue sin conocer compras | Un puerto propio de compras que el inventario llene | Mismo patrón que tendrán producción y ventas; sin ciclos (2026-10-11, al implementar) |
| "Pasar a en proceso" guarda lo editado antes de cambiar el estado; "Finalizar" finaliza lo guardado | Finalizar también lo no guardado | La recepción confirma lo que quedó registrado |
| Líneas dinámicas con `<template>` y script corto | HTMX | Mismo criterio que ajustes (PO, 2026-10-10) |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/purchasing tests/acceptance -k "E04a"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/purchasing/unit/test_compra.py` | Líneas, bonificación, documento, factura con DNI, totales factura vs. boleta y redondeo | RF-COM-04, 08, 09, 20 |
| Caso de uso | `tests/purchasing/usecases/test_compras.py` | Crear y editar sin stock, pasar a en proceso, finalizar con entrada al costo, no finalizar dos veces, revalidación al finalizar, comprables, proveedor desactivado, documento duplicado, numeración, lote, `tiene_compras` | RF-COM-04 a 07, 10, 11, 19, 23 a 26 |
| Integración | `tests/purchasing/integration/test_compras_pantallas.py` | Nueva compra con líneas dinámicas, listado con filtros, detalle, permisos, aislamiento, enlace desde el kardex | RF-COM-13, 14 |
| Aceptación | `features/compras.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-COM-04, 05, 06, 07, 19, 23 | §1 `compra.py`, `compras.py` · §3 `validar_linea` · §4 · §5 `/compras/nueva/` · §7 |
| RF-COM-08, 09, 20 | §3 `separa_igv`, `totales`, `validar_documento_compra` · §7 `test_compra.py` |
| RF-COM-10, 11, 12, 13, 14, 24, 25, 26, 27 | §1 `compras.py`, `repositorios.py` · §2 índice único parcial y trigger · §6 fecha de referencia · §5 · §7 |

## 9. Dependencias de dudas abiertas

- **Q12 (fecha del kardex):** resuelto por el PO (fecha de recepción, RF-COM-27); falta el visto bueno del contador.
- **0002e (impuestos):** al aprobarse, el IGV de cada línea sale de los impuestos de compra del producto (un insumo exonerado no lleva IGV).
