# Plan 0004b — Compras: anulación

Estado: implementado (aprobado por el PO el 2026-10-11)

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/purchasing` (0004a implementada). La reversión la hace `InventarioService.revertir` (0003a), que ya revierte al costo original, rechaza entradas consumidas y no revierte dos veces.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/purchasing/application/compras.py` | `AnularCompra` (`compras.compra.anular`): compra bloqueada (`FOR UPDATE`), motivo obligatorio; si está Finalizada llama a `InventarioService.revertir('COMPRA', id, usuario)`; marca Anulada | RF-COM-15 a 18, 28, 29 |
| `src/inventory/domain/errores.py`, `movimientos.py` | `AnulacionConConsumoPosterior` lleva el `producto_id` consumido (el mensaje de 0003a no cambia) | RF-COM-16 |
| `src/purchasing/infrastructure/models.py`, `repositorios.py` | Campos `anulada_por`, `anulada_en`, `motivo_anulacion`; `ComprasOrm.anular` | RF-COM-15, 28 |
| `src/inventory/application/servicio.py` | Reexporta `AnulacionConConsumoPosterior`: compras la captura sin importar el dominio del inventario (contrato de import-linter) | RF-COM-16 |
| `src/purchasing/interfaces/` | "Anular compra" al final de "Más acciones", en rojo (docs/ux.md), que abre un `<dialog>` que explica qué se revierte y pide el motivo; en el detalle, quién anuló, cuándo y por qué | RF-COM-15, 16, 28 |

## 2. Modelo de datos

| Tabla | Cambio | Restricciones | RF |
|---|---|---|---|
| `purchasing_compra` | + anulada_por (usuario), anulada_en, motivo_anulacion | CHECK: Anulada ⇔ con motivo y fecha de anulación | RF-COM-15, 28, 29 |

El índice único del documento ya excluye las anuladas (0004a): RF-COM-18 no necesita cambios.

## 3. Funciones puras

Ninguna nueva: la reversión y su validación (RF-INV-20, 21) ya son del dominio del inventario.

## 4. Algoritmos clave

```
AnularCompra(actor, compra_id, motivo):            # compras.compra.anular
  motivo vacío → "El motivo es obligatorio"         # RF-COM-29
  en una transacción, con la compra bloqueada:      # RF-COM-17: el segundo espera y ve ANULADA
     no existe → NoEncontrado
     ANULADA → "La compra ya está anulada"
     FINALIZADA → InventarioService.revertir('COMPRA', id, usuario)
                  si AnulacionConConsumoPosterior(producto_id) →
                     "No se puede anular: <SKU> tuvo salidas posteriores a la compra. Corrígela con un ajuste CORRECCION"
     estado = ANULADA; anulada_por, anulada_en, motivo   # libera el documento (RF-COM-18)
```

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/compras/<id>/` | "Anular compra" en "Más acciones" (si el usuario tiene `compras.compra.anular` y la compra no está anulada) → `<dialog>` centrado que dice qué ocurrirá (con stock: se revierten las entradas; sin stock: solo cambia el estado) y pide el motivo; el rechazo muestra el producto consumido; una compra Anulada muestra quién, cuándo y por qué, y sus movimientos `ANULACION` | RF-COM-15, 16, 28 |
| `/compras/` | Chip "Anulada" y filtro por estado (ya existen) | — |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Anular una compra Creada o En proceso solo cambia su estado | Borrarla | Art. 4.5: los documentos no se borran; queda el motivo |
| El producto consumido viaja en la excepción del inventario | Que compras revise el kardex | Una sola regla (RF-INV-21) en un solo lugar |
| Concurrencia con `FOR UPDATE` sobre la compra | Solo el `UNIQUE revierte_id` | El segundo recibe un mensaje claro, no un error de base |

## 7. Estrategia de tests (pytest)

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Caso de uso | `tests/purchasing/usecases/test_anular.py` | Finalizada revierte al mismo costo; Creada solo cambia estado; consumida ⇒ rechazo con SKU y sin cambios; motivo; no dos veces; documento liberado; anulada no se edita | RF-COM-15, 16, 18, 28, 29 |
| Integración | `tests/purchasing/integration/test_concurrencia_compras.py` | Dos hilos anulan a la vez ⇒ una reversión | RF-COM-17 |
| Integración | `tests/purchasing/integration/test_compras_pantallas.py` | Anular desde el detalle con motivo; rechazo visible; sin permiso no ve el botón | RF-COM-15, 16 |
| Aceptación | `features/anulacion.feature` | Escenarios de la spec | ver `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-COM-15, 16, 17, 18, 28, 29 | §1 `AnularCompra` · §4 · §5 · §7 |

## 9. Dependencias de dudas abiertas

- Q12: si el contador no aprueba la opción A, cambia RF-COM-16 (y RF-INV-21 de 0003a).
