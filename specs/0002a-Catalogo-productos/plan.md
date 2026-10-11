# Plan 0002a — Catálogo: unidades y productos

Estado: implementada (2026-10-10) · enmienda 1 en borrador

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
| `/catalogo/unidades/`, `/catalogo/categorias/` (antes familias) | CRUD simple | RF-CAT-01 a 03, 49 |

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

## Enmienda 1: ficha estilo Odoo (RF-CAT-04, 29 a 32), implementada

| Archivo | Cambio | RF |
|---|---|---|
| `src/shared/domain/auditoria.py` | Se mueve `diferencias()` desde `tenancy/domain/auditoria.py` (el catálogo no puede importar `tenancy.domain`) | RF-CAT-32 |
| `src/catalog/domain/precio.py` | `desglose_precio(precio, igv_pct, isc_unitario)`: base = precio / (1 + IGV), a 2 decimales half-up; IGV = precio − base; valor = base − ISC | RF-CAT-30 |
| `src/catalog/infrastructure/models.py` | `Producto.referencia`, `Producto.codigo_barras` (índice único parcial por empresa cuando no está vacío); `ProductoHistorial` (empresa, producto, actor, acción, antes, después, fecha) con trigger de solo inserción (`fn_rechazar_cambio`) | RF-CAT-31, 32 |
| `src/catalog/application/productos.py` | `CrearProducto`, `EditarProducto` y `CambiarEstadoProducto` registran el historial; `EditarProducto` admite cambiar el tipo sin movimientos | RF-CAT-29, 32 |
| `src/catalog/interfaces/pestanas.py` | Registro de pestañas externas de la ficha (mismo patrón que `shared/interfaces/menu.py`): 0002d registra "Compras" sin que el catálogo conozca a compras | RF-CAT-04 |
| `src/catalog/interfaces/templates/catalog/producto.html`, `forms.py`, `views.py` | Ficha con encabezado (nombre, tipo, estado, acciones), pestañas solo con CSS y panel de historial a la derecha; selector de tipo; desglose del precio | RF-CAT-04, 29 a 32 |

**Decisiones:**

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Historial propio del producto con `diferencias()` compartido | Librería de auditoría (`django-simple-history`) | Sin dependencias nuevas (art. 7.6); el mismo formato "antes → después" que la auditoría de accesos |
| Pestañas con CSS (radio + etiquetas) | JavaScript o HTMX | Funcionan sin JS y en el celular |
| Desglose calculado al mostrar, con IGV e ISC de hoy | Guardar el desglose en el producto | Los impuestos cambian por vigencia; cada venta calcula los suyos a su fecha |

**Notas de implementación:** `ProductoHistorial.producto_id` es un entero sin FK, para que el historial sobreviva a la eliminación del producto; el historial guarda solo los campos que cambiaron (familia, ISC y materiales por id). El tipo se cambia con `?tipo=` en la ficha (igual que al crear), solo sin movimientos. Cambiar el tipo se rechaza si el producto tiene referencias internas o externas.

**Tests:** `tests/catalog/unit/test_precio.py`, `tests/catalog/unit/test_pestanas.py` (desglose), `tests/catalog/usecases/test_historial.py` (historial y cambio de tipo), `tests/catalog/integration/test_pantallas.py` (pestañas por tipo, código de barras único, `UPDATE` sobre el historial falla) y los escenarios `@RF-CAT-29` a `@RF-CAT-32`.

## Enmienda 2: marcas y listado de maestros (RF-CAT-04, 14, 33 a 36)

| Archivo | Cambio | RF |
|---|---|---|
| `src/catalog/infrastructure/models.py` | `Marca` (nombre único por empresa sin distinguir mayúsculas, `activo`); `Producto.marca` (FK opcional, `PROTECT`); `Familia` con la misma restricción de nombre | RF-CAT-33, 34 |
| `src/catalog/application/productos.py` | `GuardarAgrupacion`, `CambiarEstadoAgrupacion`, `EliminarAgrupacion` (un solo juego para familia y marca); `EditarUnidad` | RF-CAT-33 a 35 |
| `src/catalog/interfaces/templates/catalog/_maestro.html` | Listado común: migas, buscador, botón "Nueva …", tabla con conteo de productos, estado y acciones (lápiz, tacho o desactivar) | RF-CAT-36 |
| `src/catalog/interfaces/views.py`, `urls.py`, `forms.py` | Vistas `unidades`, `familias`, `marcas` e `isc` con el patrón; `?q=`, `?nuevo=1`, `?editar=<id>`; marca en la ficha y en el filtro del listado | RF-CAT-04, 14, 36 |
| `src/shared/interfaces/templates/base.html` | `{% block migas %}` y CSS del listado de maestro | RF-CAT-36 |

**Decisiones:**

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Un juego de casos de uso para familia y marca (`tipo`) | Casos de uso duplicados | Mismas reglas (RF-CAT-34) |
| Formulario en la misma página (`?nuevo`, `?editar`) | Modal con JS o páginas aparte | Sin JS y sin rutas nuevas por acción |
| Íconos SVG en línea | Librería de íconos | Sin dependencias (ADR-12) |

**Tests:** `tests/catalog/usecases/test_maestros.py`, `tests/catalog/integration/test_pantallas.py` (búsqueda, conteo, 404 de otra empresa) y los escenarios `@UC-CAT-07`.

## Enmienda 4: Bien o Servicio, casillas, receta e ISC en la ficha (RF-CAT-37 a 48), implementada

Se implementa en **3 etapas**, cada una con su migración y la suite en verde al cerrar: **A** tipo y casillas, **B** receta, **C** ISC en la ficha.

*Ajuste al implementar (2026-10-10):* las etapas **A y B se hacen juntas** (una migración, `0007_bien_servicio`). La validación de la presentación depende de los tipos viejos (origen `GRANEL`, materiales `ENVASE`): separarlas obligaba a escribir una presentación provisional que B descartaba. El contenido en litros pasa ya a ser un campo del producto (se copia desde la presentación en la conversión), así `isc_de_producto` no depende de la receta. La etapa C (tasas en la ficha y retiro de las categorías) no cambia. Al desactivar un producto ya no se exige desactivar antes los que lo usan en su receta (la receta es opcional y la OP copia y edita sus componentes); sí se sigue impidiendo eliminarlo (RF-CAT-21).

### Modelo de datos

| Tabla | Cambio | Etapa |
|---|---|---|
| `catalog_producto` | `tipo` pasa a `BIEN`/`SERVICIO` (conversión de datos según la tabla de equivalencias de la spec); nuevos `se_vende`, `se_compra`, `se_fabrica`, `peso_kg` (12,4), `volumen_m3` (12,6); se eliminan `controla_lote` y `prefijo_lote`. CHECK: al menos una casilla; servicio sin `se_fabrica`, sin peso ni volumen; `precio_venta > 0` si y solo si `se_vende` | A |
| `catalog_receta_componente` (nueva) | `producto`, `componente`, `cantidad_por_unidad` (14,4 > 0); único (producto, componente); CHECK producto ≠ componente. Se llena desde `Presentacion` (granel × contenido + materiales) y se eliminan `Presentacion` y `PresentacionMaterial` | B |
| `catalog_producto` | Nuevos `isc_sistema` (`ESPECIFICO` o nulo = no afecto), `isc_codigo_tipo_sistema`; `contenido_litros` pasa a ser la unidad de control (> 0 si afecto). Se elimina `isc_categoria` | C |
| `catalog_producto_isc_tasa` (nueva) | `producto`, `vigente_desde`, `monto_por_litro` (10,4 > 0), `creado_por`; único (producto, fecha); trigger de solo inserción (`fn_rechazar_cambio`). Se llena copiando las tarifas de la categoría de cada producto; luego se eliminan `IscCategoria` e `IscTarifa` (y su trigger) | C |

### Archivos y responsabilidades

| Archivo | Cambio | RF |
|---|---|---|
| `catalog/domain/tipos.py` | `TipoProducto` = `BIEN`, `SERVICIO` | 37 |
| `catalog/domain/producto.py` | `DatosProducto` con casillas, peso y volumen; `validar_producto()` por casilla (al menos una, servicio sin fabricar ni inventario, precio si se vende); `campos_requeridos()` por casillas; sin lote | 37 a 40, 42, 43 |
| `catalog/domain/receta.py` (reemplaza `presentacion.py`) | `validar_receta()` (≥ 1 componente, cantidades > 0, sin repetidos ni el propio producto) y `hay_ciclo(grafo, producto, componentes)`; `componentes_para(receta, cantidad)` (4 decimales half-up) | 41 |
| `catalog/domain/isc.py` | Se conserva `tarifa_aplicable` e `isc_linea`; `contenido_sugerido(receta, unidades)` = suma de los componentes en L | 45, 46 |
| `catalog/application/productos.py` | `CrearProducto`/`EditarProducto` con receta opcional y casillas; `AgregarTasaIsc`; se retiran `isc.py` (categorías) y la presentación | 37 a 46 |
| `catalog/application/fachada.py` | `ProductoDTO` con `tipo` y casillas; `activos(se_vende=…, se_compra=…, se_fabrica=…)`; `receta(producto)` y `componentes_para(producto, cantidad)` (reemplazan `presentacion`/`materiales_para`, para 0005); `isc_aplicable`/`isc_de_linea` leen las tasas del producto | 41, 45, 46 |
| `catalog/interfaces/forms.py`, `views.py`, plantillas | Encabezado con tipo (radio) y casillas; pestañas por casilla; Producción = receta (filas de componentes con cualquier producto activo); Ventas = precio, "Afecto a ISC", sistema, código, tasas (lista + "Nueva tasa") y litros por unidad sugeridos; Inventario = stock mínimo, vida útil, peso, volumen; listado filtra por tipo y casilla; se retira la pantalla de categorías de ISC y su menú | 37 a 46 |
| `catalog/interfaces/api.py` | `tipo` y `se_vende`, `se_compra`, `se_fabrica` | 47 |

### Decisiones

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Reutilizar la columna `tipo` con los valores nuevos | Columna nueva `naturaleza` | Un solo concepto; la conversión es de datos |
| Receta en el catálogo (una por producto, sin versiones) | Recetas versionadas en producción | La OP copia los componentes (0005a RF-PRD-37): las versiones no hacen falta |
| Ciclos detectados en el dominio con el grafo de recetas | Trigger recursivo en la base | La regla vive en el dominio (art. 7.3); el grafo de una empresa es chico |
| Tasas de ISC por producto con solo inserción | Editar la tasa en el producto | Art. 5.1: vigencia y trazabilidad de cada tasa |
| Una migración por etapa, con conversión de datos reversible hasta eliminar las tablas viejas | Una sola migración grande | Cada etapa queda en verde y se puede revisar por separado |

### Tests

- **Unitarios:** `test_producto.py` reescrito por casillas; `test_receta.py` (validación, ciclos, componentes por cantidad); `test_isc.py` (tasa aplicable, contenido sugerido).
- **Casos de uso:** `test_productos.py`, `test_historial.py`, `test_maestros.py` adaptados; `test_receta_uc.py`; `test_isc_producto.py` (tasa nueva, inmutable, con movimientos).
- **Integración:** conversión de datos (cada tipo viejo → casillas; presentación → receta; categoría → tasas copiadas); triggers (`UPDATE` sobre tasas falla); pantallas por casilla.
- **Aceptación:** los escenarios `@borrador` de UC-CAT-08 pasan a ejecutarse; los de 0002b y 0002c se reescriben a receta e ISC en la ficha.

*Notas de la etapa C (2026-10-10):* `ProductoIscTasa.producto_id` sin FK, como el historial (las tasas sobreviven a la eliminación del producto). Marcar "Afecto a ISC" exige registrar su primera tasa; cambiar el ISC o agregar una tasa exige `catalogo.isc.gestionar` (sin ese permiso los campos se ven bloqueados). Las conversiones de 0007 y 0008 ejecutan `SET CONSTRAINTS ALL IMMEDIATE` antes de alterar tablas (PostgreSQL no altera con FK diferidas pendientes), y borran los modelos viejos con `DeleteModel` para que la migración se pueda revertir; `tests/catalog/integration/test_conversion.py` lo verifica de punta a punta.

## Enmienda 5: Familias pasan a llamarse "Categorías" y formulario propio en maestros (RF-CAT-49 a 51)

Aprobada por el PO (2026-10-10) tras las capturas de referencia de Odoo ("familias es categoría y se puede editar").

### Modelo de datos y migración

| Tabla / Modelo | Cambio | Motivo |
|---|---|---|
| `catalog_familia` → `catalog_categoria` (`Categoria`) | `RenameModel` de `Familia` a `Categoria`; nuevo campo `descripcion = models.TextField(blank=True)`; constraint `categoria_unica_sin_mayusculas` | RF-CAT-49, 50 |
| `catalog_producto` (`Producto`) | `RenameField` de `familia` a `categoria` | RF-CAT-49 |

Migración: `0009_familias_a_categorias.py`.

### Dominio y Casos de uso

- `DatosProducto`: campo `categoria_id: int | None = None` (reemplaza `familia_id`).
- `catalog/application/productos.py`: `AGRUPACIONES = ("categoria", "marca")`. `GuardarAgrupacion` acepta `descripcion: str = ""` y `activo: bool | None = None`. `EliminarAgrupacion` y `CambiarEstadoAgrupacion` aplican a `"categoria"`.
- Repositorio `CatalogoOrm`: consultas a `categoria` y `categoria_id`; `guardar_agrupacion` guarda nombre, descripción (solo categorías) y estado en una sola operación.

### Interfaz y Patrón de maestros (ADR-12)

- Menú: "Categorías" (`/catalogo/categorias/`, icono `categorias`). Sin alias de "familia" en código, rutas ni plantillas (art. 7.6).
- URLs: `/catalogo/categorias/` (`views.categorias`).
- Plantilla `_maestro.html`: cuando `nuevo` o `editando` está presente (`?nuevo=1` o `?editar=<id>`), muestra únicamente el formulario con sus migas específicas ("Inicio / Maestro / Nuevo" o "… / Editar") y botones Guardar y Cancelar, **sin renderizar la tabla**. Sin esos parámetros, renderiza el listado normal.
- Formulario de categorías (`agrupaciones.html`): `nombre`, `descripcion` y casilla `activo`.
- Pestaña General de la ficha de producto y listado: selector y columna "Categoría", link "Administrar categorías".
- API: campo `categoria` en la respuesta JSON.

