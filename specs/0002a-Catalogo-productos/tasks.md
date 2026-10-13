# Tareas 0002a — Catálogo: unidades y productos

Estado: **implementada** (2026-10-10). 16/16 tareas hechas; escenarios en verde salvo 1 parcial anotado.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [x] **T1. Crear `TipoProducto` y sus capacidades (comprable, producible, vendible, lote).** — RF-CAT-12, RF-CAT-13
  - Hecho cuando: `test_producto.py` comprueba la tabla de tipos de la spec: `GRANEL` y `TERMINADO` siempre con lote, `MERCADERIA` según lo elegido, y solo `TERMINADO` y `MERCADERIA` vendibles.

- [x] **T2. Implementar `campos_requeridos(tipo)` y `validar_producto()`.** — RF-CAT-04 a RF-CAT-07, RF-CAT-11
  - Hecho cuando: un test por tipo comprueba los campos pedidos; un `GRANEL` sin litros y un `TERMINADO` con vida útil 0 se rechazan.

- [x] **T3. Implementar `cambios_prohibidos()` y `cabe_en_limite()`.** — RF-CAT-09, RF-CAT-10
  - Hecho cuando: un test comprueba que con movimientos no se cambian SKU, tipo, unidad ni lote, y que el límite cuenta los activos de todos los tipos.

- [x] **T4. Implementar `puede_desactivar()` y `puede_eliminar()`.** — RF-CAT-20, RF-CAT-21
  - Hecho cuando: un test comprueba que no se desactiva con stock > 0 ni un granel con presentaciones activas, y que solo se elimina sin movimientos ni referencias.

## Persistencia

- [x] **T5. Crear los modelos de unidad, familia y producto, con sus constraints.** — RF-CAT-04, RF-CAT-08
  - Hecho cuando: la migración se aplica y un test comprueba `UNIQUE(empresa_id, sku)` y el `CHECK` de tipos.
  - Nota: los `CHECK` usan `IS NOT NULL` explícito: en PostgreSQL un CHECK que da NULL se acepta (un vendible sin precio pasaba).

- [x] **T6. Crear el sembrador de unidades iniciales y registrarlo en 0001a.** — RF-CAT-01
  - Hecho cuando: después de registrar una empresa existen UND, KG, G, L y ML con su código SUNAT.

- [x] **T7. Crear los puertos `InventarioConsultaPort` y `ReferenciasPort`, con implementaciones falsas para tests.** — RF-CAT-09, RF-CAT-20, RF-CAT-21
  - Hecho cuando: los casos de uso de productos se prueban con los falsos; las implementaciones reales llegan con 0003, 0005 y 0006.
  - Nota: `catalog.application.puertos.puertos`: inventario (0003) reemplaza `puertos.inventario`; recetas (0005) y pedidos (0006) agregan `puertos.referencias`. Hasta entonces no hay stock ni movimientos (`SinInventario`).

## Casos de uso

- [x] **T8. Crear el CRUD de unidades: alta, desactivar y eliminar.** — RF-CAT-02, RF-CAT-03
  - Hecho cuando: "Unidad en uso no se elimina" está en verde y una unidad usada por productos activos no se desactiva.

- [x] **T9. Crear `CrearProducto` y `EditarProducto` con validación por tipo y límite del plan.** — RF-CAT-04 a RF-CAT-13
  - Hecho cuando: "Crear productos de cada tipo", "Granel con unidad distinta a litros", "SKU duplicado en la misma empresa", "El mismo SKU en otra empresa sí se permite", "Campos inmutables después de tener movimientos" y "Límite de productos del plan" están en verde.
  - Nota: el límite de productos no toma lock (comentario `ponytail:`): dos altas simultáneas en el último cupo podrían pasar ambas.

- [x] **T10. Soportar `MERCADERIA` con precio, lote opcional y vida útil sugerida.** — RF-CAT-06, RF-CAT-12, RF-CAT-13
  - Hecho cuando: "Crear mercadería de reventa perecible" y "Mercadería no perecible sin lote" están en verde.

- [x] **T11. Crear `DesactivarProducto` y `EliminarProducto`.** — RF-CAT-19 a RF-CAT-21
  - Hecho cuando: "No se desactiva un producto con stock", "No se desactiva un granel con presentaciones activas", "Eliminar producto sin movimientos" y "No se elimina un producto con movimientos" están en verde.

- [x] **T12. Crear la fachada `CatalogoQuery` (`producto`, `activos(tipo)`).** — RF-CAT-13, RF-CAT-19
  - Hecho cuando: "Producto desactivado no se ofrece en operaciones nuevas" está en verde: `activos()` no devuelve inactivos.
  - Nota: "Producto desactivado no se ofrece…" queda parcial: las pantallas de compras (0004a) y recetas (0005a) usarán `CatalogoQuery.activos()`.

## Pantallas

- [x] **T13. Crear el listado `/catalogo/productos/` con búsqueda, filtros y paginación de 25.** — RF-CAT-14, RNF-CAT-01
  - Hecho cuando: `test_listado.py` comprueba los filtros y que la búsqueda con 10 000 productos responde en menos de 800 ms (p95).
  - Nota: el filtro "stock bajo" recorre los productos con mínimo (`ponytail:`); la épica 0003 lo resuelve con SQL. La prueba de 10 000 productos mide p95 < 800 ms.

- [x] **T14. Crear el formulario por tipo y la ficha con campos bloqueados si hay movimientos.** — RF-CAT-04 a RF-CAT-09
  - Hecho cuando: un test de vista comprueba que el formulario de `INSUMO` no muestra precio y que la ficha bloquea el SKU de un producto con movimientos.
  - Nota: con movimientos, SKU, unidad y lote se muestran con candado y la pantalla ignora lo enviado; el caso de uso además lo rechaza.

- [x] **T15. Crear la API `GET /api/v1/productos` para n8n.** — (RF-TEN-48)
  - Hecho cuando: un test con token comprueba que devuelve solo productos de la empresa, paginados.

## Cierre

- [x] **T16. Verificar la spec completa.** — RF-CAT-01 a RF-CAT-14, RF-CAT-19 a RF-CAT-21
  - Hecho cuando: `pytest tests/catalog tests/acceptance -k E02a` en verde; lint en verde; cada RF con escenario `@RF-CAT-…` o test; `MEMORY.md` actualizado.


## Enmienda 1: ficha estilo Odoo (en borrador, pendiente de aprobación del PO)

- [x] **T17. Mover `diferencias()` a `shared/domain/auditoria.py`.** — RF-CAT-32
  - Hecho cuando: tenancy lo importa desde `shared` y sus tests siguen en verde.
- [x] **T18. Implementar `desglose_precio()`.** — RF-CAT-30
  - Hecho cuando: `test_precio.py` comprueba S/ 12.00 con IGV 18 % e ISC 0.83 → valor 9.34, IGV 1.83, y sin ISC → valor 10.17.
- [x] **T19. Agregar referencia, código de barras y el modelo de historial con su trigger.** — RF-CAT-31, RF-CAT-32
  - Hecho cuando: un test comprueba el código de barras único por empresa (vacío permitido en varios) y que un `UPDATE` o `DELETE` sobre el historial falla.
- [x] **T20. Registrar el historial en los casos de uso y permitir cambiar el tipo sin movimientos.** — RF-CAT-29, RF-CAT-32
  - Hecho cuando: `test_historial.py` comprueba creación, edición (antes → después), cambio de estado y cambio de tipo; con movimientos el tipo no cambia.
- [x] **T21. Crear el registro de pestañas externas (`catalog/interfaces/pestanas.py`).** — RF-CAT-04
  - Hecho cuando: un test registra una pestaña de prueba y la ficha la muestra solo para los tipos indicados.
- [x] **T22. Rehacer la ficha: encabezado, pestañas, selector de tipo, desglose y panel de historial.** — RF-CAT-04, RF-CAT-29 a RF-CAT-32
  - Hecho cuando: un test de vista comprueba qué pestañas ve cada tipo, el desglose de un vendible y el historial; y los escenarios de la enmienda están en verde.
- [x] **T23. Verificar la enmienda.** — RF-CAT-04, RF-CAT-29 a RF-CAT-32
  - Hecho cuando: suite, lint, contratos y migraciones en verde; cada RF nuevo con escenario o test; `MEMORY.md` actualizado.

## Enmienda 2: marcas y listado de maestros

- [x] **T24. Modelo `Marca`, `Producto.marca` y unicidad sin mayúsculas en familias y marcas.** — RF-CAT-33, RF-CAT-34
  - Hecho cuando: la migración aplica y un test comprueba "Gloria" y "gloria" como duplicados.
- [x] **T25. Casos de uso de agrupaciones (familia y marca) y `EditarUnidad`.** — RF-CAT-33 a RF-CAT-35
  - Hecho cuando: `test_maestros.py` cubre duplicado, eliminar en uso, desactivar y abreviatura bloqueada.
- [x] **T26. Marca en la ficha y en el filtro del listado de productos.** — RF-CAT-04, RF-CAT-14
  - Hecho cuando: un test guarda la marca desde la ficha, no ofrece marcas inactivas y filtra por marca.
- [x] **T27. Patrón de listado de maestro (migas, buscador, conteo, acciones) en unidades, familias y marcas.** — RF-CAT-36
  - Hecho cuando: un test de vista busca, cuenta productos y da 404 al editar un elemento de otra empresa.
- [x] **T28. Categorías de ISC con el mismo patrón.** — RF-CAT-36
  - Hecho cuando: el listado muestra la tarifa vigente y los productos, y `?editar=` muestra sus tarifas.
- [x] **T29. Verificar la enmienda 2.** — RF-CAT-33 a RF-CAT-36
  - Hecho cuando: suite, lint, contratos y migraciones en verde; escenarios `@UC-CAT-07` en verde; `MEMORY.md` actualizado.

## Enmienda 3: unidades de fábrica

- [x] **T30. Sembrar también CAJA, DOC, MT, PAQ y SERV al registrar una empresa.** — RF-CAT-01
  - Hecho cuando: el test de registro comprueba las 10 unidades con su código SUNAT.

## Enmienda 4: Bien o Servicio, receta e ISC en la ficha

### Etapas A y B (juntas, ver plan): tipo, casillas y receta
- [x] **T31. Dominio: `BIEN`/`SERVICIO`, casillas, peso y volumen, validación por casilla, sin lote.** — RF-CAT-37 a 40, 42, 43
  - Hecho cuando: `test_producto.py` cubre al menos una casilla, servicio sin fabricar ni inventario, precio si se vende, vida útil opcional.
- [x] **T32. Migración A con conversión de datos y CHECK nuevos.** — RF-CAT-44
  - Hecho cuando: un test de conversión comprueba cada tipo viejo → casillas, y los CHECK rechazan un producto sin casillas y un servicio que se fabrica.
- [x] **T33. Casos de uso, historial y límite del plan con el modelo nuevo.** — RF-CAT-37 a 43
  - Hecho cuando: `test_productos.py` y `test_historial.py` en verde con bienes y servicios.
- [x] **T34. Ficha: tipo y casillas en el encabezado, pestañas por casilla, Inventario con peso y volumen; listado y API.** — RF-CAT-38, 39, 42, 47
  - Hecho cuando: tests de vista por casilla y de la API con `tipo` y casillas; escenarios UC-CAT-08 de tipo, casillas y peso en verde.

### Etapa B: receta
- [x] **T35. Dominio de la receta: validación, ciclos y componentes por cantidad.** — RF-CAT-41
  - Hecho cuando: `test_receta.py` cubre 1 y varios componentes, sin el propio producto, ciclo A→B→A y redondeo a 4 decimales.
- [x] **T36. Migración B: `receta_componente`, conversión desde presentaciones y retiro de `Presentacion`.** — RF-CAT-41, 44
  - Hecho cuando: un test convierte una presentación (granel × contenido + materiales) en receta sin perder componentes.
- [x] **T37. Receta en casos de uso, fachada (`receta`, `componentes_para`) y pestaña Producción.** — RF-CAT-41
  - Hecho cuando: crear sin receta, agregar una de 1 componente y una de varios; escenarios de receta en verde; features de 0002b reescritas.

### Etapa C: ISC en la ficha
- [x] **T38. Dominio y migración C: ISC en el producto, tasas por producto con trigger, conversión desde categorías.** — RF-CAT-45, 46, 48
  - Hecho cuando: la conversión copia todas las tarifas con sus fechas; un `UPDATE` sobre una tasa falla.
- [x] **T39. `AgregarTasaIsc`, contenido sugerido desde la receta, bloqueo con movimientos y fachada (`isc_aplicable`).** — RF-CAT-45, 46
  - Hecho cuando: `test_isc_producto.py` cubre tasa nueva, fecha repetida, venta antes y después del cambio, contenido sugerido 0.33 y bloqueado con movimientos.
- [x] **T40. Pestaña Ventas con "Afecto a ISC" y tasas; retiro de la pantalla de categorías.** — RF-CAT-45, 46
  - Hecho cuando: test de vista con el bloque de ISC y el desglose; features de 0002c reescritas y en verde; `/catalogo/isc/` ya no existe.

### Cierre
- [x] **T41. Verificar la enmienda 4.** — RF-CAT-37 a 48
  - Hecho cuando: suite, lint, contratos y migraciones en verde; cada RF nuevo con escenario o test; specs 0002b/0002c marcadas como reformuladas; `MEMORY.md` actualizado.

## Enmienda 5: familias → categorías (implementada)

- [x] **T42. Renombrar "familia" a "categoría" en pantallas, filtros, menú, mensajes y API; descripción opcional.** — RF-CAT-49, RF-CAT-50
  - Hecho cuando: ningún texto visible dice "familia"; la categoría guarda su descripción; los tests y escenarios de familias pasan con el nombre nuevo.
- [x] **T43. Formulario propio para nuevo y editar en los maestros (con "activa" en categorías).** — RF-CAT-50, RF-CAT-51
  - Hecho cuando: `?nuevo=1` y `?editar=<id>` muestran solo el formulario con migas, Guardar y Cancelar; un test cubre editar nombre, descripción y estado de una categoría.

## Enmienda 6: estrategia de salida por producto (aprobada, 2026-10-12)

- [x] **T44. Campo `estrategia_salida` (FEFO/FIFO, por defecto FEFO) en el producto, dominio y migración; ficha (pestaña Inventario) y fachada (`ProductoDTO`).** — RF-CAT-62
  - Hecho cuando: un bien guarda y muestra su estrategia; un servicio no la tiene; los productos existentes quedan en FEFO.
- [x] **T45. El inventario asigna lotes según la estrategia (`orden_fifo` junto a `orden_fefo`).** — RF-CAT-62; 0003a RF-INV-22
  - Hecho cuando: el escenario FIFO de 0003a está en verde y los de FEFO siguen en verde.
