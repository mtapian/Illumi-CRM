# Spec 0002a — Catálogo: unidades y productos

Estado: implementada (2026-10-10) · enmienda 1 (ficha estilo Odoo) implementada · enmienda 2 (marcas y listado de maestros) implementada · enmienda 3 (unidades de fábrica) implementada · **enmienda 4 (Bien o Servicio) implementada** · **enmienda 5 (familias → categorías) implementada (2026-10-10)**

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
- H5 (enmienda 1): Como usuario del catálogo, quiero ver cada producto en una ficha con pestañas (como en Odoo), con su desglose de impuestos y su historial de cambios, para entenderlo de un vistazo sin mezclar datos de ventas, compras e inventario.

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

- RF-CAT-01: CUANDO se registra una empresa, EL SISTEMA le crea las unidades UND (NIU), KG (KGM), G (GRM), L (LTR) y ML (MLT). *(Enmienda 3, PO 2026-10-10)* También CAJA (BX), DOC (DZN), MT (MTR), PAQ (PK) y SERV (ZZ). Las empresas ya registradas no cambian.
- RF-CAT-02: CUANDO un usuario con `catalogo.unidad.gestionar` crea una unidad con nombre, abreviatura y código SUNAT, EL SISTEMA la guarda si la abreviatura no existe en la empresa.
- RF-CAT-03: SI se intenta eliminar una unidad en uso, ENTONCES EL SISTEMA lo rechaza y ofrece desactivarla. SI se intenta desactivar una unidad usada por productos activos, ENTONCES EL SISTEMA lo rechaza.

### UC-CAT-02 Gestionar productos por tipo

- RF-CAT-04: CUANDO un usuario crea o edita un producto, EL SISTEMA pide los campos comunes (SKU, nombre, tipo, unidad, familia opcional, stock mínimo, activo) y solo los campos propios del tipo elegido. *(Enmienda 1)* La ficha se organiza en pestañas, y cada una aparece solo si aplica al tipo:
  - **General:** nombre, SKU, tipo, unidad, familia, marca (opcional, enmienda 2), referencia y código de barras.
  - **Ventas:** solo en vendibles; precio de lista, categoría de ISC y desglose del precio.
  - **Compras:** solo en comprables; proveedores del producto (spec 0002d).
  - **Inventario:** stock mínimo, control de lote, vida útil y prefijo de lote.
  - **Producción:** solo en `TERMINADO`; su presentación (spec 0002b).
- RF-CAT-05: CUANDO el tipo es `TERMINADO`, EL SISTEMA pide además precio de lista, categoría de ISC (opcional), vida útil en días y su presentación (UC-CAT-03).
- RF-CAT-06: CUANDO el tipo es `MERCADERIA`, EL SISTEMA pide además precio de lista, categoría de ISC (opcional), contenido en litros por unidad (obligatorio si la categoría de ISC cobra por litro) e indicar si controla lote; si controla lote, pide una vida útil sugerida en días. No pide presentación ni receta.
- RF-CAT-07: CUANDO el tipo es `GRANEL`, EL SISTEMA exige la unidad litros y pide vida útil (opcional) y prefijo de lote (por defecto, las 3 primeras letras del nombre).
- RF-CAT-08: SI el SKU ya existe en la empresa, ENTONCES EL SISTEMA rechaza el producto (RN-CAT-01).
- RF-CAT-09: SI el producto tiene movimientos de inventario, ENTONCES EL SISTEMA no permite cambiar su SKU, tipo, unidad ni si controla lote (RN-CAT-01, RN-CAT-02, RN-CAT-03).
- RF-CAT-10: SI crear o activar un producto supera el límite de productos activos del plan, ENTONCES EL SISTEMA lo rechaza (RN-CAT-07). Cuentan los productos activos de todos los tipos.
- RF-CAT-11: SI un `TERMINADO` no tiene vida útil mayor a 0 días, ENTONCES EL SISTEMA lo rechaza (RN-CAT-09).
- RF-CAT-12: EL SISTEMA trata siempre como productos con lote a los `GRANEL` y los `TERMINADO`, y a la `MERCADERIA` solo si el usuario lo indicó al crearla (RN-CAT-03).
- RF-CAT-13: EL SISTEMA solo permite precio de venta y venta en productos `TERMINADO` y `MERCADERIA` (RN-CAT-06).
- RF-CAT-14: CUANDO el usuario consulta el listado, EL SISTEMA permite buscar por SKU o nombre y filtrar por tipo, familia, marca *(enmienda 2)*, estado y stock bajo, paginado de 25 en 25.

### UC-CAT-06 Ficha del producto (enmienda 1, referencia visual: Odoo)

- RF-CAT-29: CUANDO un usuario con `catalogo.producto.gestionar` cambia el tipo de un producto sin movimientos de inventario, EL SISTEMA lo valida con las reglas del tipo nuevo y descarta los campos que no corresponden. SI el producto tiene movimientos, ENTONCES el tipo no se puede cambiar (RF-CAT-09).
- RF-CAT-30: CUANDO se muestra un producto vendible, EL SISTEMA desglosa su precio de lista (que ya incluye impuestos) en valor sin impuestos, ISC por unidad e IGV, con el IGV y la tarifa de ISC vigentes hoy. Ejemplo: "S/ 12.00 = valor 9.34 + ISC 0.83 + IGV 1.83" (base del IGV = 12.00 / 1.18 = 10.17; IGV = 12.00 − 10.17; valor = 10.17 − ISC). El desglose es informativo; cada venta calcula sus impuestos a su fecha de emisión (épica 0006).
- RF-CAT-31: EL SISTEMA permite registrar una referencia interna (texto libre) y un código de barras, ambos opcionales. SI el código de barras ya existe en otro producto de la empresa, ENTONCES EL SISTEMA lo rechaza con "El código de barras ya está asignado a <SKU>".
- RF-CAT-32: CUANDO se crea un producto o cambia cualquiera de sus datos, su estado o su presentación, EL SISTEMA lo registra en el historial del producto con autor, fecha, valor anterior y valor nuevo. La ficha muestra ese historial, del más reciente al más antiguo. El historial no se edita ni se borra.

### UC-CAT-07 Maestros del catálogo (enmienda 2, referencia visual del PO)

- RF-CAT-33: CUANDO un usuario con `catalogo.producto.gestionar` crea o edita una marca, EL SISTEMA guarda su nombre si no existe otra con el mismo nombre en la empresa, sin distinguir mayúsculas. EL SISTEMA permite activarla, desactivarla y eliminarla. SI una marca la usa algún producto, ENTONCES EL SISTEMA no la elimina y ofrece desactivarla. MIENTRAS una marca está inactiva, EL SISTEMA no la ofrece al crear o editar productos; los productos que ya la tienen la conservan.
- RF-CAT-34: EL SISTEMA permite las mismas operaciones de RF-CAT-33 sobre las familias, con las mismas reglas.
- RF-CAT-35: CUANDO un usuario con `catalogo.unidad.gestionar` edita una unidad, EL SISTEMA guarda su nombre y su código SUNAT. SI algún producto usa la unidad, ENTONCES EL SISTEMA no permite cambiar su abreviatura.
- RF-CAT-36: EL SISTEMA lista cada maestro (unidades, familias y marcas; las categorías de ISC se retiraron con la enmienda 4) con migas de pan, un buscador por nombre (y abreviatura en unidades), la cantidad de productos que lo usan, su estado, y las acciones editar y eliminar; si está en uso, eliminar se reemplaza por desactivar. Las categorías de ISC no se eliminan: sus tarifas son inmutables (RF-CAT-24).

### UC-CAT-04 Desactivar producto

- RF-CAT-19: CUANDO un producto se desactiva, EL SISTEMA deja de ofrecerlo en compras, recetas, envasados y ventas nuevas, y lo sigue mostrando en el historial y los reportes.
- RF-CAT-20: SI el producto tiene stock mayor a 0, ENTONCES EL SISTEMA no lo desactiva e indica qué hacer primero (RN-CAT-08). *(Enmienda 4)* Un producto usado en recetas sí se puede desactivar: deja de ofrecerse y las recetas lo conservan (la receta es opcional y la OP copia y edita sus componentes).
- RF-CAT-21: SI se intenta eliminar un producto con movimientos, o usado en una receta, una presentación o un pedido, ENTONCES EL SISTEMA lo rechaza y ofrece desactivarlo. Un producto sin movimientos ni referencias sí se puede eliminar.

## Enmienda 4 (aprobada 2026-10-10): Bien o Servicio, casillas de gestión y receta

**Pedido del PO (2026-10-10, capturas de Odoo):** "todo es un bien o un servicio; en producción se puede tomar cualquier producto del catálogo". Con casillas de gestión de ventas y compras, y peso y volumen en Inventario.

**Qué cambia:** los 5 tipos (`INSUMO`, `ENVASE`, `GRANEL`, `TERMINADO`, `MERCADERIA`) se reemplazan por 2 tipos y 3 casillas. Lo que hoy decide el tipo (precio, presentación, ISC) pasa a decidirlo cada casilla. **El lote deja de ser un dato del producto** (PO, 2026-10-10): se registra en el inventario que ingresa (compra, ajuste) o en la orden de producción.

| Hoy | Con la enmienda 4 |
|---|---|
| `INSUMO`, `ENVASE` | Bien · se compra |
| `MERCADERIA` | Bien · se compra · se vende |
| `GRANEL` | Bien · se fabrica |
| `TERMINADO` (presentación) | Bien · se fabrica · se vende; su presentación pasa a ser su **receta** |
| — | Servicio (delivery, alquiler de barril, maquila…): sin stock, lote ni kardex |

### UC-CAT-08 Tipo y gestión del producto

- RF-CAT-37: EL SISTEMA clasifica cada producto como **Bien** o **Servicio**. MIENTRAS un producto es Servicio, EL SISTEMA no le lleva stock, lote, kardex, stock mínimo, peso ni volumen; su unidad por defecto es SERV (ZZ).
- RF-CAT-38: EL SISTEMA muestra en el encabezado de la ficha las casillas **Se vende**, **Se compra** y **Se fabrica** (esta última solo en bienes). Al crear un Bien, viene marcada "Se compra"; al crear un Servicio, "Se vende". SI no se marca ninguna, ENTONCES EL SISTEMA rechaza el producto con "Marca al menos una opción: se vende, se compra o se fabrica".
- RF-CAT-39: MIENTRAS un producto **se vende**, EL SISTEMA muestra la pestaña Ventas y exige un precio de lista mayor a 0 (reemplaza RN-CAT-06: deja de depender del tipo). MIENTRAS **se compra**, muestra la pestaña Compras (0002d). MIENTRAS **se fabrica**, muestra la pestaña Producción con su receta (opcional).
- RF-CAT-40: EL SISTEMA no guarda el lote en el producto: no hay "controla lote" ni "prefijo de lote". El lote (código y vencimiento) se registra en cada ingreso de inventario (opcional por línea en compras y ajustes, épicas 0003 y 0004) y en cada orden de producción (obligatorio, con código sugerido, épica 0005). EL SISTEMA permite registrar en la pestaña Inventario una **vida útil** en días, opcional y mayor a 0, que solo **sugiere** el vencimiento del lote (fecha de ingreso o de producción + vida útil); el vencimiento real se edita en el lote. Reemplaza RN-CAT-03 y RN-CAT-09.
- RF-CAT-41: CUANDO un Bien se fabrica, EL SISTEMA permite definirle una **receta**, que es **opcional** y se puede cambiar en cualquier momento. La receta tiene **uno o varios componentes**: cualquier producto activo del catálogo (bien o servicio, fabricado o no, salvo él mismo y sin ciclos), cada uno con una cantidad por unidad del producto mayor a 0, en la unidad del componente. La orden de producción usa la receta para precargar sus componentes (0005a); un Bien sin receta también se puede producir, cargando los componentes en la propia orden. La receta reemplaza la presentación de 0002b: p. ej. "IPA botella 330 ml" = 0.33 L de "IPA a granel" + 1 botella + 1 tapa + 0.0417 caja; o "IPA a granel" = solo 0.2 kg de malta por litro, con un único componente.
- RF-CAT-42: EL SISTEMA permite registrar en la pestaña Inventario de un Bien el **peso** (kg) y el **volumen** (m³) por unidad, opcionales y mayores o iguales a 0. Son informativos: ningún cálculo los usa.
- RF-CAT-43: SI el producto tiene movimientos de inventario, ENTONCES EL SISTEMA no permite cambiar si es Bien o Servicio, su SKU ni su unidad (reemplaza RF-CAT-09). Las casillas de gestión sí pueden cambiar; desmarcar "Se vende" o "Se compra" no afecta documentos ya emitidos.
- RF-CAT-44: CUANDO se aplica la enmienda, EL SISTEMA convierte los productos existentes según la tabla de equivalencias, y la presentación de cada terminado pasa a ser su receta, con el granel como un componente más (contenido en litros por unidad). "Controla lote" y "prefijo de lote" se descartan (aún no hay lotes registrados: el inventario es la épica 0003); la vida útil se conserva como sugerencia. No se pierde ningún otro dato ni historial; la conversión no agrega entradas al historial de cada producto (PO, 2026-10-10).

- RF-CAT-45 (ISC, en la ficha del producto; PO 2026-10-10): EL SISTEMA muestra en la pestaña Ventas de un **Bien que se vende** la casilla **Afecto a ISC**; un Servicio nunca lleva ISC. CUANDO se marca, EL SISTEMA pide en la misma ficha: (1) el **sistema de cálculo** (en el MVP solo Específico, S/ por litro); (2) el **código de tipo de sistema** para el comprobante; (3) la **tasa** con su fecha de vigencia (p. ej. S/ 2.51 por litro desde 2024-07-01); y (4) la **unidad de control**: el contenido en litros por unidad de venta, mayor a 0 (botella 330 ml = 0.33 L; caja de 12 × 330 ml = 3.96 L; producto vendido en L = 1, no se pide). SI el bien se fabrica y su receta tiene componentes medidos en L, ENTONCES EL SISTEMA **sugiere** el contenido como la suma de esos componentes, editable. Se retiran las **categorías de ISC** de 0002c.
- RF-CAT-46 (ISC): CUANDO cambia la tasa de un producto, EL SISTEMA la registra como una **tasa nueva con su fecha de vigencia** en el historial de tasas del producto; las anteriores no se editan ni se borran, y cada venta usa la tasa vigente a su fecha de emisión (conserva RF-CAT-24 y 25 y la constitución, art. 5.1). SI el bien afecto a ISC tiene movimientos de inventario, ENTONCES EL SISTEMA no permite cambiar su contenido en litros (conserva RF-CAT-18). Desmarcar "Afecto a ISC" deja de calcularlo en ventas futuras y conserva su historial de tasas. El cálculo (cantidad × litros por unidad × tasa vigente), la base del IGV (valor + ISC), el desglose del precio (RF-CAT-30), las entregas gratuitas y las notas de crédito siguen como en 0002c y 0006–0007.

- RF-CAT-47: CUANDO se consulta la API `GET /api/v1/productos/`, EL SISTEMA devuelve `tipo` (`BIEN` o `SERVICIO`) y `se_vende`, `se_compra`, `se_fabrica`, en lugar del tipo anterior, sin versión nueva de la API (aún no hay integraciones; PO, 2026-10-10).
- Límite del plan (RF-CAT-10, sin cambio): cuentan los productos activos, sean bienes o servicios (PO, 2026-10-10).

- RF-CAT-48 (ISC, conversión): CUANDO se aplica la enmienda, EL SISTEMA copia a cada producto con categoría de ISC su sistema, su código de tipo de sistema y todas las tarifas de la categoría con sus fechas, y retira la pantalla de categorías; ninguna tasa ni fecha se pierde.

[NECESITA ACLARACIÓN] **ISC Al valor y Precio de Venta al Público:** la referencia del PO menciona tres sistemas (Específico, Al valor, PVP). El MVP solo tiene el Específico, validado con el contador (S/ 2.51 por litro desde 2024-07-01). Propuesta: dejar Al valor y PVP fuera de esta enmienda y agregarlos a 0002c cuando el contador confirme si aplican a algún producto del piloto (constitución, art. 5.5).

**RF que se reemplazan al aprobarse:** RF-CAT-04 a 07 (campos por tipo → por casilla), RF-CAT-09 (→ RF-CAT-43), RF-CAT-11 y 12 (lote y vida útil por tipo → RF-CAT-40), RF-CAT-13 (venta por tipo → RF-CAT-39), RF-CAT-29 (cambio de tipo → RF-CAT-43); en 0002b, RF-CAT-15 a 17 (presentación → receta, RF-CAT-41). Se conservan RF-CAT-18 (los cambios rigen para producciones futuras) y el contenido en litros por unidad para el ISC (RF-CAT-26), que pasa a ser un campo de la pestaña Ventas de cualquier producto con categoría de ISC.

**Impacto en specs en borrador (se ajustan tras la aprobación, antes de implementarlas):**
- **0003a:** el stock es por producto × almacén × lote, con lote opcional; un ingreso o ajuste de entrada puede traer lote y vencimiento (sugerido por la vida útil). MIENTRAS un producto tenga stock con lote, las salidas piden el lote y sugieren el que vence primero (FEFO). Los servicios no generan movimientos.
- **0004a:** se compra cualquier producto con "Se compra" (también servicios, sin ingreso a almacén); cada línea de un bien admite lote y vencimiento opcionales.
- **0005a / 0005b:** la receta y el envasado se unifican en "producir un bien con una orden de producción, precargada desde su receta si la tiene". El envasado pasa a ser una producción cuyo componente es otro bien fabricado con lote: el producto hereda ese código de lote (hoy RN-PRD-07) y la merma se registra sobre ese componente. El costo unitario sale de lo consumido en la orden de producción.
- **0006a / 0006b:** se vende cualquier producto con "Se vende"; un servicio no descuenta stock. El faltante a fabricar se calcula con la receta.
- **0002c:** las categorías de ISC se retiran; sistema, código, tasas con vigencia y contenido en litros pasan a la ficha del producto (RF-CAT-45, 46 y 48). Se conservan las reglas de cálculo (RF-CAT-23 a 27).

**Fuera de alcance de esta enmienda:** atributos y variantes, punto de venta, política de facturación, combos, responsable, plazo de entrega al cliente y notas para recepciones, entregas y traslados (aparecen en la referencia de Odoo).

**Resuelto (PO, 2026-10-10):** un Servicio no se fabrica; "Se fabrica" es solo para bienes. Un servicio sí puede ser componente de una receta o de una OP (p. ej. maquila de un tercero): suma su costo sin mover stock.

## Enmienda 5: las familias se llaman "categorías" (aprobada e implementada, 2026-10-10)

**Pedido del PO (2026-10-10, captura "Editar categoría"):** "familias es categoría y se puede editar".

- RF-CAT-49: EL SISTEMA llama **Categoría** a lo que hasta ahora se llamaba "familia", en todas las pantallas, filtros, menú y API. Las reglas de RF-CAT-34 no cambian (nombre único sin mayúsculas, se edita, se activa o desactiva, y se elimina solo si ningún producto la usa). No hay ninguna otra "categoría" en el catálogo: las de ISC se retiraron con la enmienda 4.
- RF-CAT-50: CUANDO un usuario con `catalogo.producto.gestionar` crea o edita una categoría, EL SISTEMA muestra un formulario propio con **nombre** (obligatorio), **descripción** (opcional, texto libre) y la casilla **Categoría activa**, con los botones Guardar y Cancelar y migas "Inicio / Categorías / Nueva" o "… / Editar". Desactivarla desde el formulario sigue las reglas de RF-CAT-33.
- RF-CAT-51 (patrón de listado, ADR-12): EL SISTEMA abre "Nuevo …" y el lápiz de todos los maestros (unidades, categorías, marcas) en su propia página de formulario, sin la tabla, como en la referencia del PO.

## Requisitos no funcionales

- RNF-CAT-01: La búsqueda del listado responde en menos de 800 ms (p95) con 10 000 productos por empresa (PRD §7).

## Casos límite

- Cambiar el precio de lista no afecta pedidos ya confirmados (guardan su precio).
- Dos productos con el mismo nombre y distinto SKU: se permite.
- *(Enmienda 1)* Cambiar el tipo de un producto que otros usan (granel de una presentación, material, receta o pedido) se rechaza con "No se puede cambiar el tipo: lo usan otros productos (presentaciones, recetas o pedidos)", aunque no tenga movimientos: la referencia dejaría de ser válida.
- *(Enmienda 1)* Un terminado que cambia a otro tipo pierde su presentación.
- *(Enmienda 1)* Guardar sin cambios no agrega una fila al historial. El historial sobrevive a la eliminación de un producto sin movimientos.
- Dos altas o activaciones simultáneas cuando queda un solo cupo del plan: en el MVP pueden pasar ambas y superar el límite en 1 (ver "Fuera de alcance").

## Fuera de alcance

Conversión de unidad de compra a unidad de uso, variantes, listas de precios por canal o cliente, imágenes múltiples, ISC al valor o por precio de venta al público, materiales "por empaque" (1 caja cada 24 unidades).

*(Enmienda 1)* Tampoco se toman de Odoo: imagen del producto, variantes, peso y volumen, punto de venta, mensajes y actividades del registro.

**Pospuesto por el PO (2026-10-10), para una iteración posterior:** que el límite de productos activos del plan (RF-CAT-10) se respete también con altas o activaciones simultáneas (bloqueo por empresa al contar los activos). Hoy se valida sin bloqueo.

## Criterios de finalización

- El piloto carga su catálogo real (insumos, envases, 3+ estilos, 6+ presentaciones y su mercadería de reventa) sin campos ambiguos.
- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- **PRD Q7 (resuelta por el PO con el valor por defecto, 2026-10-10): vida útil por presentación, obligatoria.** Pregunta original: ¿la vida útil va por presentación (botella vs. barril) o por estilo? Hoy es por presentación y obligatoria.
- [NECESITA ACLARACIÓN] **Cerveza que entra sin producir:** ¿hay maquila o compra de cerveza a granel? Si la hay, `GRANEL` y `TERMINADO` deberían poder comprarse. ¿La cerveza de terceros que se revende paga ISC de nuevo? (contador)
