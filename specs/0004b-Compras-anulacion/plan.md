# Plan 0004b — Compras: anulación

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/purchasing`. Usa `CatalogoQuery` (épica 0002) para validar productos e `InventarioService` (épica 0003) para las entradas y su reversión. Requiere: 0004a, 0003a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/purchasing/domain/errores.py` | `ProductoNoComprable`, `LoteRequerido`, `LoteConOtroVencimiento`, `DocumentoDuplicado`, `FechaFutura`, `FacturaRequiereRuc`, `CostoCeroSinBonificacion` | todos los `SI … ENTONCES` |
| `src/purchasing/application/compras.py` | `RegistrarCompra`, `AnularCompra`, `ComprasQuery` | RF-COM-15 a 18 |
| `src/purchasing/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/purchasing/interfaces/views/*.py` + `templates/purchasing/*.html` | Pantallas de §5 | RF-COM-15 a 18 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `purchasing_compra` | empresa_id, numero, proveedor_id, fecha `DATE`, almacen_id, doc_tipo, doc_serie_numero, igv_pct (vigente a la fecha), subtotal, igv, total, estado (`REGISTRADA`/`ANULADA`), observacion, created_by, anulado_por, anulado_en, motivo_anulacion | UNIQUE(empresa_id, numero); índice único parcial del documento entre compras activas (excepto `SIN_DOCUMENTO`) | RF-COM-15, 18 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|

## 4. Algoritmos clave

**Anular compra** (RF-COM-15 a 18):

```
AnularCompra(id, motivo):
  actor.exige(compras.compra.anular)
  compra = select_for_update(id); si compra.estado ≠ REGISTRADA → "La compra ya está anulada"   # RF-COM-17
  InventarioService.revertir('COMPRA', id)     # lanza AnulacionConConsumoPosterior (RF-COM-16)
  compra.estado = ANULADA (+ usuario, fecha, motivo)                         # libera el documento: RF-COM-18
```

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/compras/<id>` | Detalle de solo lectura con enlace a sus movimientos de kardex; botón "Anular" con motivo; mensaje de rechazo con el producto consumido | RF-COM-15 a 17 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Compras inmutables: se anulan y se registran de nuevo | Edición de compras | Art. 4.5; el kardex no se reescribe |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/purchasing tests/acceptance -k "E04b"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Caso de uso | `tests/purchasing/usecases/test_anular.py` | Reversión y nuevo promedio; consumo posterior ⇒ rechazo; documento liberado | RF-COM-15, 16, 18 |
| Integración | `tests/purchasing/integration/test_concurrencia.py` | Doble anulación simultánea ⇒ una sola reversión | RF-COM-17 |
| Aceptación | `features/compras.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-COM-15, RF-COM-16, RF-COM-17, RF-COM-18 | §4 anular · §5 detalle · §7 `test_anular.py`, `test_concurrencia.py` |

## 9. Dependencias de dudas abiertas

- Ninguna.
