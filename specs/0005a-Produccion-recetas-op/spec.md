# Spec 0005a — Producción: órdenes de producción

Estado: **implementada** (2026-10-12; aprobada por el PO: "procede") · RF-PRD-47 ajustado (componentes opcionales, PO 2026-10-12) · **enmienda 1 (varios productos de salida) aprobada ("ok") e implementada (2026-10-12)** · consolidada el 2026-10-12 con la enmienda 4 de 0002a (OP de cualquier producto, referencia Odoo) y las decisiones del PO del 2026-10-11 y 2026-10-12; **absorbe 0005b** (envasado, cierre y costo del lote), que se retira

Épica E05 (Producción). Depende de: 0002a (receta, enmienda 4), 0003a (inventario y lotes). La usan: 0008b (costo y pérdidas de producción).

## Contexto y objetivo

La cervecera produce a pedido: cocina un lote de un estilo (cientos de litros), lo fermenta durante semanas y luego lo envasa en varias presentaciones (botella, lata, barril). Hoy no sabe cuánto le costó cada lote, cuánto se perdió en el camino ni qué lote terminó en cada botella.

**Objetivo:** registrar cada producción como una orden (OP) que consume componentes y obtiene un producto con su lote, para conocer el costo real de cada lote y de cada unidad envasada, con trazabilidad del lote desde el granel hasta la botella.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Producción (maestro cervecero) | Crea, edita, inicia y finaliza OP |
| Gerente / Administrador | Además anula OP y consulta sus costos |

## Historias de usuario

- H1: Como maestro cervecero, quiero crear una OP desde la receta del producto y ajustar sus componentes para producir lo que realmente voy a usar.
- H2: Como maestro cervecero, quiero ver si tengo los componentes disponibles antes de producir.
- H3: Como maestro cervecero, quiero registrar lo que realmente consumí y lo que obtuve, con su lote, para que el stock y el costo del lote sean reales.
- H4: Como gerente, quiero ver el costo, la merma y el rendimiento de cada OP.

## Definiciones

- **OP (orden de producción):** fabricación de una cantidad de un **bien que se fabrica** (0002a, RF-CAT-38), a partir de una lista de **componentes** (cualquier producto activo del catálogo). La cocción del granel y el envasado son OP: el envasado es una OP del producto envasado que consume el granel de un lote.
- **Receta:** componentes por unidad del producto (0002a, RF-CAT-41). Es opcional; la OP copia sus componentes y la copia es de la OP.
- **Por consumir:** cantidad prevista de un componente = cantidad por unidad × cantidad de la OP, con 4 decimales.
- **Merma de un componente:** consumido real − por consumir (negativa si se usó menos).
- **Rendimiento:** cantidad producida / cantidad programada.
- **Costo unitario del producto:** (costo de los componentes consumidos + costo indirecto) / cantidad producida, con 6 decimales (constitución, art. 4.1). Los bienes se consumen al costo promedio vigente (art. 4.2).
- **Lote perdido:** OP finalizada con cantidad producida 0: sus componentes se consumieron, pero no se obtuvo producto.

**Estados** (PO, 2026-10-11: los mismos nombres que la compra, 0004a):

```
Creada ──► En proceso ──► Finalizada        (Anulada, fuera de la barra)
   │            │            └─ consume componentes e ingresa el producto con su lote
   └──► Anulada ◄┘            (todo en una sola operación; antes no hay movimientos)
```

### Ejemplo de referencia (base de los escenarios)

**OP-000001 · GRA-IPA (IPA a granel, en L) · 500 L.** Receta por litro: Malta Pilsen 0.2 kg · Malta Caramelo 0.02 kg · Lúpulo Cascade 3 g · Levadura US-05 0.02 sobres.

| Componente | Por consumir | Consumido real | Costo promedio | Costo |
|---|---|---|---|---|
| Malta Pilsen | 100 kg | **102 kg** (merma 2 kg) | 4.00 | 408.00 |
| Malta Caramelo | 10 kg | 10 kg | 6.00 | 60.00 |
| Lúpulo Cascade | 1500 g | 1500 g | 0.12 | 180.00 |
| Levadura US-05 | 10 sobres | 10 sobres | 15.00 | 150.00 |

Finalizada con **425 L** (rendimiento 85 %) y costo indirecto 52.00: (798.00 + 52.00) / 425 = **2.000000 S/ por L**, lote **IPA-0020**.

**OP-000002 · TER-IPA-330 (botella 330 ml) · 1000 UND.** Componentes: GRA-IPA 0.33 L, botella 1, tapa 1, etiqueta 1, caja x24 0.0417 por unidad.

| Componente | Por consumir | Consumido real | Costo |
|---|---|---|---|
| GRA-IPA (lote IPA-0020) | 330 L | **340 L** (merma 10 L) | 340 × 2.00 = 680.00 |
| Botella ámbar 330 ml | 1000 | 1000 | × 0.85 = 850.00 |
| Tapa corona | 1000 | 1000 | × 0.05 = 50.00 |
| Etiqueta IPA | 1000 | 1000 | × 0.20 = 200.00 |
| Caja x24 | 41.7 | 41.7 | × 2.40 = 100.08 |

Finalizada con 1000 UND: 1880.08 / 1000 = **1.880080 S/ por botella**, lote sugerido **IPA-0020** (el del único componente con lote). Saldo de granel del lote: 425 − 340 = 85 L a 2.000000.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-PRD-01 Crear y preparar una OP

- RF-PRD-36: CUANDO un usuario con `produccion.op.planificar` crea una OP, EL SISTEMA pide el **producto** (un bien activo que se fabrica), la **cantidad** en su unidad (mayor a 0, 4 decimales), la fecha programada, el almacén de origen de los componentes y el de destino del producto (sugerido el almacén principal), el responsable (RF-PRD-35) y un **comentario** opcional de texto libre (p. ej. el pedido que atiende; PO, 2026-10-12: sin vínculo con los pedidos), y la guarda como **Creada** con un número correlativo por empresa (`OP-000001`), sin efecto en el stock.
- RF-PRD-35: CUANDO se crea una OP, EL SISTEMA le asigna un responsable, que por defecto es quien la crea y puede cambiarse por otro usuario activo de la empresa con `produccion.op.ejecutar`.
- RF-PRD-37: EL SISTEMA muestra en la OP un campo **Receta**, opcional, que propone la receta del producto si la tiene. CUANDO se elige, EL SISTEMA **copia** sus componentes a la OP con su cantidad por consumir. Si se deja vacío, la OP empieza sin componentes. Editar la lista de la OP no cambia la receta, y cambiar después la receta no altera las OP existentes.
- RF-PRD-38: MIENTRAS la OP está Creada o En proceso, EL SISTEMA permite agregar, quitar y cambiar componentes con **cualquier producto activo del catálogo** salvo el propio producto, sin mover stock, y cambiar su cantidad, fechas, almacenes, responsable y comentario. Un usuario que además tiene `catalogo.producto.gestionar` puede **guardar los componentes de la OP como la receta del producto** (por unidad = por consumir / cantidad de la OP).
- RF-PRD-39: EL SISTEMA muestra junto a cada componente que es un bien su disponibilidad: **Disponible** si el stock del almacén de origen cubre lo por consumir, **No disponible** si no. La disponibilidad solo informa: no impide crear ni editar la OP.
- RF-PRD-44: SI un componente es un **servicio** (p. ej. una maquila de un tercero), ENTONCES EL SISTEMA no le muestra disponibilidad ni le mueve stock, y le pide su costo en S/ (2 decimales, ≥ 0), que suma al costo del producto.
- RF-PRD-45: CUANDO un usuario con `produccion.op.ejecutar` pasa una OP Creada a **En proceso**, EL SISTEMA solo cambia su estado (indica que la producción empezó) y registra quién y cuándo.

### UC-PRD-02 Finalizar una OP

- RF-PRD-41: CUANDO un usuario con `produccion.op.ejecutar` **finaliza** una OP En proceso indicando la cantidad real consumida de cada componente (precargada con lo por consumir), el lote a consumir de cada componente con lotes (sugerido según la estrategia de salida del producto, FEFO o FIFO; 0003a y 0002a enmienda 6), la **cantidad producida**, la **fecha de fin** (sugerida hoy, no futura) y el costo indirecto opcional (S/, 2 decimales, ≥ 0; PO, 2026-10-12), EL SISTEMA, en una sola operación: registra la salida de cada componente al costo promedio vigente; ingresa el producto al almacén de destino a su costo unitario (Definiciones), con su **lote obligatorio**; y deja la OP **Finalizada**. Los movimientos y el ingreso del lote llevan la fecha de fin.
- RF-PRD-46: CUANDO se finaliza una OP, EL SISTEMA sugiere el código del lote del producto: SI la OP consume un solo componente con lote, el de ese componente (la botella de IPA-0020 es IPA-0020); si no, el SKU del producto con un correlativo. Sugiere el vencimiento como la fecha de fin + la vida útil del producto, si la tiene. Ambos son editables; si el lote ya existe para el producto, se suma a él y debe tener el mismo vencimiento (0003a, RF-INV-26).
- RF-PRD-09: SI algún componente no tiene stock suficiente en el almacén y lote indicados, ENTONCES EL SISTEMA no finaliza la OP, indica cada faltante y no registra ningún movimiento.
- RF-PRD-12: SI dos usuarios finalizan la misma OP a la vez, ENTONCES EL SISTEMA la finaliza una sola vez y consume los componentes una sola vez.
- RF-PRD-14: SI la cantidad producida supera la programada, ENTONCES EL SISTEMA lo permite con una advertencia (rendimiento mayor a 100 %).
- RF-PRD-15: CUANDO se finaliza una OP con cantidad producida 0 y un motivo (**lote perdido**; PO, 2026-10-12, resuelve Q10), EL SISTEMA consume sus componentes, no ingresa producto ni crea lote, y registra el costo total (componentes + costo indirecto) como **pérdida de producción** de la OP a su fecha de fin, para el estado de resultados (0008b). Sin motivo, una cantidad producida 0 se rechaza.
- RF-PRD-47: SI el producto ya no está activo o ya no se fabrica, ENTONCES EL SISTEMA no finaliza la OP e indica el motivo. *(PO, 2026-10-12)* Los componentes **no son obligatorios**: una OP sin componentes se finaliza y el costo del producto es solo su costo indirecto (0 si no tiene).

### UC-PRD-03 Anular una OP

- RF-PRD-16: CUANDO un usuario con `produccion.op.anular` anula con motivo una OP Creada o En proceso, EL SISTEMA la deja **Anulada** sin efecto en el stock (aún no tiene movimientos) y registra quién, cuándo y por qué.
- RF-PRD-18: SI se intenta anular una OP Finalizada, ENTONCES EL SISTEMA lo rechaza: se corrige con un ajuste de inventario trazable (constitución, art. 4.5).
- RF-PRD-33: SI se intenta una transición distinta de las de Definiciones (p. ej. finalizar una OP Creada, editar una Finalizada o Anulada), ENTONCES EL SISTEMA la rechaza.

### UC-PRD-04 Consultar OP y su costo

- RF-PRD-48: CUANDO un usuario con `produccion.op.ver` abre el listado de OP, EL SISTEMA lo muestra con la grilla estándar (docs/ux.md §5): número, producto, cantidad programada y producida, fecha programada, responsable y estado, con filtros por estado, producto, fechas y número.
- RF-PRD-34: CUANDO un usuario con `produccion.reporte.ver` consulta una OP Finalizada, EL SISTEMA muestra su pestaña **Costos**: por cada componente, por consumir vs. consumido (cantidad y costo) y su merma (RF-PRD-42); el costo indirecto; la cantidad programada vs. producida y el rendimiento %; el costo total y el costo unitario del producto. Sin `inventario.costo.ver` (0001c, RF-TEN-51) los importes no se muestran.
- RF-PRD-42: EL SISTEMA calcula la merma de cada componente como consumido real − por consumir; queda en el costo del producto (no se registra aparte).

## Enmienda 1: varios productos de salida (aprobada e implementada, 2026-10-12)

**Pedido del PO (2026-10-12):** "el lote de producción puede generar más de 1 producto". Casos: envasar un granel en varias presentaciones a la vez (botellas, latas, barriles) y una producción que da varios productos distintos. Decisiones del PO: el costo se reparte **por un factor de cada producto**; **cada producto lleva su propio lote**.

- RF-PRD-49: EL SISTEMA permite que una OP tenga **uno o varios productos de salida**, cada uno un bien activo que se fabrica, sin repetirse, con su **cantidad programada** (mayor a 0) y su **factor de reparto** (mayor a 0, 4 decimales). El factor sugerido es el contenido en litros por unidad del producto, si lo tiene (botella 0.33, barril 20), y si no, 1; es editable. Reemplaza el producto y la cantidad únicos de RF-PRD-36.
- RF-PRD-50: CUANDO se pide usar la receta, EL SISTEMA copia la receta de **cada** producto de salida por su cantidad programada, y cada componente copiado queda **asignado** a esa salida. Un mismo componente puede estar asignado a varias salidas (el granel en la botella y en el barril). Ajusta RF-PRD-37.
- RF-PRD-51: EL SISTEMA permite que cada componente quede **asignado a una salida** (es costo directo de ella) o **común** (sin asignar; p. ej. la mano de obra de un servicio o un insumo compartido). Ajusta RF-PRD-38.
- RF-PRD-52: CUANDO se finaliza la OP, EL SISTEMA pide la **cantidad producida** y el **lote** de cada salida (RF-PRD-46 por salida: sugerido el del único lote que consumen sus componentes asignados, si lo hay; si no, el SKU de esa salida con un correlativo). Ingresa cada salida con producción mayor a 0 a su costo unitario (6 decimales):
  - costo de la salida = sus componentes asignados + (componentes comunes + costo indirecto) × (producida × factor) / Σ (producida × factor) de todas las salidas;
  - el redondeo a céntimos se ajusta en la última salida, para que la suma sea exactamente el costo total de la OP;
  - los componentes asignados a una salida con producción 0 se suman a los comunes;
  - SI todas las salidas tienen producción 0, ENTONCES es un lote perdido (RF-PRD-15).
  Ajusta RF-PRD-41, 42 y 46.
- RF-PRD-53: EL SISTEMA muestra en la pestaña Costos, por cada salida, la cantidad programada y producida, el rendimiento, el lote, el costo total y el unitario (ajusta RF-PRD-34), y en el listado de OP sus productos de salida (ajusta RF-PRD-48).

**Ejemplo (envasado en dos presentaciones):** granel GRA-IPA del lote IPA-0020 a 2.00 por litro. Salidas: 1000 botellas 330 ml (factor 0.33) y 3 barriles 20 L (factor 20). Componentes asignados: botella → granel 330 L, botella, tapa, etiqueta y caja; barril → granel 60 L y precinto 3 × 1.50. Común: servicio de limpieza S/ 39.00. Producidas 1000 y 3: Σ = 1000 × 0.33 + 3 × 20 = 390; la botella recibe 39 × 330/390 = 33.00 y el barril 39 × 60/390 = 6.00. Lote sugerido de cada salida: IPA-0020 (cada una consume solo ese lote de granel).

| Salida | Asignados | Común | Costo | Unitario |
|---|---|---|---|---|
| TER-IPA-330 × 1000 | 660.00 + 850.00 + 50.00 + 200.00 + 100.08 = 1860.08 | 33.00 | 1893.08 | **1.893080** |
| TER-IPA-20L × 3 | 120.00 + 4.50 = 124.50 | 6.00 | 130.50 | **43.500000** |

Control: 1893.08 + 130.50 = 2023.58 = granel 780.00 + materiales 1204.58 + común 39.00.

## Requisitos no funcionales

- RNF-PRD-02: La OP se usa en una tablet en planta: se puede crear, editar y finalizar a 768 px de ancho sin scroll horizontal.

## Casos límite

- Rendimiento mayor a 100 %: se permite con advertencia (RF-PRD-14).
- Lote perdido: la OP no se anula (eso dejaría en stock lo que ya se usó); se finaliza con 0 y motivo (RF-PRD-15).
- Envasar un lote en varias presentaciones: una OP por presentación; cada una consume del mismo lote de granel, y el saldo del lote se ve en el stock (0003c).
- Granel de dos OP del mismo estilo en stock a la vez: cada OP de envasado consume al costo promedio del granel (art. 4.2), no al costo exacto del lote; el lote sirve para la trazabilidad.
- Componente sin stock al crear: se advierte (No disponible), pero la OP se crea; el faltante se valida al finalizar (RF-PRD-09).
- Un componente que se desactiva después de copiado: sigue en la OP; no tiene stock (0002a no deja desactivar con stock), así que la OP no se finaliza mientras no se quite.

## Fuera de alcance

Vínculo de la OP con pedidos (sugerir OP desde un pedido, cambiar el estado de los pedidos; solo el comentario libre), recetas versionadas, recetas multinivel y OP encadenadas, control de proceso (densidades, temperaturas, pH), planificación de tanques y capacidad, centros de trabajo y tiempos por operación, mano de obra por OP, mermas estándar por receta, costeo estándar con variaciones, costo específico por lote, anulación de una OP finalizada.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.
- Prueba de reconciliación: tras varias OP encadenadas (granel → envasado), el kardex reproduce stock y valor de cada producto (constitución, art. 4.6).

## Impacto en otras specs

- **0005b:** se retira; el envasado es una OP (RF-PRD-41, 46), la merma está en RF-PRD-42 y el costo en RF-PRD-34. El cierre de la OP desaparece: el saldo de un lote se ve en el stock.
- **0001b / 0001c:** las funcionalidades `produccion.recetas` (la receta está en el catálogo, 0002a) y `produccion.envasado` (el envasado es una OP) se retiran del catálogo de accesos; las plantillas de rol se ajustan en el plan.
- **0006a / 0006b:** los pedidos no cambian de estado por las OP (RF-PRD-11, 19, 27 y 32 se retiran); se revisan al reescribir esas specs.
- **0008b:** lee la pérdida de producción (RF-PRD-15) y el costo de las OP.

## RF retirados (historia)

RF-PRD-01 a 03 (recetas versionadas: la receta es del producto, 0002a) · RF-PRD-04 a 06 (→ RF-PRD-36, 37, 39) · RF-PRD-07 y 43 (sugerir desde pedidos: fuera de alcance) · RF-PRD-08 y 10 (consumo al iniciar y adicionales → RF-PRD-38, 41) · RF-PRD-11, 19, 27, 32 (estados de pedidos) · RF-PRD-13 (→ RF-PRD-41, 46) · RF-PRD-17 (anular revertía consumos: ya no hay) · RF-PRD-20 a 31 de 0005b (envasado y cierre → OP).

## Dudas abiertas

- ~~Enmienda 1: ¿una OP creada con un producto se puede convertir en varias salidas?~~ **Resuelta (PO, 2026-10-12): sí**, mientras esté Creada o En proceso, editando sus salidas en la ficha (RF-PRD-38 y 49).

- [NECESITA ACLARACIÓN] **Contador (Q12):** el costo indirecto manual por OP (opcional, PO 2026-10-12) puede duplicar gastos de planta registrados como gasto operativo (0008a). ¿Algún reparo?
- [NECESITA ACLARACIÓN] **Contador:** la pérdida de producción de un lote perdido (RF-PRD-15), ¿va como costo de producción del período o como gasto (desmedro)? ¿Requiere sustento?
