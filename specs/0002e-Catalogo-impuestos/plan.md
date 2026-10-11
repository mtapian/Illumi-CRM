# Plan 0002e — Catálogo: impuestos

Estado: borrador (2026-10-10)

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/catalog`. Los impuestos son del catálogo porque se asignan al producto; ventas, compras y facturación los leen por la fachada (`CatalogoQuery`).

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/catalog/domain/impuestos.py` | Códigos SUNAT y criterios; `validar_impuesto` (IGV/EXO/INA solo porcentaje), `validar_tasa`, `validar_impuestos_de_venta` (una afectación, un ISC como máximo, ISC solo en bienes), `desglose_linea(total, cantidad, igv_pct, isc)` con ISC fijo o porcentual, `sistema_isc(criterio)` (fijo → 02, porcentaje → 01) | RF-CAT-53, 54, 57 a 59 |
| `src/catalog/domain/precio.py` | `desglose_precio` pasa a recibir el % de la afectación del producto (0 en EXO/INA) | RF-CAT-59 |
| `src/catalog/application/impuestos.py` | `GuardarImpuesto`, `AgregarTasa`, `CambiarEstadoImpuesto` (`catalogo.isc.gestionar`) | RF-CAT-53 a 55 |
| `src/catalog/application/productos.py` | `CrearProducto` / `EditarProducto` reciben `impuestos_venta` e `impuestos_compra` (ids) y validan; se retiran `tasa` y `AgregarTasaIsc` | RF-CAT-56 a 58 |
| `src/catalog/application/fachada.py` | `impuestos_de_venta(producto, fecha)` → afectación, % IGV, ISC (tasa, litros, código); `isc_aplicable` e `isc_de_linea` se reimplementan sobre ella | RF-CAT-59 |
| `src/catalog/infrastructure/models.py` + migraciones | Tablas de §2; migración de conversión (RF-CAT-60) que retira `catalog_productoisctasa`, `isc_sistema` e `isc_codigo_tipo_sistema` del producto | RF-CAT-60 |
| `src/catalog/infrastructure/contenedor.py` | Sembrador de los tres impuestos iniciales | RF-CAT-52 |
| `src/catalog/interfaces/` | `/catalogo/impuestos/` (listado de maestro, ficha con tasas y "Agregar tasa"); etiquetas en las pestañas Ventas y Compras de la ficha de producto | RF-CAT-53 a 57 |
| `src/tenancy/...` | Se retira el % de IGV de la configuración de la empresa; `igv_vigente` se reemplaza por la fachada del catálogo | 0001a RF-TEN-15, 16 |
| `src/shared/domain/accesos.py` | La etiqueta de `catalogo.isc.gestionar` pasa a "Gestionar impuestos" (mismo código: no cambia roles) | — |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `catalog_impuesto` | empresa_id, nombre, codigo (`IGV`/`EXO`/`INA`/`ISC`), criterio (`PORCENTAJE`/`MONTO_FIJO`), uso (`VENTA`/`COMPRA`/`AMBOS`), activo | UNIQUE(empresa_id, lower(nombre)); CHECK `MONTO_FIJO` solo en ISC | RF-CAT-53, 55 |
| `catalog_impuesto_tasa` | empresa_id, impuesto_id, vigente_desde, importe `NUMERIC(10,4)`, creado_por | UNIQUE(impuesto_id, vigente_desde); CHECK importe ≥ 0; trigger de solo inserción (`fn_rechazar_cambio`) | RF-CAT-54 |
| `catalog_producto_impuesto` | empresa_id, producto_id, impuesto_id, uso (`VENTA`/`COMPRA`) | UNIQUE(producto_id, impuesto_id, uso) | RF-CAT-56 a 58 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `validar_tasa(tributo, importe, existentes, fecha)` | Fecha única, importe ≥ 0, 0 en EXO/INA | RF-CAT-54 |
| `validar_impuestos_de_venta(impuestos, es_servicio, litros)` | Exactamente una afectación; a lo sumo un ISC; ISC solo en bien con litros > 0 | RF-CAT-57, 58 |
| `desglose_linea(total, cantidad, litros, igv_pct, isc_tasa)` | Fórmula de Definiciones, half-up a 2 decimales | RF-CAT-59 |
| `agrupar_historiales(historiales_fijos)` | Para la conversión: productos con el mismo historial de ISC (ya pasado a monto fijo por unidad) comparten impuesto | RF-CAT-60 |

## 4. Algoritmos clave

**Conversión (RF-CAT-60), una migración de datos reversible:**

```
por empresa:
  crear "IGV 18%", "Exonerado", "Inafecto"
  copiar el historial de IGV de la empresa a las tasas de "IGV 18%"
  por producto con ISC: historial fijo = [(fecha, round(tasa × litros, 4))]
  grupos = productos con el mismo historial fijo
  por grupo: crear impuesto ISC de monto fijo "ISC <litros> L" con ese historial
  por producto: VENTA y COMPRA = "IGV 18%"; si estaba afecto a ISC, VENTA += su ISC
SET CONSTRAINTS ALL IMMEDIATE   (como en 0002a 0007 y 0008)
```

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/catalogo/impuestos/` | Listado de maestro (ADR-12): nombre, código SUNAT, criterio, uso, tasa vigente hoy (S/ o %), productos, estado; `?editar=<id>` con historial de tasas y "Agregar tasa" | RF-CAT-53 a 55 |
| Ficha de producto, pestañas Ventas y Compras | "Impuestos de venta" / "Impuestos de compra" como etiquetas (casillas de los activos); el desglose del precio se mantiene | RF-CAT-56 a 59 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Monto fijo por unidad vendida, definido por el usuario | ISC por litro calculado con los litros del producto | Pedido del PO: más simple y dinámico; cada presentación tiene su impuesto. El sistema no valida que el monto corresponda a la presentación (responsabilidad del usuario) |
| Orden ISC → IGV fijo en el dominio | "Afecta la base de los siguientes" configurable (Odoo) | Una sola regla tributaria, validada con el contador; menos combinaciones que probar |
| Tasas aparte del impuesto, solo inserción | Importe editable en el impuesto (Odoo) | Constitución, art. 5.1: vigencia y documentos inmutables |
| Mismo permiso `catalogo.isc.gestionar` con otra etiqueta | Permiso nuevo | No obliga a tocar roles ni plantillas; el alcance es el mismo (impuestos) |
| La gratuidad no es un impuesto del producto | Impuesto GRA asignable | Es una condición de la línea de venta (0006b) |

## 7. Estrategia de tests (pytest)

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/catalog/unit/test_impuestos.py` | Tasas, criterios, validación de impuestos de venta, desglose gravado/exonerado/inafecto con ISC fijo, porcentual o sin ISC (ejemplo de 0006b con ISC fijo 0.8283: 288.00 → 224.19 + 19.88 + 43.93), sistema 01/02 | RF-CAT-53, 54, 57 a 59 |
| Caso de uso | `tests/catalog/usecases/test_impuestos.py` | Nombre único, tributo fijo con uso, desactivar con productos, permisos | RF-CAT-53 a 55 |
| Integración | `tests/catalog/integration/test_conversion.py` | Conversión con datos reales: IGV con historial; ISC por litro → monto fijo por unidad; dos productos con los mismos litros e historial comparten impuesto; el ISC de una venta da lo mismo antes y después; reversible | RF-CAT-60 |
| Integración | `tests/catalog/integration/test_pantallas.py` | Maestro de impuestos y etiquetas en la ficha | RF-CAT-53, 56 |
| Aceptación | `features/impuestos.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-CAT-52 | §1 sembrador · §7 |
| RF-CAT-53 a 55 | §1 `impuestos.py` (aplicación) · §2 `catalog_impuesto`, `catalog_impuesto_tasa` · §5 maestro · §7 |
| RF-CAT-56 a 59 | §1 `productos.py`, `fachada.py`, dominio · §2 `catalog_producto_impuesto` · §5 ficha · §7 |
| RF-CAT-60 | §4 conversión · §7 `test_conversion.py` |
