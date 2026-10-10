# Plan 0003a — Inventario: almacenes, movimientos y costo promedio

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/inventory`. Es el núcleo transaccional: compras, producción y ventas **solo** cambian stock a través de su fachada `InventarioService` (constitución art. 4). Requiere: 0001a, 0002a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/inventory/domain/costo.py` | `CostoProducto` (cantidad + valor): entrada, salida al promedio, reversión de entrada, salida que vacía | RF-INV-18, 20, 21, 24 |
| `src/inventory/domain/existencia.py` | Stock por producto × almacén × lote; salida sin negativos | RF-INV-19 |
| `src/inventory/domain/fefo.py` | Asignación FEFO con `hoy` | RF-INV-22, 23 |
| `src/inventory/domain/lotes.py` | `lote_vencido`, `lotes_por_vencer` con `hoy` | RF-INV-23 |
| `src/inventory/domain/errores.py` | `StockInsuficiente`, `LoteVencido`, `AnulacionConConsumoPosterior`, `CostoRequerido`, `SaldoInicialNoPermitido`… | todos los `SI … ENTONCES` |
| `src/inventory/application/servicio.py` | `InventarioService`: `registrar_entrada`, `registrar_salida`, `revertir`, `bloquear`, `crear_lote`, `asegurar_costo_producto`, `crear_almacen` | RF-INV-17 a 24 |
| `src/inventory/application/almacenes.py` | CRUD de almacenes y desactivación | RF-INV-01 a 03 |
| `src/inventory/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios con locks en el orden de 0000 §5 | §2 |
| `src/inventory/infrastructure/sql/*.sql` | `trg_movimiento_inmutable`, `vw_kardex`, `vw_stock_valorizado` | RF-INV-17 |
| `src/inventory/interfaces/views/*.py` + `templates/inventory/*.html` | Pantallas de §5 | RF-INV-01 a 03 |
| `src/inventory/interfaces/api.py` | `GET /api/v1/stock` | (épica 0001, RF-TEN-48) |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `inventory_almacen` | empresa_id, nombre, activo | UNIQUE(empresa_id, nombre) | RF-INV-01 a 03 |
| `inventory_lote` | empresa_id, producto_id, codigo, fecha_produccion, fecha_vencimiento null, origen_tipo, origen_id | UNIQUE(empresa_id, producto_id, codigo) | RF-INV-22 |
| `inventory_stock` | empresa_id, producto_id, almacen_id, lote_id null, cantidad `NUMERIC(14,4)` | UNIQUE NULLS NOT DISTINCT (…); `CHECK cantidad >= 0` | RF-INV-19 |
| `inventory_costo_producto` | empresa_id, producto_id, cantidad_total, valor_total `NUMERIC(14,2)`, costo_promedio `NUMERIC(14,6)` | UNIQUE(empresa_id, producto_id); `CHECK valor_total >= 0`; la fila se crea al crear el producto | RF-INV-18, 24 |
| `inventory_movimiento` | empresa_id, fecha `timestamptz`, tipo, motivo, producto_id, almacen_id, lote_id, cantidad, costo_unitario `NUMERIC(14,6)`, costo_total `NUMERIC(14,2)`, saldo_cantidad, saldo_promedio, ref_tipo (`COMPRA`, `AJUSTE`, `OP`, `ENVASADO`, `VENTA`), ref_id, revierte_id null, usuario_id | `UNIQUE(revierte_id) WHERE NOT NULL`; trigger de inmutabilidad | RF-INV-17, 20 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `entrada(costo: CostoProducto, cant, costo_unit) -> CostoProducto` | `valor += cant × costo`; `cantidad += cant`; promedio = valor / cantidad | RF-INV-18 |
| `salida_al_promedio(costo, cant) -> (CostoProducto, Money)` | Sale al promedio; si deja 0, sale por el valor restante | RF-INV-24 |
| `reversion_de_entrada(costo, cant, costo_original) -> CostoProducto` | `valor −= cant × costo_original`; error si el valor quedaría negativo | RF-INV-20 |
| `salir(existencia, cant) -> Existencia` | Lanza `StockInsuficiente` si queda negativo | RF-INV-19 |
| `lote_vencido(fecha_vencimiento, hoy) -> bool` | `fecha_vencimiento is not None and fecha_vencimiento < hoy` | RF-INV-23 |
| `orden_fefo(lote) -> tuple` | `(vencimiento is None, vencimiento, fecha_produccion, id)`: los sin fecha al final | RF-INV-22 |
| `asignar_fefo(existencias, cant, hoy) -> list[(lote, cant)]` | Excluye vencidos, ordena por `orden_fefo`, reparte | RF-INV-22 |
| `validar_salida_de_lote(lote, motivo, hoy)` | `LoteVencido` salvo motivo `MERMA` | RF-INV-23 |
| `hubo_salidas_posteriores(movimientos_producto, entrada) -> bool` | Cualquier salida del producto (cualquier almacén o lote) posterior a la entrada | RF-INV-21 |
| `inversos_de(movimientos) -> list` | Movimientos opuestos al costo original; en transferencia, ambos | RF-INV-20 |

## 4. Algoritmos clave

**Registrar una salida** (RF-INV-17, 19, 22 a 24):

```
registrar_salida(cmd):                         # dentro de la transacción del caso de uso que llama
  lineas = ordenar(cmd.lineas, por=(producto, almacen, lote))
  bloquear costo_producto de esos productos (FOR UPDATE), luego sus filas de stock
  por cada línea:
    si lote indicado: validar_salida_de_lote(lote, cmd.motivo, hoy)          # RF-INV-23
    asignaciones = [(lote, cant)] o asignar_fefo(existencias, cant, hoy)      # RF-INV-22
    por cada (lote, cant):
      existencia = salir(existencia, cant)                                     # RF-INV-19
      costo, importe = salida_al_promedio(costo, cant)                         # RF-INV-24
      insertar movimiento (inmutable) con costo y saldos                       # RF-INV-17
```

**Revertir un documento** (RF-INV-13, 20, 21):

```
revertir(ref_tipo, ref_id):
  movs = movimientos de la referencia sin revertir
  por cada entrada en movs: si hubo_salidas_posteriores(…) → AnulacionConConsumoPosterior   # RF-INV-21
  por cada m en inversos_de(movs):
     entrada o reversion_de_entrada al costo original; revierte_id = m.id      # UNIQUE impide revertir 2 veces
```

**Costo promedio (ejemplo de la spec):** 100 KG × 4,00 → +50 × 5,00 ⇒ 150 / 650,00 / 4,333333 → −30 ⇒ 130,00 → −20 ⇒ 86,67. Reversión de la compra de 50 a 5,00 ⇒ 100 KG / 400,00 / 4,000000.

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/inventario/almacenes/` | CRUD | RF-INV-01 a 03 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Guardar `valor_total` además del promedio | Guardar solo el promedio | La reversión de entradas y la salida que vacía el stock cuadran al céntimo (art. 4.2 y 4.6) |
| Bloqueo de `costo_producto` como mutex por producto | Locks solo sobre las filas de stock | Con FEFO el lote todavía no se conoce; el mutex por producto serializa la última unidad y el promedio |
| Movimientos inmutables por trigger | Solo por convención en el código | Art. 4.4: la base de datos es la red de seguridad (art. 7.3) |
| Rechazar la anulación de entradas ya consumidas | Revertir al promedio vigente | No falsea el promedio; la corrección se hace por ajuste (art. 4.5, v1.1.0) |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/inventory tests/acceptance -k "E03a"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/inventory/unit/test_costo.py` | Tabla del kardex de la spec; reversión de entrada a 4,000000; salida que vacía ⇒ valor 0 | RF-INV-18, 20, 24 |
| Unitario | `tests/inventory/unit/test_fefo.py` | Vencidos excluidos, reparto entre lotes, empate, lotes sin vencimiento al final; `hoy` = día del vencimiento | RF-INV-22, 23 |
| Caso de uso | `tests/inventory/usecases/test_revertir.py` | Reversión al costo original; con salidas posteriores ⇒ rechazo | RF-INV-20, 21 |
| Integración | `tests/inventory/integration/test_concurrencia.py` | Dos salidas por el último stock (`TransactionTestCase`) | RF-INV-19 |
| Integración | `tests/inventory/integration/test_inmutable.py` | `UPDATE`/`DELETE` sobre movimientos fallan; doble reversión falla | RF-INV-17, 20 |
| Integración | `tests/inventory/integration/test_almacenes.py` | Almacén "Principal", nombre único, no desactivar con stock | RF-INV-01 a 03 |
| Aceptación | `features/ajustes_lotes_alertas.feature`, `features/costo_y_kardex.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-INV-01, RF-INV-02, RF-INV-03 | §1 `almacenes.py` · §2 `inventory_almacen` · §5 `/inventario/almacenes/` · §7 `test_almacenes.py` |
| RF-INV-17, RF-INV-18, RF-INV-19, RF-INV-24 | §1 `servicio.py`, `costo.py`, `existencia.py` · §3 `entrada`, `salir`, `salida_al_promedio` · §4 registrar salida · §7 |
| RF-INV-20, RF-INV-21 | §3 `reversion_de_entrada`, `hubo_salidas_posteriores` · §4 revertir · §7 `test_revertir.py` |
| RF-INV-22, RF-INV-23 | §1 `fefo.py` · §3 `orden_fefo`, `asignar_fefo`, `validar_salida_de_lote` · §4 registrar salida · §7 `test_fefo.py` |

## 9. Dependencias de dudas abiertas

- **Q12 (anulación de compra consumida):** si el contador prefiere revertir al promedio, cambia `revertir` y `reversion_de_entrada`.
