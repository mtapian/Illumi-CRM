# Plan 002 — Catálogo

Estado: borrador

Spec: `./spec.md` · Base técnica: `../000-arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/catalog`. Es mayormente CRUD; tiene dominio puro solo para los tipos de producto, las presentaciones y el ISC.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/catalog/domain/tipos.py` | `TipoProducto` y sus capacidades (comprable, producible, vendible, lote) | RF-CAT-05 a 07, 12, 13 |
| `src/catalog/domain/producto.py` | Validación de un producto según su tipo y de los campos inmutables con movimientos | RF-CAT-04 a 11 |
| `src/catalog/domain/presentacion.py` | Validación de la presentación y `materiales_para(unidades)` | RF-CAT-15 a 18 |
| `src/catalog/domain/isc.py` | Categorías de ISC, tarifa aplicable por fecha, cálculo del ISC por litro | RF-CAT-22 a 27 |
| `src/catalog/domain/errores.py` | `SkuDuplicado`, `CampoInmutable`, `LimiteProductosPlan`, `MaterialNoEsEnvase`, `ContenidoInmutable`, `IscSinTarifaVigente`… | todos los `SI … ENTONCES` |
| `src/catalog/application/unidades.py` | Alta, desactivación y eliminación de unidades; siembra inicial | RF-CAT-01 a 03 |
| `src/catalog/application/productos.py` | `CrearProducto`, `EditarProducto`, `DesactivarProducto`, `EliminarProducto` | RF-CAT-04 a 14, 19 a 21 |
| `src/catalog/application/presentaciones.py` | `DefinirPresentacion` | RF-CAT-15 a 18 |
| `src/catalog/application/isc.py` | `CrearCategoriaIsc`, `AgregarTarifaIsc`, `DesactivarCategoriaIsc` | RF-CAT-22 a 24, 28 |
| `src/catalog/application/fachada.py` | `CatalogoQuery` público: `producto()`, `presentacion()`, `activos(tipo)`, `isc_aplicable(producto, fecha)`, `materiales_para()` | RF-CAT-13, 25, 27 |
| `src/catalog/application/puertos.py` | `InventarioConsultaPort` (stock y movimientos de un producto, implementado por spec 003) y `ReferenciasPort` (recetas, pedidos) | RF-CAT-09, 20, 21 |
| `src/catalog/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios filtrados por tenant | §2 |
| `src/catalog/interfaces/views/*.py` + `templates/catalog/*.html` | Pantallas de §5 | RF-CAT-01 a 28 |
| `src/catalog/interfaces/api.py` | `GET /api/v1/productos` (lectura para n8n) | (spec 001, RF-TEN-48) |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `catalog_unidad` | empresa_id, nombre, abreviatura, codigo_sunat, activo | UNIQUE(empresa_id, abreviatura) | RF-CAT-01 a 03 |
| `catalog_familia` | empresa_id, nombre, activo | UNIQUE(empresa_id, nombre) | RF-CAT-04, 14 |
| `catalog_producto` | empresa_id, sku, nombre, tipo, unidad_id, familia_id null, stock_minimo `NUMERIC(14,4)`, controla_lote, precio_venta `NUMERIC(14,2)` null, isc_categoria_id null, contenido_litros `NUMERIC(10,4)` null (solo `MERCADERIA`), vida_util_dias null, prefijo_lote null, activo | UNIQUE(empresa_id, sku); `CHECK tipo IN (…5 tipos)`; `TERMINADO` y `MERCADERIA` con precio; `TERMINADO` con vida útil > 0; `GRANEL`/`TERMINADO` con lote | RF-CAT-04 a 13 |
| `catalog_presentacion` | empresa_id, producto_id (TERMINADO), granel_id, contenido_litros `NUMERIC(10,4)` | UNIQUE(producto_id); `CHECK contenido_litros > 0` | RF-CAT-15, 17, 18 |
| `catalog_presentacion_material` | presentacion_id, material_id (ENVASE), cantidad_por_unidad `NUMERIC(14,4)` | UNIQUE(presentacion_id, material_id); `CHECK > 0` | RF-CAT-16 |
| `catalog_isc_categoria` | empresa_id, nombre, sistema (`ESPECIFICO`), codigo_tributo (`2000`), codigo_tipo_sistema, activo | UNIQUE(empresa_id, nombre); `CHECK sistema = 'ESPECIFICO'` | RF-CAT-22, 23, 28 |
| `catalog_isc_tarifa` | categoria_id, vigente_desde `DATE`, monto_por_litro `NUMERIC(10,4)`, creado_por | UNIQUE(categoria_id, vigente_desde); `CHECK > 0`; solo inserción (trigger) | RF-CAT-24, 25 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `campos_requeridos(tipo) -> set` | Campos obligatorios según el tipo | RF-CAT-04 a 07 |
| `validar_producto(datos, tipo)` | Unidad litros en `GRANEL`, precio en vendibles, vida útil en `TERMINADO`, contenido si el ISC es por litro | RF-CAT-05 a 07, 11, 26 |
| `cambios_prohibidos(original, nuevo, tiene_movimientos) -> list` | SKU, tipo, unidad, controla lote | RF-CAT-09 |
| `controla_lote(tipo, elegido) -> bool` | Siempre en `GRANEL`/`TERMINADO`; elegido en `MERCADERIA` | RF-CAT-12 |
| `es_vendible(tipo) -> bool` | `TERMINADO` o `MERCADERIA` | RF-CAT-13 |
| `cabe_en_limite(activos, limite) -> bool` | Cuentan los activos de todos los tipos | RF-CAT-10 |
| `validar_presentacion(granel, contenido, materiales)` | Granel activo, contenido > 0, ≥ 1 material `ENVASE` con cantidad > 0 | RF-CAT-15, 16 |
| `materiales_para(presentacion, unidades) -> dict` | Material → cantidad (4 decimales); la usa la spec 005 | RF-CAT-16 |
| `tarifa_aplicable(tarifas, fecha) -> Tarifa \| None` | La de mayor `vigente_desde ≤ fecha` | RF-CAT-24, 25 |
| `isc_linea(cantidad, contenido_l, tarifa) -> Decimal` | `round(cantidad × contenido × monto_por_litro, 2)`; 0 sin categoría | RF-CAT-25, 27 |
| `puede_eliminar(tiene_movimientos, referencias) -> bool` | Sin movimientos ni referencias | RF-CAT-21 |
| `puede_desactivar(stock, es_granel_con_presentaciones_activas) -> bool` | Ver RF | RF-CAT-20 |

`tarifa_aplicable` recibe la fecha de emisión (no "hoy"): así una venta del 31-dic usa la tarifa vieja aunque se calcule el 1-ene.

## 4. Algoritmos clave

**ISC aplicable a una línea** (RF-CAT-25 a 27):
```
isc_aplicable(producto, fecha):
  si producto.isc_categoria is None → None                         # RF-CAT-27
  contenido = presentacion(producto).contenido si TERMINADO, si no producto.contenido_litros
  tarifa = tarifa_aplicable(tarifas(categoria), fecha)
  si tarifa is None → IscSinTarifaVigente(categoria, fecha)
  devolver IscDTO(monto_por_litro, contenido, codigo_tributo, codigo_tipo_sistema)
```

**Editar una presentación** (RF-CAT-18):
```
si cambia contenido_litros y InventarioConsultaPort.tiene_movimientos(producto) → ContenidoInmutable
si cambian materiales → se guardan; aplican a envasados futuros (el costo existente no se toca)
```

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/catalogo/productos/` | Listado paginado de 25 con búsqueda por SKU/nombre y filtros por tipo, familia, estado y stock bajo (HTMX) | RF-CAT-14 |
| `/catalogo/productos/nuevo?tipo=` | Formulario que muestra solo los campos del tipo; para `TERMINADO`, formset de materiales; para `MERCADERIA`, precio, ISC, contenido y "controla lote" | RF-CAT-04 a 13, 15, 16 |
| `/catalogo/productos/<id>` | Ficha; campos bloqueados con candado si hay movimientos; botones desactivar y eliminar según RF | RF-CAT-09, 18 a 21 |
| `/catalogo/unidades/`, `/catalogo/familias/` | CRUD simple | RF-CAT-01 a 03 |
| `/catalogo/isc/` | Categorías con su historial de tarifas (tabla por fecha; solo "Agregar tarifa") | RF-CAT-22 a 24, 28 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Un solo modelo `Producto` con tipo y campos opcionales | Una tabla por tipo | Los 5 tipos comparten stock, kardex y costo; la validación por tipo vive en el dominio |
| Tarifas de ISC inmutables con vigencia | Editar el monto vigente | Constitución art. 5.1; los comprobantes emitidos no cambian |
| ISC configurado en el catálogo (por empresa) | En la configuración de facturación | Es un atributo del producto; la facturación solo recibe importes (000 §2) |
| Contenido de la presentación inmutable con movimientos | Permitir cambiarlo | El contenido define el ISC de unidades ya envasadas (RF-CAT-18) |
| Fracción de caja (0,0417) aceptada | Materiales "por empaque" | Simplicidad en el MVP (art. 7.6); queda como fuera de alcance |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/catalog tests/acceptance -k "E02"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/catalog/unit/test_producto.py` | Campos por tipo, inmutables con movimientos, lote, vendible | RF-CAT-04 a 13 |
| Unitario | `tests/catalog/unit/test_presentacion.py` | Validaciones; `materiales_para(240)` = 240 botellas, 10,008 cajas | RF-CAT-15 a 17 |
| Unitario | `tests/catalog/unit/test_isc.py` | Tarifa el día antes, el día de inicio y después del cambio; sin categoría ⇒ 0; 24 × 0,33 L × 2,51 = 19,88 | RF-CAT-23 a 27 |
| Caso de uso | `tests/catalog/usecases/test_productos.py` | Límite del plan, desactivar con stock, eliminar con referencias | RF-CAT-10, 19 a 21 |
| Caso de uso | `tests/catalog/usecases/test_presentacion_edicion.py` | Contenido inmutable con movimientos; materiales editables | RF-CAT-18 |
| Caso de uso | `tests/catalog/usecases/test_isc.py` | Crear categoría con primera tarifa, agregar tarifa, no editar, desactivar en uso | RF-CAT-22, 24, 28 |
| Integración | `tests/catalog/integration/test_unidades.py` | Siembra inicial, unidad en uso no se elimina ni desactiva | RF-CAT-01 a 03 |
| Integración | `tests/catalog/integration/test_constraints.py` | SKU único por empresa; trigger de tarifas inmutables | RF-CAT-08, 24 |
| Integración | `tests/catalog/integration/test_listado.py` | Filtros y paginación; p95 con 10 000 productos | RF-CAT-14, RNF-CAT-01 |
| Aceptación | `features/productos.feature`, `features/presentaciones.feature` | Escenarios de la spec | todos |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-CAT-01, RF-CAT-02, RF-CAT-03 | §1 `unidades.py` · §2 `catalog_unidad` · §5 `/catalogo/unidades/` · §7 `test_unidades.py` |
| RF-CAT-04, RF-CAT-05, RF-CAT-06, RF-CAT-07 | §1 `producto.py`, `tipos.py` · §3 `campos_requeridos`, `validar_producto` · §5 formulario por tipo · §7 `test_producto.py` |
| RF-CAT-08, RF-CAT-09, RF-CAT-10, RF-CAT-11, RF-CAT-12, RF-CAT-13 | §2 constraints · §3 `cambios_prohibidos`, `cabe_en_limite`, `controla_lote`, `es_vendible` · §7 |
| RF-CAT-14 | §5 listado · §7 `test_listado.py` |
| RF-CAT-15, RF-CAT-16, RF-CAT-17, RF-CAT-18 | §1 `presentacion.py` · §3 `validar_presentacion`, `materiales_para` · §4 editar presentación · §7 |
| RF-CAT-19, RF-CAT-20, RF-CAT-21 | §1 `productos.py`, `puertos.py` · §3 `puede_desactivar`, `puede_eliminar` · §7 `test_productos.py` |
| RF-CAT-22, RF-CAT-23, RF-CAT-24, RF-CAT-25, RF-CAT-26, RF-CAT-27, RF-CAT-28 | §1 `isc.py` · §2 tablas ISC · §3 `tarifa_aplicable`, `isc_linea` · §4 ISC aplicable · §5 `/catalogo/isc/` · §7 `test_isc.py` |

## 9. Dependencias de dudas abiertas

- **Q7 (vida útil):** si pasa a ser por estilo, cambia `vida_util_dias` de la presentación al granel.
- **Código de tipo de sistema ISC:** es un dato de la categoría; no cambia el código.
- **Maquila / compra de granel:** si se confirma, `es_comprable` agrega `GRANEL` y `TERMINADO` (cambio en `tipos.py` y spec 004).
