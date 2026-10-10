# Spec 0005b — Producción: envasado, cierre y costo del lote

Estado: borrador

Épica E05 (Producción), parte 2 de 2. Depende de: 0005a, 0002b. La usan: 0006.

## Contexto y objetivo

La cervecera produce a pedido: cocina un lote de un estilo (cientos de litros), lo fermenta durante semanas y luego lo envasa en varias presentaciones (botella, lata, barril). Hoy no sabe cuánto le costó cada lote, cuánto se perdió en el camino ni qué lote terminó en manos de qué cliente.

**Objetivo:** conocer el costo real de cada lote y de cada botella o barril, con trazabilidad desde la receta hasta el envasado.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Producción (maestro cervecero) | Gestiona recetas, planifica, inicia, termina y cierra OP, registra envasados |
| Gerente / Administrador | Además anula OP y consulta el costo del lote |

## Historias de usuario

- H1: Como maestro cervecero, quiero envasar un lote en varias presentaciones a la vez, registrando la merma, para que el costo de cada botella y barril sea el real.
- H2: Como gerente, quiero ver el costo y el rendimiento de cada lote para saber qué estilo me deja más margen.

## Definiciones

- **Costo por litro efectivo del envasado:** costo del granel consumido / litros envasados (la merma de envasado se absorbe en el costo).

- **Costo unitario de una presentación:** contenido × costo por litro efectivo + Σ costo de materiales por unidad.

- **Receta, OP, lote, rendimiento, costo por litro del lote y ejemplo de referencia:** ver spec 0005a.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-PRD-06 Registrar envasado

- RF-PRD-20: CUANDO un usuario con `produccion.envasado.registrar` envasa una OP `TERMINADA` indicando las unidades por presentación y los litros de merma, EL SISTEMA:
  1. saca del lote de granel los litros envasados + la merma, al costo promedio del granel;
  2. saca los materiales de cada presentación (unidades × cantidad por unidad), al costo promedio;
  3. ingresa cada presentación con el **mismo código de lote** del granel y vencimiento = fecha de envasado + vida útil de la presentación (RN-PRD-07);
  4. asigna a cada presentación su costo unitario según Definiciones.
- RF-PRD-21: SI Σ (unidades × contenido) + merma supera el granel disponible del lote, ENTONCES EL SISTEMA rechaza el envasado e indica los litros requeridos y disponibles (RN-PRD-05).
- RF-PRD-22: SI una presentación no es del granel de la OP, ENTONCES EL SISTEMA la rechaza (RN-PRD-05).
- RF-PRD-23: SI falta algún material, ENTONCES EL SISTEMA rechaza el envasado e indica el material y el faltante, sin registrar ningún movimiento.
- RF-PRD-24: EL SISTEMA conserva el costo en el envasado: Σ costo de las presentaciones = costo del granel consumido + Σ costo de materiales; la diferencia por redondeo (≤ 0.01 por presentación) se asigna a la última (RN-PRD-06).
- RF-PRD-25: CUANDO se envasa la misma presentación del mismo lote en otra fecha, EL SISTEMA suma las unidades al lote existente y conserva el vencimiento más próximo.
- RF-PRD-26: CUANDO un envasado tiene 0 unidades y solo merma (descarte), EL SISTEMA registra la salida de granel como merma, para que aparezca en "Mermas y ajustes" del estado de resultados.
- RF-PRD-27: CUANDO se registra un envasado, EL SISTEMA pasa a `LISTO` los pedidos vinculados en `CONFIRMADO` o `EN_PRODUCCION` cuyo stock queda completo (épica 0006).
- RF-PRD-28: SI dos envasados del mismo lote se registran a la vez, ENTONCES EL SISTEMA valida el segundo contra el saldo real.
- RF-PRD-29: EL SISTEMA permite varios envasados por OP.

### UC-PRD-07 Cerrar OP

- RF-PRD-30: CUANDO el granel del lote llega a 0 tras un envasado, EL SISTEMA cierra la OP automáticamente.
- RF-PRD-31: CUANDO un usuario cierra manualmente una OP con saldo de granel y motivo, EL SISTEMA registra el saldo como merma y la pasa a `CERRADA`.
- RF-PRD-32: CUANDO se cierra una OP, EL SISTEMA pasa a `LISTO` los pedidos vinculados en `CONFIRMADO` o `EN_PRODUCCION` cuyo stock está completo; los que siguen sin cubrirse se evalúan según épica 0006, RF-VEN-41.
- RF-PRD-33: SI se intenta una transición de estado distinta de las de Definiciones, ENTONCES EL SISTEMA la rechaza (RN-PRD-03).

### UC-PRD-08 Consultar costo y rendimiento del lote

- RF-PRD-34: CUANDO un usuario con `produccion.reporte.ver` consulta una OP, EL SISTEMA muestra insumos teóricos vs. reales (cantidad y costo), costo indirecto, litros planificados vs. reales, rendimiento %, costo por litro, envasados por presentación (unidades y costo unitario), merma de envasado (L y % sobre el granel consumido) y saldo de granel.

## Requisitos no funcionales

- RNF-PRD-01: El piloto registra un envasado de 3 presentaciones en menos de 5 minutos de captura (PRD §8).
- RNF-PRD-02: La interfaz de OP y envasado se usa en una tablet en planta.

## Casos límite

- Envasado de 0 unidades (descarte): se registra como merma (RF-PRD-26).
- Dos envasados simultáneos del mismo lote: el segundo valida contra el saldo real.

## Fuera de alcance

Control de proceso (densidades, temperaturas, pH), planificación de tanques y capacidad, mano de obra por OP, recetas multinivel, mermas estándar por receta, producción continua, costeo estándar con variaciones, anulación de envasados.

## Criterios de finalización

- El ejemplo de referencia se reproduce exactamente en una prueba de aceptación.
- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Corrección de errores de digitación:** hoy un envasado o unos litros reales mal ingresados solo se corrigen con ajustes. ¿Se necesita anular un envasado (si su stock está intacto) en el MVP?
- [NECESITA ACLARACIÓN] Wireframes de la OP y del envasado (no existen; el sistema de referencia no tiene producción).
