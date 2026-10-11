# Spec 0002d — Catálogo: proveedores y proveedores del producto

Estado: implementada (2026-10-10)

Épica E02 (Catálogo), parte 4 de 4. Depende de: 0001c, 0002a. La usan: 0004a (compras) y la pestaña "Compras" de la ficha de producto (0002a, enmienda 1).

Origen: el PO adelanta el maestro de proveedores (antes UC-COM-01 de la spec 0004a) para que cada producto comprable muestre sus proveedores habituales, como en Odoo (2026-10-10). Los RF conservan su número (RF-COM-01 a 03).

## Contexto y objetivo

Para comprar bien hay que saber a quién se le compra cada insumo, envase o mercadería, a qué precio de referencia y en cuánto tiempo llega. Hoy esa información vive en la cabeza del encargado de almacén o en una planilla.

**Objetivo:** tener el registro de proveedores de la empresa y, en la ficha de cada producto comprable, sus proveedores habituales con precio referencial y plazo de entrega.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Almacén, Gerente, Administrador | Gestionan proveedores y los asocian a productos (`compras.proveedor.gestionar`) |
| Producción, Ventas | Consultan la ficha del producto |

## Historias de usuario

- H1: Como encargado de almacén, quiero registrar a mis proveedores para asociarles productos y compras.
- H2: Como encargado de almacén, quiero ver en la ficha de un insumo a quién se lo compro, a qué precio referencial y con qué plazo, para reponerlo a tiempo.

## Definiciones

- **Proveedor del producto:** relación entre un proveedor y un producto comprable (con la casilla "Se compra" marcada; 0002a enmienda 4, RF-CAT-38) con precio referencial en S/ por unidad del producto, plazo de entrega en días y, opcionalmente, el código con que el proveedor identifica el producto.
- **Precio referencial:** dato informativo para comprar; no es el costo. El costo lo fija cada compra (spec 0004a).

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-COM-01 Gestionar proveedores (movido desde 0004a)

- RF-COM-01: CUANDO un usuario con `compras.proveedor.gestionar` registra un proveedor con tipo y número de documento (RUC o DNI), razón social y datos de contacto, EL SISTEMA lo guarda si el documento es válido y no existe en la empresa.
- RF-COM-02: SI se intenta eliminar un proveedor con compras, ENTONCES EL SISTEMA lo rechaza y ofrece desactivarlo.
- RF-COM-03: MIENTRAS un proveedor esté desactivado, EL SISTEMA no lo ofrece en compras nuevas ni para asociarlo a productos.

### UC-COM-08 Proveedores del producto

- RF-COM-21: CUANDO un usuario con `compras.proveedor.gestionar` asocia un proveedor activo a un producto comprable, EL SISTEMA guarda el precio referencial (≥ 0, 2 decimales), el plazo de entrega (≥ 0 días) y el código del proveedor (opcional). SI el proveedor ya está asociado a ese producto, ENTONCES EL SISTEMA actualiza esos datos en vez de duplicarlo.
- RF-COM-22: EL SISTEMA muestra los proveedores del producto en la pestaña "Compras" de su ficha, solo en productos comprables. El precio referencial no cambia el costo del producto. Quitar un proveedor de un producto no afecta las compras ya registradas.

## Requisitos no funcionales

- Ninguno propio; aplican los de 0001c (permisos y aislamiento).

## Casos límite

- Un RUC con dígito verificador inválido se rechaza; un DNI debe tener 8 dígitos.
- El mismo RUC en dos empresas distintas: se permite (cada empresa tiene sus proveedores).
- Un producto que deja de ser comprable (se desmarca "Se compra") conserva sus proveedores asociados, pero no se muestran hasta que vuelva a ser comprable.

## Fuera de alcance

Otras monedas (solo S/), precios por cantidad o por rango de fechas, política de control de facturas, evaluación de proveedores, sugerencia automática de compras.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- Ninguna.
