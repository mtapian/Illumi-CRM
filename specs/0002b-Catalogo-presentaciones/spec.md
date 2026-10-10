# Spec 0002b — Catálogo: presentaciones y materiales

Estado: aprobada (PO, 2026-10-10)

Épica E02 (Catálogo), parte 2 de 3. Depende de: 0002a. La usan: 0005.

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

- H1: Como maestro cervecero, quiero definir cada presentación con su granel, su contenido y sus materiales por unidad, para que el envasado descuente lo correcto y calcule el costo.

## Definiciones

- **Presentación:** definición de un `TERMINADO` = granel de origen + contenido en litros + materiales (`ENVASE`) por unidad. Ejemplo: "IPA botella 330 ml" = IPA a granel × 0,330 L + 1 botella + 1 tapa + 1 etiqueta + 1/24 de caja x24.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-CAT-03 Definir presentación y sus materiales

- RF-CAT-15: CUANDO un usuario define la presentación de un `TERMINADO`, EL SISTEMA exige un granel activo, un contenido mayor a 0 L y al menos un material (RN-CAT-04).
- RF-CAT-16: SI un material no es de tipo `ENVASE` o su cantidad por unidad no es mayor a 0, ENTONCES EL SISTEMA lo rechaza. Se admiten fracciones (p. ej. 0,0417 caja por botella) (RN-CAT-05).
- RF-CAT-17: EL SISTEMA permite varias presentaciones para un mismo granel.
- RF-CAT-18: CUANDO cambian los materiales de una presentación con stock, EL SISTEMA aplica el cambio solo a los envasados futuros; el costo del stock existente no cambia. SI se intenta cambiar el contenido en litros de una presentación con movimientos, ENTONCES EL SISTEMA lo rechaza, porque ese contenido define el ISC de las unidades ya envasadas.

## Requisitos no funcionales

- RNF-CAT-02: Las cantidades por unidad de material admiten 4 decimales (RN-GEN-09).

## Casos límite

- Los barriles retornables no son material de la presentación (PRD, supuesto 3): "IPA barril 20 L" = IPA a granel × 20 L + 1 precinto + 1 etiqueta de barril.
- La fracción de caja (0,0417 × 240 botellas = 10,008 cajas) acumula una diferencia de redondeo; se acepta en el MVP.

## Fuera de alcance

Conversión de unidad de compra a unidad de uso, variantes, listas de precios por canal o cliente, imágenes múltiples, código de barras, ISC al valor o por precio de venta al público, materiales "por empaque" (1 caja cada 24 unidades).

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- Ninguna.
