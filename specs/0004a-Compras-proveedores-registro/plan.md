# Plan 0004a — Compras: proveedores y registro de compras

> Los proveedores (`purchasing_proveedor`, `/compras/proveedores/`) se implementan en la spec 0002d; aquí se usan. 0004a implementa `ComprasPort.tiene_compras()` de 0002d.

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/purchasing`. Usa `CatalogoQuery` (épica 0002) para validar productos e `InventarioService` (épica 0003) para las entradas y su reversión. Requiere: 0002a, 0003a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/purchasing/domain/compra.py` | Agregado `Compra`: líneas, IGV según documento, totales, bonificación, lotes | RF-COM-04 a 09, 19, 20 |
| `src/purchasing/domain/documento.py` | Tipos de documento y si separan IGV | RF-COM-08, 20 |
| `src/purchasing/domain/errores.py` | `ProductoNoComprable`, `LoteRequerido`, `LoteConOtroVencimiento`, `DocumentoDuplicado`, `FechaFutura`, `FacturaRequiereRuc`, `CostoCeroSinBonificacion` | todos los `SI … ENTONCES` |
| `src/purchasing/application/compras.py` | `RegistrarCompra`, `AnularCompra`, `ComprasQuery` | RF-COM-04 a 14 |
| `src/purchasing/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/purchasing/interfaces/views/*.py` + `templates/purchasing/*.html` | Pantallas de §5 | RF-COM-04 a 14 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `purchasing_compra` | empresa_id, numero, proveedor_id, fecha `DATE`, almacen_id, doc_tipo, doc_serie_numero, igv_pct (vigente a la fecha), subtotal, igv, total, estado (`REGISTRADA`/`ANULADA`), observacion, created_by, anulado_por, anulado_en, motivo_anulacion | UNIQUE(empresa_id, numero); índice único parcial del documento entre compras activas (excepto `SIN_DOCUMENTO`) | RF-COM-04, 11, 13 |
| `purchasing_compra_linea` | compra_id, producto_id, cantidad, costo_unitario `NUMERIC(14,6)`, es_bonificacion, subtotal, lote_id null | `CHECK cantidad > 0`; `CHECK costo_unitario > 0 OR es_bonificacion` | RF-COM-04, 06, 07 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `es_comprable(tipo) -> bool` | `INSUMO`, `ENVASE`, `MERCADERIA` | RF-COM-05 |
| `validar_linea(linea, producto)` | Cantidad > 0; costo > 0 o bonificación; lote y vencimiento si el producto controla lote | RF-COM-04, 06 |
| `vencimiento_sugerido(fecha_compra, vida_util) -> date` | Fecha de compra + vida útil | RF-COM-06 |
| `resolver_lote(lote_existente, vencimiento) -> accion` | Sumar si coincide el vencimiento; crear si no existe; error si difiere | RF-COM-07, 19 |
| `separa_igv(doc_tipo) -> bool` | Solo `FACTURA` | RF-COM-08 |
| `totales(lineas, doc_tipo, igv_pct) -> (subtotal, igv, total)` | Redondeo *half-up* a 2 decimales por línea y en total | RF-COM-08, 09 |
| `validar_documento(doc_tipo, proveedor)` | `FACTURA` exige proveedor con RUC | RF-COM-20 |
| `validar_fecha(fecha, hoy)` | `fecha ≤ hoy` (hora de Lima) | RF-COM-12 |

## 4. Algoritmos clave

**Registrar compra** (RF-COM-04 a 12, 19, 20):

```
RegistrarCompra(cmd):
  actor.exige(compras.compra.registrar)
  validar_fecha(cmd.fecha, hoy); validar_documento(cmd.doc_tipo, proveedor)
  por línea: producto = CatalogoQuery.producto(id); si not es_comprable → ProductoNoComprable
             validar_linea(…); accion_lote = resolver_lote(…)
  si documento activo duplicado → DocumentoDuplicado                         # RF-COM-11
  igv_pct = TenancyService.igv_vigente(cmd.fecha)
  en una transacción:
     numero = SequencePort.siguiente('COMPRA', 'C')
     guardar compra con totales(…)
     InventarioService.registrar_entrada(motivo=COMPRA, ref=compra, líneas con costo y lote)   # RF-COM-10
```

## 5. Interfaz

**Referencia visual del PO (2026-10-10):** "Nueva compra" en una tarjeta: proveedor y fecha en dos columnas, observación (n.º de factura, guía), selector de producto con "+ Agregar" que suma filas (código, producto, cantidad, precio de compra, subtotal) y totales a la derecha (subtotal, IGV, total); botones "Registrar compra" (verde) y "Cancelar". Se adapta a los campos de esta spec (lote, vencimiento, bonificación).

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/compras/nueva` | Cabecera + tabla de líneas (HTMX): casilla "bonificación", columnas de lote y vencimiento solo para productos con lote (vencimiento sugerido), totales en vivo con o sin IGV según el documento | RF-COM-04 a 12, 19, 20 |
| `/compras/` | Listado con filtros por proveedor, fecha, estado y número | RF-COM-14 |
| `/compras/<id>` | Detalle de solo lectura con enlace a sus movimientos de kardex; botón "Anular" con motivo; mensaje de rechazo con el producto consumido | RF-COM-13, 14 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Compras inmutables: se anulan y se registran de nuevo | Edición de compras | Art. 4.5; el kardex no se reescribe |
| Costo 0 solo con bonificación marcada | Permitir cualquier costo ≥ 0 | Evita errores de digitación que bajan el promedio sin motivo |
| El IGV lo calcula el sistema | Ingresar el IGV del documento | Simplicidad en el MVP; la diferencia de céntimos queda como duda abierta |
| La fecha del movimiento es la del registro | La fecha del documento | El kardex no se reordena hacia atrás; pendiente de confirmar con el contador |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/purchasing tests/acceptance -k "E04a"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/purchasing/unit/test_compra.py` | Comprables, bonificación, lote requerido, lote con otro vencimiento, factura con DNI, fecha futura | RF-COM-04 a 07, 12, 19, 20 |
| Unitario | `tests/purchasing/unit/test_totales.py` | Factura vs. boleta; redondeo por línea y total | RF-COM-08, 09 |
| Caso de uso | `tests/purchasing/usecases/test_registrar.py` | Entrada al costo, documento duplicado, numeración | RF-COM-04, 10, 11 |
| Integración | `tests/purchasing/integration/test_listado.py` | Filtros, inmutabilidad | RF-COM-13, 14 |
| Aceptación | `features/compras.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-COM-04, RF-COM-05, RF-COM-06, RF-COM-07, RF-COM-19 | §1 `compra.py` · §3 `es_comprable`, `validar_linea`, `vencimiento_sugerido`, `resolver_lote` · §4 registrar · §5 `/compras/nueva` · §7 |
| RF-COM-08, RF-COM-09, RF-COM-20 | §1 `documento.py` · §3 `separa_igv`, `totales`, `validar_documento` · §7 `test_totales.py` |
| RF-COM-10, RF-COM-11, RF-COM-12, RF-COM-13, RF-COM-14 | §1 `compras.py` · §2 índice único parcial · §3 `validar_fecha` · §4 registrar · §5 · §7 |

## 9. Dependencias de dudas abiertas

- **Q12 (fecha del kardex):** si se usa la fecha del documento, cambia el `fecha` del movimiento en `registrar_entrada`.

- **IGV del documento:** si se acepta ingresarlo, `totales()` admite una tolerancia de ±0,01 por línea.

- **Maquila / granel:** si se confirma, `es_comprable` agrega `GRANEL` y `TERMINADO`.
