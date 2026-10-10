# Spec 0005a — Producción: recetas y órdenes de producción

Estado: borrador

Épica E05 (Producción), parte 1 de 2. Depende de: 0002a, 0003a. La usan: 0005b, 0006.

## Contexto y objetivo

La cervecera produce a pedido: cocina un lote de un estilo (cientos de litros), lo fermenta durante semanas y luego lo envasa en varias presentaciones (botella, lata, barril). Hoy no sabe cuánto le costó cada lote, cuánto se perdió en el camino ni qué lote terminó en manos de qué cliente.

**Objetivo:** conocer el costo real de cada lote y de cada botella o barril, con trazabilidad desde la receta hasta el envasado.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Producción (maestro cervecero) | Gestiona recetas, planifica, inicia, termina y cierra OP, registra envasados |
| Gerente / Administrador | Además anula OP y consulta el costo del lote |

## Historias de usuario

- H1: Como maestro cervecero, quiero recetas versionadas para cambiar una receta sin alterar las OP que ya la usaron.
- H2: Como maestro cervecero, quiero planificar una OP y ver si me faltan insumos antes de empezar.
- H3: Como vendedor, quiero que el sistema me sugiera cuántos litros producir para cubrir un pedido.
- H4: Como maestro cervecero, quiero registrar lo que realmente consumí y los litros que obtuve para conocer el costo por litro del lote.

## Definiciones

- **Receta:** granel (estilo) + volumen base en litros + insumos con su cantidad para ese volumen. Tiene versiones; cada granel tiene una versión activa.

- **OP (orden de producción):** cocción y fermentación de una receta para obtener granel.

- **Lote:** código de trazabilidad del granel producido (`{prefijo}-{correlativo de 4 dígitos}`, p. ej. IPA-0020). Las presentaciones envasadas heredan el mismo código.

- **Rendimiento:** litros reales / litros planificados.

- **Costo por litro del lote:** (costo de insumos consumidos + costo indirecto) / litros reales.

- **Lote perdido:** lote contaminado o descartado cuyos insumos ya se consumieron físicamente.

```
Receta (estilo, versión, volumen base, insumos)
   │
   ▼
OP PLANIFICADA ──iniciar──► EN_PROCESO ──terminar──► TERMINADA ──(granel del lote = 0)──► CERRADA
   │  (sin efecto en stock)   │ salida de insumos      │ entrada de granel (lote)
   ▼                          │ (+ consumos adicionales)├──► Envasado 1 (botellas)
ANULADA ◄────────────────────┘ (revierte consumos)     ├──► Envasado 2 (barriles)
                              └─(0 L, lote perdido)──► CERRADA
```

### Ejemplo de referencia (base de los escenarios)

**Receta IPA v1** — volumen base 500 L: Malta Pilsen 100 kg · Malta Caramelo 10 kg · Lúpulo Cascade 1500 g · Levadura US-05 10 sobres.

| Paso | Detalle | Costo |
|---|---|---|
| Iniciar OP-000020 (500 L) | Malta Pilsen **102 kg** real × 4.00 = 408.00 · Caramelo 10 × 6.00 = 60.00 · Cascade 1500 × 0.12 = 180.00 · US-05 10 × 15.00 = 150.00 | 798.00 |
| Terminar | 425 L reales (rendimiento 85 %) + costo indirecto 52.00 | 850.00 → **2.000000 S/ por L** · lote IPA-0020 |
| Envasado E-000031 | 1000 botellas 330 ml (330 L) + 3 barriles 20 L (60 L) + 19.5 L de merma = 409.5 L de granel | Granel 819.00 → efectivo 819 / 390 = **2.100000 S/ por L** |
| Costo botella | 0.33 × 2.10 = 0.693 + botella 0.85 + tapa 0.05 + etiqueta 0.20 + caja 0.0417 × 2.40 = 0.10008 | **1.893080** |
| Costo barril | 20 × 2.10 = 42.00 + precinto 1.50 | **43.500000** |
| Saldo del lote | 425 − 409.5 = 15.5 L de granel | 31.00 |

Control: entra a terminados 1893.08 + 130.50 = 2023.58 = granel 819.00 + materiales 1204.58 ✔

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-PRD-01 Gestionar recetas versionadas

- RF-PRD-01: CUANDO un usuario con `produccion.receta.gestionar` crea una receta, EL SISTEMA exige un granel, un volumen base mayor a 0 y al menos un insumo; los insumos deben ser productos `INSUMO` activos (RN-PRD-01).
- RF-PRD-02: CUANDO se edita una receta ya usada en una OP, EL SISTEMA crea una versión nueva y las OP existentes conservan la suya (RN-PRD-09).
- RF-PRD-03: EL SISTEMA mantiene una versión activa por granel y permite consultar las anteriores.

### UC-PRD-02 Planificar OP

- RF-PRD-04: CUANDO un usuario con `produccion.op.planificar` crea una OP desde la receta activa (o una versión elegida) con litros, fecha prevista y pedidos vinculados opcionales, EL SISTEMA la guarda como `PLANIFICADA`, sin efecto en el stock.
- RF-PRD-05: CUANDO se planifica una OP, EL SISTEMA calcula la cantidad teórica de cada insumo = cantidad de la receta × litros planificados / volumen base, con 4 decimales (RN-PRD-02).
- RF-PRD-06: SI falta stock de algún insumo, ENTONCES EL SISTEMA lo advierte, pero permite planificar (el insumo puede comprarse antes de iniciar).
- RF-PRD-07: CUANDO se planifica desde un pedido confirmado, EL SISTEMA sugiere los litros por estilo = Σ max(0, faltante de cada presentación) × contenido − granel disponible sin comprometer. El faltante se calcula por presentación, porque el sobrante de barriles no cubre la falta de botellas. El usuario puede editar los litros.

### UC-PRD-03 Iniciar OP

- RF-PRD-08: CUANDO un usuario con `produccion.op.ejecutar` inicia una OP confirmando las cantidades reales de insumos (precargadas con las teóricas) y el almacén de origen, EL SISTEMA registra la salida de los insumos al costo promedio vigente y pasa la OP a `EN_PROCESO`.
- RF-PRD-09: SI falta algún insumo, ENTONCES EL SISTEMA no inicia la OP e indica los faltantes.
- RF-PRD-10: MIENTRAS la OP esté `EN_PROCESO`, EL SISTEMA permite registrar consumos adicionales (p. ej. dry hopping, clarificantes), incluso de insumos fuera de la receta. SI falta stock del insumo, ENTONCES rechaza el consumo adicional.
- RF-PRD-11: CUANDO una OP se inicia, EL SISTEMA pasa a `EN_PRODUCCION` sus pedidos vinculados que estén `CONFIRMADO` (épica 0006).
- RF-PRD-12: SI dos usuarios inician la misma OP a la vez, ENTONCES EL SISTEMA la inicia una sola vez y consume los insumos una sola vez.

### UC-PRD-04 Terminar OP

- RF-PRD-13: CUANDO un usuario termina una OP con litros reales mayores a 0, fecha de fin, almacén de destino y costo indirecto opcional, EL SISTEMA crea el lote del granel (código sugerido editable y único; vencimiento = fecha de fin + vida útil del granel, si está definida), ingresa el granel al costo por litro del lote y pasa la OP a `TERMINADA` (RN-PRD-04).
- RF-PRD-14: SI los litros reales superan los planificados, ENTONCES EL SISTEMA lo permite con una advertencia (rendimiento mayor a 100 %).
- RF-PRD-15: CUANDO se termina una OP con 0 L y motivo (lote perdido), EL SISTEMA no crea lote, pasa la OP a `CERRADA` y registra su costo total como pérdida de producción del período (épica 0008). *Pendiente de aprobación: PRD Q10.*

### UC-PRD-05 Anular OP

- RF-PRD-16: CUANDO un usuario con `produccion.op.anular` anula con motivo una OP `PLANIFICADA`, EL SISTEMA la pasa a `ANULADA` sin efecto en el stock.
- RF-PRD-17: CUANDO se anula una OP `EN_PROCESO`, EL SISTEMA revierte todos sus consumos (incluidos los adicionales) al costo original.
- RF-PRD-18: SI se intenta anular una OP `TERMINADA` o `CERRADA`, ENTONCES EL SISTEMA lo rechaza; las correcciones se hacen con ajustes de inventario (RN-PRD-08).
- RF-PRD-19: CUANDO se anula una OP, EL SISTEMA devuelve a `CONFIRMADO` solo los pedidos vinculados que estén `EN_PRODUCCION` y no tengan otra OP vinculada en proceso; los demás pedidos no cambian (épica 0006, RF-VEN-41).

## Requisitos no funcionales

- RNF-PRD-02: La interfaz de OP y envasado se usa en una tablet en planta.

## Casos límite

- Rendimiento mayor a 100 %: se permite con advertencia.
- Lote perdido: no se anula la OP (eso devolvería al stock insumos que ya se usaron); se termina con 0 L (RF-PRD-15).
- OP del mismo estilo que se superponen en fermentación: el costo de la botella sale del costo promedio del granel, no exactamente del lote (ver dudas).

## Fuera de alcance

Control de proceso (densidades, temperaturas, pH), planificación de tanques y capacidad, mano de obra por OP, recetas multinivel, mermas estándar por receta, producción continua, costeo estándar con variaciones, anulación de envasados.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **PRD Q10:** ¿se aprueba el lote perdido con 0 L (RF-PRD-15)? Escenarios marcados `@pendiente-q10`.
- [NECESITA ACLARACIÓN] **Contador (PRD Q12):** costeo del granel: ¿promedio del producto (hoy) o costo específico por lote? Con OP superpuestas del mismo estilo, el costo de la botella no es exactamente el del lote.
- [NECESITA ACLARACIÓN] **Contador (PRD Q12):** el costo indirecto manual por OP puede duplicar gastos de planta registrados como gasto operativo. ¿Se mantiene, se vincula a un gasto o se elimina en el MVP?
- [NECESITA ACLARACIÓN] Wireframes de la OP y del envasado (no existen; el sistema de referencia no tiene producción).
