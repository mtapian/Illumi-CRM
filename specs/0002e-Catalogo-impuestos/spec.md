# Spec 0002e — Catálogo: impuestos

Estado: borrador. Propuesta del 2026-10-10 (capturas de Odoo del PO), pendiente de aprobación del PO **y de la validación del contador** de las reglas nuevas (constitución, art. 5.5)

Épica E02 (Catálogo), parte 5. Depende de: 0001a, 0002a (enmienda 4). La usan: 0004a (compras), 0006b (ventas), 0007a (facturación).

Origen: el PO propone manejar los impuestos como en Odoo: un maestro de impuestos y, en la ficha del producto, sus impuestos de venta y de compra (2026-10-10). Decisiones del PO: el precio de venta **incluye** los impuestos; las tasas del ISC viven **en el maestro** (reemplaza las tasas por producto de la enmienda 4 de 0002a); el MVP incluye **IGV, exonerado, inafecto e ISC**. Además (PO, 2026-10-10): el usuario **define cada impuesto** con nombre, código SUNAT y criterio (**monto fijo o porcentaje**), p. ej. "ISC por 750 ml" monto fijo S/ 2.01 o "ISC por galón" S/ 10.94; definirlos y cargarlos es responsabilidad del usuario.

## Contexto y objetivo

Hoy el IGV es un dato de la empresa y el ISC una tasa por producto; todo producto se asume gravado con IGV. No hay forma de vender un producto exonerado o inafecto, y si SUNAT cambia la tasa del ISC hay que registrarla producto por producto.

**Objetivo:** que cada empresa tenga su lista de impuestos con tasas por vigencia, que cada producto diga qué impuestos le aplican, y que las ventas, compras y comprobantes los tomen de ahí.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Administrador (u otro rol con `catalogo.isc.gestionar`, que pasa a llamarse "Gestionar impuestos") | Crea impuestos, registra tasas y asigna impuestos a los productos |
| Resto de roles con acceso al catálogo | Ven los impuestos del producto |

## Historias de usuario

- H1: Como administrador, quiero registrar los impuestos de mi empresa con sus tasas por vigencia para que cada documento use la tasa de su fecha.
- H2: Como administrador, quiero indicar en cada producto si es gravado, exonerado o inafecto, y si lleva ISC, para que la venta y el comprobante salgan bien.

## Definiciones

- **Impuesto:** registro de la empresa definido por el usuario con **nombre**, **código SUNAT** (tributo: IGV, EXO, INA o ISC en el MVP), **criterio** (**monto fijo** por unidad vendida del producto, o **porcentaje**), **uso** (ventas, compras o ambos) y activo. Su importe está en sus **tasas**. Ejemplos: "IGV 18%" (IGV, porcentaje 18); "ISC por 750 ml" (ISC, monto fijo S/ 2.01); "ISC por galón" (ISC, monto fijo S/ 10.94).
- **Tasa:** importe con fecha de vigencia (p. ej. IGV 18 % desde 2011-03-01; "ISC por 750 ml" S/ 2.01 desde 2026-01-01). No se edita ni se borra: un cambio es una tasa nueva. Cada documento usa la tasa vigente a su fecha.
- **Sistema del ISC en el comprobante** (catálogo 08 de SUNAT): lo define el criterio: monto fijo = `02` (aplicación del monto fijo); porcentaje = `01` (sistema al valor). Resuelve la duda 01 vs 02.
- **Afectación del IGV:** lo define el impuesto de tipo IGV, EXO o INA que tiene el producto: gravado (IGV), exonerado (EXO, tasa 0) o inafecto (INA, tasa 0). Es el dato que cada línea del comprobante necesita.
- **Precio de lista:** incluye los impuestos (sin cambio respecto de 0002a). El desglose separa valor, ISC e IGV.
- **Código de afectación del IGV en el comprobante** (catálogo 07 de SUNAT, compartido por el PO el 2026-10-10). Lo deriva el sistema del impuesto de afectación del producto y del tipo de línea:

  | Impuesto del producto | Venta onerosa | Entrega gratuita (0006b) |
  |---|---|---|
  | IGV (gravado) | `10` | `11` a `16` según el motivo: premio, donación, retiro, publicidad, bonificación, entrega a trabajadores |
  | EXO (exonerado) | `20` | `21` |
  | INA (inafecto) | `30` | `31` a `36` según el motivo: bonificación, retiro, muestras médicas, convenio colectivo, premio, publicidad |

  Fuera del MVP: `17` (IVAP), `37` y `40` (exportación).

  **Motivo de la entrega gratuita → código** (PO, 2026-10-10), para un producto gravado:

  | Motivo (lo elige el vendedor en la línea, 0006b) | Tipo de operación | Código |
  |---|---|---|
  | Degustación en eventos o muestras | Retiro por publicidad | `14` |
  | Regalo vinculado a una venta (promoción) | Bonificación | `15` |
  | Regalo a trabajadores (festividades, metas) | Retiro por entrega a trabajadores | `16` |
  | Retiro sin sustento publicitario o comercial | Retiro de bienes (general) | `13` |

  Producto exonerado: `21` con cualquier motivo. Producto inafecto (propuesta, a confirmar): degustación `36`, promoción `31`, trabajadores y retiro general `32`.

Orden del cálculo (fijo, no configurable; contador 2026-10-10): primero el ISC; después el IGV sobre valor + ISC. Con un precio que incluye impuestos:

```
base  = total / (1 + % de IGV vigente)               (% = 0 si es EXO o INA; base = valor + ISC)
ISC monto fijo:  ISC = round(cantidad × monto vigente, 2);   valor = round(base − ISC, 2)
ISC porcentaje:  valor = round(base / (1 + % de ISC), 2);    ISC = round(base, 2) − valor
sin ISC:         ISC = 0;                                    valor = round(base, 2)
IGV   = total − valor − ISC
```

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-CAT-09 Gestionar impuestos

- RF-CAT-52: CUANDO se registra una empresa, EL SISTEMA le crea los impuestos "IGV 18%" (IGV, ventas y compras, con la tasa vigente desde la fecha de registro), "Exonerado" (EXO) e "Inafecto" (INA).
- RF-CAT-53: CUANDO un usuario con `catalogo.isc.gestionar` crea o edita un impuesto, EL SISTEMA guarda nombre (único en la empresa, sin distinguir mayúsculas), código SUNAT, criterio y uso; el código y el criterio no cambian si algún producto o documento usa el impuesto. SI un impuesto IGV, EXO o INA no tiene criterio porcentaje, ENTONCES EL SISTEMA lo rechaza (solo el ISC admite monto fijo).
- RF-CAT-54: CUANDO se agrega una tasa a un impuesto, EL SISTEMA la guarda con su fecha de vigencia; SI ya hay una tasa en esa fecha, o el importe es negativo, o es mayor a 0 en un impuesto EXO o INA, ENTONCES EL SISTEMA la rechaza. Las tasas no se editan ni se borran (constitución, art. 5.1).
- RF-CAT-55: SI se intenta desactivar un impuesto asignado a productos activos, ENTONCES EL SISTEMA lo rechaza; un impuesto inactivo no se ofrece en productos nuevos.

### UC-CAT-10 Impuestos del producto

- RF-CAT-56: EL SISTEMA muestra en la pestaña Ventas de un producto que se vende sus **impuestos de venta** y en la pestaña Compras de uno que se compra sus **impuestos de compra**, como etiquetas; un producto nuevo trae "IGV 18%" en ambos.
- RF-CAT-57: SI un producto que se vende no tiene exactamente un impuesto de afectación del IGV (IGV, EXO o INA) entre sus impuestos de venta, ENTONCES EL SISTEMA lo rechaza con "El producto debe tener un impuesto de IGV, exonerado o inafecto".
- RF-CAT-58: SI se asigna un impuesto ISC a un servicio, o más de un ISC al mismo producto, ENTONCES EL SISTEMA lo rechaza. El ISC de monto fijo se cobra por unidad vendida del producto: elegir el impuesto que corresponde a cada presentación es responsabilidad del usuario (reemplaza RF-CAT-45 y 26: los litros por unidad dejan de ser obligatorios y ya no intervienen en el cálculo; se conservan como dato informativo).
- RF-CAT-59: CUANDO se calcula el desglose del precio o el impuesto de una línea, EL SISTEMA usa los impuestos de venta del producto y sus tasas vigentes a la fecha del documento, en el orden de Definiciones (reemplaza RF-CAT-46 y conserva RF-CAT-23 a 25, 27 y 30).
- RF-CAT-60: CUANDO se aplica esta spec, EL SISTEMA convierte los datos existentes sin perder tasas ni fechas: el IGV de cada empresa, con su historial de vigencias, pasa a las tasas de su impuesto "IGV 18%"; cada ISC por litro de un producto pasa a un impuesto ISC de **monto fijo** por unidad con el mismo historial de fechas (cada tasa × los litros por unidad del producto, con 4 decimales; p. ej. 2.51 × 0.33 L = 0.8283), y los productos con el mismo historial resultante comparten el impuesto (nombre sugerido "ISC 0.33 L"); todos los productos quedan con "IGV 18%" en venta y compra, más su ISC si lo tenían.

## Requisitos no funcionales

- Ninguno propio. Aplican el aislamiento y los permisos de 0001c.

## Casos límite

- Cambio de IGV o de ISC a mitad de mes: las ventas anteriores a la fecha de vigencia usan la tasa anterior.
- Producto exonerado con ISC: válido (el ISC se calcula; el IGV es 0).
- Producto vendido por caja (p. ej. 12 × 330 ml): el usuario le asigna un ISC de monto fijo por caja; el sistema no lo deriva de los litros.
- ISC por unidad con importe de más de 2 decimales (0.8283): la tasa admite 4; el ISC de la línea se redondea a 2.
- Un impuesto sin ninguna tasa vigente a la fecha del documento: la venta se rechaza con "El impuesto <nombre> no tiene tasa vigente al <fecha>" (como hoy con el ISC).
- Entregas gratuitas: siguen como en 0006b (la gratuidad es de la línea de venta, no un impuesto del producto).

## Fuera de alcance

Exportación (EXP), ICBPER, IVAP y OTROS como códigos (se agregan a la lista cuando hagan falta), ISC por Precio de Venta al Público (sistema 03), grupos de impuestos, impuestos con precio sin impuestos, cuentas contables ("distribución de facturas"), percepciones y retenciones. Se agregan con una enmienda cuando hagan falta.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.
- La conversión probada con los datos de la empresa demo.

## Impacto en otras specs (se ajustan en el mismo cambio, al aprobarse)

- **0001a:** RF-TEN-15 y 16: el % de IGV deja de editarse en la configuración de la empresa; pasa a las tasas del impuesto "IGV 18%" (misma regla de vigencia, RN-TEN-07).
- **0002a:** RF-CAT-45, 46 y 48 (ISC en la ficha con tasas por producto y litros obligatorios) quedan reemplazados por RF-CAT-56 a 60; RF-CAT-30 (desglose) usa los impuestos del producto.
- **0002c:** RF-CAT-23 (solo Sistema Específico por litro) queda reemplazado por el criterio monto fijo / porcentaje; RF-CAT-24, 25 y 27 (vigencia y sin ISC si no tiene impuesto) se conservan.
- **0004a, 0006b, 0007a (borradores):** toman los impuestos de compra y de venta del producto; el comprobante usa la afectación (gravado, exonerado, inafecto) de cada línea.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Contador (art. 5.5), antes de aprobar:** (1) ~~códigos de afectación en ventas onerosas~~ **resuelto con el catálogo 07 de SUNAT (10, 20, 30)**; (1b) ~~código de las entregas gratuitas~~ **resuelto por el PO para productos gravados (13 a 16 según motivo)**; falta confirmar el mapeo propuesto para inafectos (36, 31, 32); (2) si en compras un insumo exonerado o inafecto cambia el crédito fiscal que registra 0004a; (3) si el ISC se sigue calculando igual en un producto exonerado de IGV; (4) ISC porcentual (al valor): que la base del ISC sea el valor de venta y la del IGV valor + ISC, y que monto fijo = sistema `02` y porcentaje = `01`.
