# Spec 0002e — Catálogo: impuestos

Estado: aprobada (PO: "go", 2026-10-11). Propuesta del 2026-10-10 (capturas de Odoo del PO), ajustada el 2026-10-11; reglas validadas con el contador el 2026-10-11 (constitución, art. 5.5)

Épica E02 (Catálogo), parte 5. Depende de: 0001a, 0002a (enmienda 4), 0004a. La usan: 0004a (compras), 0006b (ventas), 0007a (facturación).

Origen: el PO propone manejar los impuestos como en Odoo: un maestro de impuestos y, en la ficha del producto, sus impuestos de venta y de compra (2026-10-10). Decisiones del PO: el precio de venta **incluye** los impuestos; las tasas del ISC viven **en el maestro** (reemplaza las tasas por producto de la enmienda 4 de 0002a); el MVP incluye **IGV, exonerado, inafecto e ISC**; el usuario **define cada impuesto** con nombre y código SUNAT, p. ej. "ISC por 750 ml" S/ 2.01 o "ISC por galón" S/ 10.94; definirlos y cargarlos es responsabilidad del usuario. Ajuste del PO (2026-10-11): los impuestos son **de dos tipos, Venta o Compra**; la compra toma el IGV de los impuestos de compra del producto; el ISC porcentual queda fuera del MVP.

## Contexto y objetivo

Hoy el IGV es un dato de la empresa y el ISC una tasa por producto; todo producto se asume gravado con IGV, también en las compras. No hay forma de vender o comprar un producto exonerado o inafecto, y si SUNAT cambia la tasa del ISC hay que registrarla producto por producto.

**Objetivo:** que cada empresa tenga su lista de impuestos de venta y de compra con tasas por vigencia, que cada producto diga qué impuestos le aplican al venderlo y al comprarlo, y que las ventas, compras y comprobantes los tomen de ahí.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Administrador (u otro rol con `catalogo.isc.gestionar`, que pasa a llamarse "Gestionar impuestos") | Crea impuestos, registra tasas y asigna impuestos a los productos |
| Resto de roles con acceso al catálogo | Ven los impuestos del producto |

## Historias de usuario

- H1: Como administrador, quiero registrar los impuestos de venta y de compra de mi empresa con sus tasas por vigencia para que cada documento use la tasa de su fecha.
- H2: Como administrador, quiero indicar en cada producto si es gravado, exonerado o inafecto al venderlo y al comprarlo, y si lleva ISC, para que la venta, la compra y el comprobante salgan bien.

## Definiciones

- **Impuesto:** registro de la empresa definido por el usuario con **nombre**, **tipo** (**Venta** o **Compra**), **código SUNAT** (IGV, EXO, INA o ISC en el MVP) y activo. Su importe está en sus **tasas**. Ejemplos: "IGV 18%" de venta y "IGV 18%" de compra (IGV, 18 %); "ISC por 750 ml" de venta (ISC, S/ 2.01 por unidad).
- **Criterio:** lo define el código. IGV, EXO e INA son un **porcentaje** del valor; el ISC es un **monto fijo** por unidad vendida del producto (Sistema Específico).
- **Tasa:** importe con fecha de vigencia (p. ej. IGV 18 % desde 2011-03-01; "ISC por 750 ml" S/ 2.01 desde 2026-01-01). No se edita ni se borra: un cambio es una tasa nueva. Cada documento usa la tasa vigente a su fecha.
- **Afectación del IGV:** la define el impuesto IGV, EXO o INA que tiene el producto en cada lista: gravado (IGV), exonerado (EXO, tasa 0) o inafecto (INA, tasa 0).
- **Código de afectación del IGV en el comprobante** (catálogo 07 de SUNAT): en una venta onerosa, gravado `10`, exonerado `20`, inafecto `30`. Los códigos de las entregas gratuitas y su motivo son de 0006b; el código del sistema del ISC en el comprobante, de 0007a.
- **Precio de lista:** incluye los impuestos (sin cambio respecto de 0002a). El desglose separa valor, ISC e IGV.

Orden del cálculo de la venta (fijo, no configurable; contador 2026-10-10): primero el ISC; después el IGV sobre valor + ISC. Con un precio que incluye impuestos:

```
base  = total / (1 + % de IGV vigente)          (% = 0 si es EXO o INA; base = valor + ISC)
ISC   = round(cantidad × monto vigente, 2)       (0 sin ISC)
valor = round(base − ISC, 2)
IGV   = total − valor − ISC
```

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-CAT-09 Gestionar impuestos

- RF-CAT-52: CUANDO se registra una empresa, EL SISTEMA le crea, de tipo Venta y de tipo Compra, los impuestos "IGV 18%" (IGV, con la tasa vigente desde la fecha de registro), "Exonerado" (EXO) e "Inafecto" (INA).
- RF-CAT-53: CUANDO un usuario con `catalogo.isc.gestionar` crea o edita un impuesto, EL SISTEMA guarda nombre (único por empresa y tipo, sin distinguir mayúsculas), tipo y código SUNAT; el tipo y el código no cambian si algún producto o documento usa el impuesto. SI se crea un impuesto ISC de tipo Compra, ENTONCES EL SISTEMA lo rechaza con "El ISC es solo un impuesto de venta".
- RF-CAT-54: CUANDO se agrega una tasa a un impuesto, EL SISTEMA la guarda con su fecha de vigencia; SI ya hay una tasa en esa fecha, o el importe es negativo, o es mayor a 0 en un impuesto EXO o INA, ENTONCES EL SISTEMA la rechaza. Las tasas no se editan ni se borran (constitución, art. 5.1).
- RF-CAT-55: SI se intenta desactivar un impuesto asignado a productos activos, ENTONCES EL SISTEMA lo rechaza; un impuesto inactivo no se ofrece en productos nuevos.

### UC-CAT-10 Impuestos del producto

- RF-CAT-56: EL SISTEMA muestra en la pestaña Ventas de un producto que se vende sus **impuestos de venta** y en la pestaña Compras de uno que se compra sus **impuestos de compra**, como etiquetas; cada lista ofrece solo los impuestos activos de su tipo. Un producto nuevo trae "IGV 18%" en la lista de cada casilla marcada (Se vende, Se compra).
- RF-CAT-57: SI un producto que se vende no tiene exactamente un impuesto de afectación (IGV, EXO o INA) entre sus impuestos de venta, o uno que se compra no lo tiene entre sus impuestos de compra, ENTONCES EL SISTEMA lo rechaza con "El producto debe tener un impuesto de IGV, exonerado o inafecto".
- RF-CAT-58: SI se asigna un impuesto ISC a un servicio, o más de un ISC al mismo producto, ENTONCES EL SISTEMA lo rechaza. El ISC se cobra por unidad vendida del producto: elegir el impuesto que corresponde a cada presentación es responsabilidad del usuario (reemplaza RF-CAT-45 y 26: los litros por unidad dejan de ser obligatorios y ya no intervienen en el cálculo; se conservan como dato informativo).
- RF-CAT-59: CUANDO se calcula el desglose del precio o el impuesto de una línea de venta, EL SISTEMA usa los impuestos de venta del producto y sus tasas vigentes a la fecha del documento, en el orden de Definiciones (reemplaza RF-CAT-46 y conserva RF-CAT-24, 25, 27 y 30).
- RF-CAT-60: CUANDO se aplica esta spec, EL SISTEMA convierte los datos existentes sin perder tasas ni fechas: el IGV de cada empresa, con su historial de vigencias, pasa a las tasas de sus dos impuestos "IGV 18%" (venta y compra); cada ISC por litro de un producto pasa a un impuesto ISC de venta con el mismo historial de fechas (cada tasa × los litros por unidad del producto, con 4 decimales; p. ej. 2.51 × 0.33 L = 0.8283), y los productos con el mismo historial resultante comparten el impuesto (nombre sugerido "ISC 0.33 L"); cada producto queda con "IGV 18%" en la lista de cada casilla marcada, más su ISC de venta si lo tenía. Las compras ya registradas no cambian.
- RF-CAT-61: CUANDO se calcula el IGV de una línea de compra con `FACTURA`, EL SISTEMA usa el % del impuesto de afectación de compra del producto vigente a la fecha de la compra: 0 si es exonerado o inafecto (ajusta RF-COM-08 de 0004a). Con otro documento el IGV sigue siendo 0.

## Requisitos no funcionales

- Ninguno propio. Aplican el aislamiento y los permisos de 0001c.

## Casos límite

- Cambio de IGV o de ISC a mitad de mes: los documentos anteriores a la fecha de vigencia usan la tasa anterior.
- Cambio del IGV: se registra la tasa nueva en los dos impuestos "IGV 18%" (venta y compra); son impuestos distintos.
- Producto exonerado con ISC: válido (el ISC se calcula; el IGV es 0).
- Producto gravado en la venta y exonerado en la compra (o al revés): válido; cada lista es independiente.
- Producto vendido por caja (p. ej. 12 × 330 ml): el usuario le asigna un ISC por caja; el sistema no lo deriva de los litros.
- ISC por unidad con importe de más de 2 decimales (0.8283): la tasa admite 4; el ISC de la línea se redondea a 2.
- Un impuesto sin ninguna tasa vigente a la fecha del documento: el documento se rechaza con "El impuesto <nombre> no tiene tasa vigente al <fecha>" (como hoy con el ISC).
- Entregas gratuitas: siguen como en 0006b (la gratuidad es de la línea de venta, no un impuesto del producto).

## Fuera de alcance

ISC porcentual (sistema al valor, `01`) e ISC por Precio de Venta al Público (`03`); ISC en compras; exportación (EXP), ICBPER, IVAP y OTROS como códigos; impuestos de tipo "ambos"; grupos de impuestos; precio sin impuestos; cuentas contables ("distribución de facturas"); percepciones y retenciones. Se agregan con una enmienda cuando hagan falta.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.
- La conversión probada con los datos de la empresa demo.

## Impacto en otras specs (se ajustan en el mismo cambio, al aprobarse)

- **0001a (implementada):** RF-TEN-15 y 16: el % de IGV deja de editarse en la configuración de la empresa; pasa a las tasas de los impuestos "IGV 18%" (misma regla de vigencia, RN-TEN-07).
- **0002a (implementada):** RF-CAT-45, 46 y 48 (ISC en la ficha con tasas por producto y litros obligatorios) quedan reemplazados por RF-CAT-56 a 60; RF-CAT-30 (desglose) usa los impuestos de venta del producto.
- **0002c (implementada):** RF-CAT-23 (Sistema Específico) se conserva como el criterio del ISC; RF-CAT-24, 25 y 27 se conservan; las tasas pasan al maestro.
- **0004a (implementada):** RF-COM-08 y la definición "IGV de la compra": el % sale del impuesto de compra de cada producto (RF-CAT-61), ya no de la empresa.
- **0006b, 0007a (borradores):** toman los impuestos de venta del producto; el comprobante usa la afectación (gravado, exonerado, inafecto) de cada línea. 0006b recibe la duda de los códigos gratuitos de inafectos; 0007a ya tiene la del código del sistema ISC (01 vs 02).

## Dudas abiertas

- ~~Contador (art. 5.5)~~ **Resueltas (respuesta a la consulta al contador transmitida por el PO, 2026-10-11):** (1) sí: en una compra con factura, un insumo exonerado o inafecto lleva IGV 0, sin crédito fiscal, y entra al inventario al valor pagado; (2) sí: el ISC se calcula igual en un producto exonerado de IGV y forma parte del precio.
- Resueltas o movidas: códigos de venta onerosa (10, 20, 30, catálogo 07); códigos gratuitos de gravados (PO, en 0006b); códigos gratuitos de inafectos → 0006b; sistema del ISC (01 vs 02) → 0007a; ISC porcentual → fuera de alcance.
