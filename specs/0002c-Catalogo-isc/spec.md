# Spec 0002c — Catálogo: categorías y tarifas de ISC

Estado: implementada (2026-10-10)

Épica E02 (Catálogo), parte 3 de 3. Depende de: 0002a. La usan: 0006, 0007.

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

- H1: Como administrador, quiero configurar qué productos pagan ISC y con qué tarifa vigente, porque no todo lo que vendo es cerveza.

## Definiciones

- **Categoría de ISC:** agrupación definida por cada empresa que indica si un producto paga ISC, con qué sistema de cálculo y con qué tarifas por vigencia.

- **Tarifa aplicable:** la tarifa de la categoría con la fecha de vigencia más reciente que sea igual o anterior a la fecha de emisión.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-CAT-05 Gestionar categorías de ISC

- RF-CAT-22: CUANDO un usuario con `catalogo.isc.gestionar` crea una categoría de ISC, EL SISTEMA pide nombre, sistema de cálculo, código de tipo de sistema para el comprobante y una primera tarifa con su fecha de vigencia.
- RF-CAT-23: EL SISTEMA solo admite en el MVP el **Sistema Específico**: un monto fijo en S/ por litro, que no depende del precio ni de la graduación.
- RF-CAT-24: CUANDO cambia la tarifa, EL SISTEMA la registra como una tarifa nueva con su fecha de inicio; no permite editar ni borrar tarifas existentes, y los comprobantes ya emitidos no cambian (RN-CAT-10).
- RF-CAT-25: CUANDO se calcula el ISC de una venta, EL SISTEMA usa la tarifa aplicable a la fecha de emisión (RN-CAT-10).
- RF-CAT-26: SI un producto con categoría de ISC por litro no tiene contenido en litros mayor a 0, ENTONCES EL SISTEMA lo rechaza (RN-CAT-10).
- RF-CAT-27: MIENTRAS un producto no tenga categoría de ISC, EL SISTEMA no le calcula ISC.
- RF-CAT-28: SI se intenta desactivar una categoría asignada a productos activos, ENTONCES EL SISTEMA lo rechaza.

## Requisitos no funcionales

- Ninguno propio.

## Casos límite

- Una tarifa de ISC con fecha de inicio futura no afecta las ventas de hoy.

## Fuera de alcance

Conversión de unidad de compra a unidad de uso, variantes, listas de precios por canal o cliente, imágenes múltiples, código de barras, ISC al valor o por precio de venta al público, materiales "por empaque" (1 caja cada 24 unidades).

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- **Código de tipo de sistema ISC (el PO aprueba tratarlo como dato configurable de la categoría, 2026-10-10; se valida en el sandbox del PSE antes de 0007a):** el contador indicó `01`; el catálogo 08 de SUNAT indica `02` para monto fijo. Validar en el sandbox del PSE.
