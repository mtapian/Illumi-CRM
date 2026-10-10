# Spec 0002a — Catálogo: unidades y productos

Estado: aprobada (PO, 2026-10-10)

Épica E02 (Catálogo), parte 1 de 3. Depende de: 0001a, 0001c. La usan: 0002b, 0002c y 0003–0008.

## Contexto y objetivo

Una cervecera maneja cinco tipos de ítems que se comportan distinto:
- insumos que se consumen en recetas;
- envases que se consumen al envasar;
- cerveza a granel en tanques;
- presentaciones propias que se venden (botellas, latas, barriles);
- **mercadería de reventa** que se compra y se vende sin producirla (agua, snacks, merchandising, cerveza de terceros).

El sistema de referencia trata todo como "producto vendible" con stock entero.

**Objetivo:** que cada ítem se registre con los datos que su tipo necesita, y que las reglas de compra, producción, venta, lote e ISC dependan del tipo y no de la memoria del usuario.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Administrador, Gerente, Producción, Almacén | Crean y mantienen productos, presentaciones y unidades (`catalogo.producto.gestionar`, `catalogo.unidad.gestionar`) |
| Ventas | Consulta el catálogo (`catalogo.producto.ver`) |
| Administrador | Configura las categorías y tarifas de ISC (`catalogo.isc.gestionar`) |

## Historias de usuario

- H1: Como usuario de almacén, quiero tener las unidades de medida con su código SUNAT para comprar y vender en la unidad correcta.
- H2: Como usuario de producción, quiero registrar insumos, envases, graneles, presentaciones y mercadería con los campos que corresponden a cada uno, para no cargar datos que no se usan.
- H3: Como gerente, quiero desactivar productos que ya no uso sin perder su historial.
- H4: Como vendedor, quiero vender agua, snacks o merchandising que se compran listos, sin pasar por producción.

## Definiciones

| Tipo | Ejemplo | Unidad típica | Se compra | Se produce | Se vende | Lote |
|---|---|---|:-:|:-:|:-:|:-:|
| `INSUMO` | Malta Pilsen, lúpulo Cascade, levadura US-05 | KG, G, UND | ✔ | — | — | — (R2) |
| `ENVASE` | Botella ámbar 330 ml, tapa corona, etiqueta IPA, caja x24, precinto de barril | UND | ✔ | — | — | — |
| `GRANEL` | IPA a granel, Stout a granel | L (obligatorio) | — | ✔ (OP) | — | ✔ siempre |
| `TERMINADO` | IPA botella 330 ml, IPA barril 20 L | UND | — | ✔ (envasado) | ✔ | ✔ siempre |
| `MERCADERIA` | Agua 500 ml, papas fritas, polo de la marca | UND (u otra) | ✔ | — | ✔ | Opcional (sí si es perecible) |

- **Precio de lista:** precio final de venta, con IGV e ISC incluidos.

- **Familia:** agrupación libre de productos para buscar y filtrar (p. ej. "Maltas", "Snacks"). No tiene efecto tributario y no se confunde con la categoría de ISC.

- **Presentación:** ver spec 0002b. **Categoría de ISC:** ver spec 0002c.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-CAT-01 Gestionar unidades de medida

- RF-CAT-01: CUANDO se registra una empresa, EL SISTEMA le crea las unidades UND (NIU), KG (KGM), G (GRM), L (LTR) y ML (MLT).
- RF-CAT-02: CUANDO un usuario con `catalogo.unidad.gestionar` crea una unidad con nombre, abreviatura y código SUNAT, EL SISTEMA la guarda si la abreviatura no existe en la empresa.
- RF-CAT-03: SI se intenta eliminar una unidad en uso, ENTONCES EL SISTEMA lo rechaza y ofrece desactivarla. SI se intenta desactivar una unidad usada por productos activos, ENTONCES EL SISTEMA lo rechaza.

### UC-CAT-02 Gestionar productos por tipo

- RF-CAT-04: CUANDO un usuario crea o edita un producto, EL SISTEMA pide los campos comunes (SKU, nombre, tipo, unidad, familia opcional, stock mínimo, activo) y solo los campos propios del tipo elegido.
- RF-CAT-05: CUANDO el tipo es `TERMINADO`, EL SISTEMA pide además precio de lista, categoría de ISC (opcional), vida útil en días y su presentación (UC-CAT-03).
- RF-CAT-06: CUANDO el tipo es `MERCADERIA`, EL SISTEMA pide además precio de lista, categoría de ISC (opcional), contenido en litros por unidad (obligatorio si la categoría de ISC cobra por litro) e indicar si controla lote; si controla lote, pide una vida útil sugerida en días. No pide presentación ni receta.
- RF-CAT-07: CUANDO el tipo es `GRANEL`, EL SISTEMA exige la unidad litros y pide vida útil (opcional) y prefijo de lote (por defecto, las 3 primeras letras del nombre).
- RF-CAT-08: SI el SKU ya existe en la empresa, ENTONCES EL SISTEMA rechaza el producto (RN-CAT-01).
- RF-CAT-09: SI el producto tiene movimientos de inventario, ENTONCES EL SISTEMA no permite cambiar su SKU, tipo, unidad ni si controla lote (RN-CAT-01, RN-CAT-02, RN-CAT-03).
- RF-CAT-10: SI crear o activar un producto supera el límite de productos activos del plan, ENTONCES EL SISTEMA lo rechaza (RN-CAT-07). Cuentan los productos activos de todos los tipos.
- RF-CAT-11: SI un `TERMINADO` no tiene vida útil mayor a 0 días, ENTONCES EL SISTEMA lo rechaza (RN-CAT-09).
- RF-CAT-12: EL SISTEMA trata siempre como productos con lote a los `GRANEL` y los `TERMINADO`, y a la `MERCADERIA` solo si el usuario lo indicó al crearla (RN-CAT-03).
- RF-CAT-13: EL SISTEMA solo permite precio de venta y venta en productos `TERMINADO` y `MERCADERIA` (RN-CAT-06).
- RF-CAT-14: CUANDO el usuario consulta el listado, EL SISTEMA permite buscar por SKU o nombre y filtrar por tipo, familia, estado y stock bajo, paginado de 25 en 25.

### UC-CAT-04 Desactivar producto

- RF-CAT-19: CUANDO un producto se desactiva, EL SISTEMA deja de ofrecerlo en compras, recetas, envasados y ventas nuevas, y lo sigue mostrando en el historial y los reportes.
- RF-CAT-20: SI el producto tiene stock mayor a 0, o es un granel con presentaciones activas, ENTONCES EL SISTEMA no lo desactiva e indica qué hacer primero (RN-CAT-08).
- RF-CAT-21: SI se intenta eliminar un producto con movimientos, o usado en una receta, una presentación o un pedido, ENTONCES EL SISTEMA lo rechaza y ofrece desactivarlo. Un producto sin movimientos ni referencias sí se puede eliminar.

## Requisitos no funcionales

- RNF-CAT-01: La búsqueda del listado responde en menos de 800 ms (p95) con 10 000 productos por empresa (PRD §7).

## Casos límite

- Cambiar el precio de lista no afecta pedidos ya confirmados (guardan su precio).
- Dos productos con el mismo nombre y distinto SKU: se permite.

## Fuera de alcance

Conversión de unidad de compra a unidad de uso, variantes, listas de precios por canal o cliente, imágenes múltiples, código de barras, ISC al valor o por precio de venta al público, materiales "por empaque" (1 caja cada 24 unidades).

## Criterios de finalización

- El piloto carga su catálogo real (insumos, envases, 3+ estilos, 6+ presentaciones y su mercadería de reventa) sin campos ambiguos.
- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- **PRD Q7 (resuelta por el PO con el valor por defecto, 2026-10-10): vida útil por presentación, obligatoria.** Pregunta original: ¿la vida útil va por presentación (botella vs. barril) o por estilo? Hoy es por presentación y obligatoria.
- [NECESITA ACLARACIÓN] **Cerveza que entra sin producir:** ¿hay maquila o compra de cerveza a granel? Si la hay, `GRANEL` y `TERMINADO` deberían poder comprarse. ¿La cerveza de terceros que se revende paga ISC de nuevo? (contador)
