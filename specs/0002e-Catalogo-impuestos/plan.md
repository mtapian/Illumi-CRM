# Plan 0002e — Catálogo: impuestos

Estado: implementado (2026-10-12; aprobado por el PO el 2026-10-11); **enmienda 1 aprobada (2026-10-12): criterio seleccionable** (§2, §3, §6, T9–T10). Historia: ( borrador del 2026-10-10, ajustado el 2026-10-11: impuestos de venta y de compra, ISC solo monto fijo, compras con IGV por producto)

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/catalog`. Los impuestos son del catálogo porque se asignan al producto; ventas, compras y facturación los leen por la fachada (`CatalogoQuery`).

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/catalog/domain/impuestos.py` | Tipos (`VENTA`/`COMPRA`) y códigos SUNAT; `validar_impuesto` (ISC solo de venta), `validar_tasa`, `validar_impuestos(tipo, impuestos, es_servicio)` (una afectación, a lo sumo un ISC, ISC solo en bienes), `desglose_linea(total, cantidad, igv_pct, isc_monto)` | RF-CAT-53, 54, 57 a 59 |
| `src/catalog/domain/precio.py` | `desglose_precio` usa `desglose_linea` con cantidad 1 | RF-CAT-59 |
| `src/catalog/application/impuestos.py` | `GuardarImpuesto`, `AgregarTasa`, `CambiarEstadoImpuesto` (`catalogo.isc.gestionar`) | RF-CAT-53 a 55 |
| `src/catalog/application/productos.py` | `CrearProducto` / `EditarProducto` reciben `impuestos_venta` e `impuestos_compra` (ids) y validan cada lista contra su tipo; se retiran `tasa` y `AgregarTasaIsc` | RF-CAT-56 a 58 |
| `src/catalog/application/fachada.py` | `impuestos_de_venta(producto, fecha)` → % IGV, afectación, ISC (monto); `igv_de_compra(producto, fecha)` → %; `isc_aplicable` e `isc_de_linea` se reimplementan sobre ella | RF-CAT-59, 61 |
| `src/catalog/infrastructure/models.py` + migraciones | Tablas de §2; migración de conversión (RF-CAT-60) que retira `catalog_productoisctasa`, `isc_sistema` e `isc_codigo_tipo_sistema` del producto | RF-CAT-60 |
| `src/catalog/infrastructure/contenedor.py` | Sembrador de los seis impuestos iniciales | RF-CAT-52 |
| `src/catalog/interfaces/` | `/catalogo/impuestos/` (listado de maestro con filtro por tipo, ficha con tasas y "Agregar tasa"); etiquetas en las pestañas Ventas y Compras de la ficha de producto | RF-CAT-53 a 57 |
| `src/purchasing/application/puertos.py`, `compras.py` | `IgvPort.igv_vigente(fecha)` pasa a `igv_de_compra(producto_id, fecha)`; el IGV se calcula por línea con el % del producto. Lo cumple la fachada del catálogo (ya permitida por import-linter) | RF-CAT-61 |
| `src/tenancy/...` | Se retira el % de IGV de la configuración de la empresa. **Al implementar:** `igv_vigente` de su fachada se conserva: el sembrador de impuestos toma de ella el IGV de la plataforma y compras la usa para un producto sin impuesto de compra (RF-COM-08 ajustado) | 0001a RF-TEN-15, 16 |
| `src/shared/domain/accesos.py` | La etiqueta de `catalogo.isc.gestionar` pasa a "Gestionar impuestos" (mismo código: no cambia roles) | — |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `catalog_impuesto` | empresa_id, nombre, tipo (`VENTA`/`COMPRA`), codigo (`IGV`/`EXO`/`INA`/`ISC`), activo | UNIQUE(empresa_id, tipo, lower(nombre)); CHECK ISC solo de `VENTA` | RF-CAT-53, 55 |
| `catalog_impuesto_tasa` | empresa_id, impuesto_id, vigente_desde, importe `NUMERIC(10,4)`, creado_por | UNIQUE(impuesto_id, vigente_desde); CHECK importe ≥ 0; trigger de solo inserción (`fn_rechazar_cambio`) | RF-CAT-54 |
| `catalog_producto_impuesto` | empresa_id, producto_id, impuesto_id | UNIQUE(producto_id, impuesto_id); la lista (venta o compra) es el tipo del impuesto | RF-CAT-56 a 58 |

Enmienda 1: `catalog_impuesto.criterio` (`PORCENTAJE`/`FIJO`, NOT NULL; la migración pone FIJO en ISC y PORCENTAJE en el resto) con CHECK de valores; fijo si el impuesto está en uso, como tipo y código.

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `validar_tasa(codigo, importe, fechas_existentes, fecha)` | Fecha única, importe ≥ 0, 0 en EXO/INA | RF-CAT-54 |
| `validar_impuestos(tipo, impuestos, es_servicio)` | Exactamente una afectación; a lo sumo un ISC; ISC solo en bienes; todos del tipo de la lista | RF-CAT-57, 58 |
| `desglose_linea(total, cantidad, afectacion, isc)` | Fórmula de Definiciones con cada impuesto como (criterio, importe), half-up a 2 decimales (enmienda 1) | RF-CAT-59 |
| `agrupar_historiales(historiales)` | Para la conversión: productos con el mismo historial de ISC por unidad comparten impuesto | RF-CAT-60 |

## 4. Algoritmos clave

**Conversión (RF-CAT-60), una migración de datos reversible:**

```
por empresa:
  por tipo en (VENTA, COMPRA): crear "IGV 18%", "Exonerado", "Inafecto"
  copiar el historial de IGV de la empresa a las tasas de los dos "IGV 18%"
  por producto con ISC: historial = [(fecha, round(tasa × litros, 4))]
  grupos = productos con el mismo historial
  por grupo: crear impuesto ISC de venta "ISC <litros> L" con ese historial
  por producto: si se vende, "IGV 18%" de venta (+ su ISC); si se compra, "IGV 18%" de compra
SET CONSTRAINTS ALL IMMEDIATE   (como en 0002a 0007 y 0008)
```

**IGV de una compra (RF-CAT-61):** al crear, editar o finalizar, cada línea con `FACTURA` toma `igv_de_compra(producto, fecha de la compra)`; el resto del cálculo de 0004a no cambia.

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/catalogo/impuestos/` | Listado de maestro (ADR-12): nombre, tipo, código SUNAT, tasa vigente hoy (S/ o %), productos, estado; filtro por tipo; `?editar=<id>` con historial de tasas y "Agregar tasa" | RF-CAT-53 a 55 |
| Ficha de producto, pestañas Ventas y Compras | "Impuestos de venta" / "Impuestos de compra" como etiquetas (casillas de los activos de su tipo); el desglose del precio se mantiene | RF-CAT-56 a 59 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Dos tipos de impuesto, Venta y Compra (PO, 2026-10-11) | Uso "ventas, compras o ambos" | Cada lista ofrece solo lo suyo y valida sus reglas; costo: el IGV se registra en dos impuestos |
| Criterio seleccionable por impuesto (enmienda 1, PO 2026-10-12) | Criterio derivado del código | El PO quiere que cada cliente lo configure según lo que vea; cubre el ISC al valor y por litro |
| Monto fijo por unidad vendida, definido por el usuario | ISC por litro calculado con los litros del producto | Pedido del PO: cada presentación tiene su impuesto; el sistema no valida el monto (responsabilidad del usuario) |
| Orden ISC → IGV fijo en el dominio | "Afecta la base de los siguientes" configurable (Odoo) | Una sola regla tributaria, validada con el contador |
| Tasas aparte del impuesto, solo inserción | Importe editable en el impuesto (Odoo) | Constitución, art. 5.1 |
| Mismo permiso `catalogo.isc.gestionar` con otra etiqueta | Permiso nuevo | No obliga a tocar roles ni plantillas |
| La gratuidad no es un impuesto del producto | Impuesto GRA asignable | Es una condición de la línea de venta (0006b) |

## 7. Estrategia de tests (pytest)

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/catalog/unit/test_impuestos.py` | Tasas, ISC solo de venta, validación de cada lista, desglose gravado/exonerado/inafecto con y sin ISC (ejemplo de 0006b: 288.00 → 224.19 + 19.88 + 43.93) | RF-CAT-53, 54, 57 a 59 |
| Caso de uso | `tests/catalog/usecases/test_impuestos.py` | Nombre único por tipo, tipo y código fijos con uso, desactivar con productos, permisos | RF-CAT-53 a 55 |
| Caso de uso | `tests/purchasing/usecases/test_compras.py` | Factura con un insumo exonerado: IGV 0 en esa línea | RF-CAT-61 |
| Integración | `tests/catalog/integration/test_conversion.py` | IGV con historial en los dos impuestos; ISC por litro → monto por unidad; dos productos con el mismo historial comparten impuesto; el ISC de una venta da lo mismo antes y después; compras sin cambios; reversible | RF-CAT-60 |
| Integración | `tests/catalog/integration/test_pantallas.py` | Maestro de impuestos y etiquetas en la ficha | RF-CAT-53, 56 |
| Aceptación | `features/impuestos.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-CAT-52 | §1 sembrador · §7 |
| RF-CAT-53 a 55 | §1 `impuestos.py` (aplicación) · §2 `catalog_impuesto`, `catalog_impuesto_tasa` · §5 maestro · §7 |
| RF-CAT-56 a 59 | §1 `productos.py`, `fachada.py`, dominio · §2 `catalog_producto_impuesto` · §5 ficha · §7 |
| RF-CAT-60 | §4 conversión · §7 `test_conversion.py` |
| RF-CAT-61 | §1 compras · §4 · §7 |
