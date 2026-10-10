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
