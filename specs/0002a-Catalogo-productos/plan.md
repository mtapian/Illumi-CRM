# Plan 0002a — Catálogo: unidades y productos

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/catalog`. Es mayormente CRUD; tiene dominio puro solo para los tipos de producto, las presentaciones y el ISC. Requiere: 0001a, 0001c.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/catalog/domain/tipos.py` | `TipoProducto` y sus capacidades (comprable, producible, vendible, lote) | RF-CAT-05 a 07, 12, 13 |
| `src/catalog/domain/producto.py` | Validación de un producto según su tipo y de los campos inmutables con movimientos | RF-CAT-04 a 11 |
| `src/catalog/domain/errores.py` | `SkuDuplicado`, `CampoInmutable`, `LimiteProductosPlan`, `MaterialNoEsEnvase`, `ContenidoInmutable`, `IscSinTarifaVigente`… | todos los `SI … ENTONCES` |
| `src/catalog/application/unidades.py` | Alta, desactivación y eliminación de unidades; siembra inicial | RF-CAT-01 a 03 |
| `src/catalog/application/productos.py` | `CrearProducto`, `EditarProducto`, `DesactivarProducto`, `EliminarProducto` | RF-CAT-04 a 14, 19 a 21 |
| `src/catalog/application/fachada.py` | `CatalogoQuery` público: `producto()`, `presentacion()`, `activos(tipo)`, `isc_aplicable(producto, fecha)`, `materiales_para()` | RF-CAT-13 |
| `src/catalog/application/puertos.py` | `InventarioConsultaPort` (stock y movimientos de un producto, implementado por épica 0003) y `ReferenciasPort` (recetas, pedidos) | RF-CAT-09, 20, 21 |
| `src/catalog/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios filtrados por tenant | §2 |
| `src/catalog/interfaces/views/*.py` + `templates/catalog/*.html` | Pantallas de §5 | RF-CAT-01 a 14, 19 a 21 |
| `src/catalog/interfaces/api.py` | `GET /api/v1/productos` (lectura para n8n) | (épica 0001, RF-TEN-48) |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `catalog_unidad` | empresa_id, nombre, abreviatura, codigo_sunat, activo | UNIQUE(empresa_id, abreviatura) | RF-CAT-01 a 03 |
| `catalog_familia` | empresa_id, nombre, activo | UNIQUE(empresa_id, nombre) | RF-CAT-04, 14 |
| `catalog_producto` | empresa_id, sku, nombre, tipo, unidad_id, familia_id null, stock_minimo `NUMERIC(14,4)`, controla_lote, precio_venta `NUMERIC(14,2)` null, isc_categoria_id null, contenido_litros `NUMERIC(10,4)` null (solo `MERCADERIA`), vida_util_dias null, prefijo_lote null, activo | UNIQUE(empresa_id, sku); `CHECK tipo IN (…5 tipos)`; `TERMINADO` y `MERCADERIA` con precio; `TERMINADO` con vida útil > 0; `GRANEL`/`TERMINADO` con lote | RF-CAT-04 a 13 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `campos_requeridos(tipo) -> set` | Campos obligatorios según el tipo | RF-CAT-04 a 07 |
| `validar_producto(datos, tipo)` | Unidad litros en `GRANEL`, precio en vendibles, vida útil en `TERMINADO`, contenido si el ISC es por litro | RF-CAT-05 a 07, 11 |
| `cambios_prohibidos(original, nuevo, tiene_movimientos) -> list` | SKU, tipo, unidad, controla lote | RF-CAT-09 |
| `controla_lote(tipo, elegido) -> bool` | Siempre en `GRANEL`/`TERMINADO`; elegido en `MERCADERIA` | RF-CAT-12 |
| `es_vendible(tipo) -> bool` | `TERMINADO` o `MERCADERIA` | RF-CAT-13 |
| `cabe_en_limite(activos, limite) -> bool` | Cuentan los activos de todos los tipos | RF-CAT-10 |
| `puede_eliminar(tiene_movimientos, referencias) -> bool` | Sin movimientos ni referencias | RF-CAT-21 |
| `puede_desactivar(stock, es_granel_con_presentaciones_activas) -> bool` | Ver RF | RF-CAT-20 |

## 4. Algoritmos clave

Sin algoritmos no triviales: la lógica está en las funciones puras de §3.

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/catalogo/productos/` | Listado paginado de 25 con búsqueda por SKU/nombre y filtros por tipo, familia, estado y stock bajo (HTMX) | RF-CAT-14 |
| `/catalogo/productos/nuevo?tipo=` | Formulario que muestra solo los campos del tipo; para `TERMINADO`, formset de materiales; para `MERCADERIA`, precio, ISC, contenido y "controla lote" | RF-CAT-04 a 13 |
| `/catalogo/productos/<id>` | Ficha; campos bloqueados con candado si hay movimientos; botones desactivar y eliminar según RF | RF-CAT-09, 19 a 21 |
| `/catalogo/unidades/`, `/catalogo/familias/` | CRUD simple | RF-CAT-01 a 03 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Un solo modelo `Producto` con tipo y campos opcionales | Una tabla por tipo | Los 5 tipos comparten stock, kardex y costo; la validación por tipo vive en el dominio |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/catalog tests/acceptance -k "E02a"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/catalog/unit/test_producto.py` | Campos por tipo, inmutables con movimientos, lote, vendible | RF-CAT-04 a 13 |
| Caso de uso | `tests/catalog/usecases/test_productos.py` | Límite del plan, desactivar con stock, eliminar con referencias | RF-CAT-10, 19 a 21 |
| Integración | `tests/catalog/integration/test_unidades.py` | Siembra inicial, unidad en uso no se elimina ni desactiva | RF-CAT-01 a 03 |
| Integración | `tests/catalog/integration/test_constraints.py` | SKU único por empresa; trigger de tarifas inmutables | RF-CAT-08, 24 |
| Integración | `tests/catalog/integration/test_listado.py` | Filtros y paginación; p95 con 10 000 productos | RF-CAT-14, RNF-CAT-01 |
| Aceptación | `features/presentaciones.feature`, `features/productos.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-CAT-01, RF-CAT-02, RF-CAT-03 | §1 `unidades.py` · §2 `catalog_unidad` · §5 `/catalogo/unidades/` · §7 `test_unidades.py` |
| RF-CAT-04, RF-CAT-05, RF-CAT-06, RF-CAT-07 | §1 `producto.py`, `tipos.py` · §3 `campos_requeridos`, `validar_producto` · §5 formulario por tipo · §7 `test_producto.py` |
| RF-CAT-08, RF-CAT-09, RF-CAT-10, RF-CAT-11, RF-CAT-12, RF-CAT-13 | §2 constraints · §3 `cambios_prohibidos`, `cabe_en_limite`, `controla_lote`, `es_vendible` · §7 |
| RF-CAT-14 | §5 listado · §7 `test_listado.py` |
| RF-CAT-19, RF-CAT-20, RF-CAT-21 | §1 `productos.py`, `puertos.py` · §3 `puede_desactivar`, `puede_eliminar` · §7 `test_productos.py` |

## 9. Dependencias de dudas abiertas

- **Q7 (vida útil):** si pasa a ser por estilo, cambia `vida_util_dias` de la presentación al granel.

- **Maquila / compra de granel:** si se confirma, `es_comprable` agrega `GRANEL` y `TERMINADO` (cambio en `tipos.py` y épica 0004).
