# language: es
@E04 @mvp
Característica: Registro y anulación de compras
  Como encargado de almacén
  Quiero registrar las compras de insumos, envases y mercadería de reventa
  Para aumentar el stock al costo real y sin IGV recuperable

  Antecedentes:
    Dado que soy usuario "almacen" de "Cervecería Andina" con IGV 18 %
    Y el proveedor "Maltería del Sur" con RUC "20512345671"
    Y el insumo "INS-MALTA" con stock 100 KG y costo promedio 4.000000
    Y el envase "ENV-BOT330" sin stock

  @UC-COM-02 @critico @RF-COM-04 @RF-COM-08 @RF-COM-09 @RF-COM-10
  Escenario: Compra con factura separa el IGV del costo
    Cuando registro una compra a "Maltería del Sur" con factura "F001-000845" al almacén "Principal":
      | producto   | cantidad | costo_unitario |
      | INS-MALTA  | 50       | 5.00           |
      | ENV-BOT330 | 1200     | 0.85           |
    Entonces la compra "C-000001" queda "REGISTRADA" con:
      | subtotal | igv    | total   |
      | 1270.00  | 228.60 | 1498.60 |
    Y el costo promedio de "INS-MALTA" es 4.333333
    Y el costo promedio de "ENV-BOT330" es 0.850000
    Y el kardex de ambos productos tiene una entrada "COMPRA" que referencia "C-000001"

  @UC-COM-02 @critico @RF-COM-08 @RF-COM-09
  Escenario: Compra con boleta no separa IGV
    Cuando registro una compra a "Maltería del Sur" con boleta "B002-001122":
      | producto  | cantidad | costo_unitario |
      | INS-MALTA | 10       | 5.90           |
    Entonces la compra tiene IGV 0.00 y total 59.00
    Y la entrada de "INS-MALTA" es a costo 5.900000

  @UC-COM-02 @borde @RF-COM-05
  Escenario: No se compran productos que se producen
    Cuando registro una compra con el producto terminado "TER-IPA-330"
    Entonces la operación es rechazada con el mensaje "Solo se pueden comprar insumos, envases y mercadería"

  @UC-COM-02 @RN-COM-01 @critico @RF-COM-06 @RF-COM-07
  Escenario: Compra de mercadería perecible ingresa con lote y vencimiento
    Dado el producto "MER-AGUA-500" de tipo "MERCADERIA" que controla lote
    Cuando registro una compra a "Distribuidora Lima" con factura "F010-000321":
      | producto     | cantidad | costo_unitario | lote     | vence      |
      | MER-AGUA-500 | 120      | 1.20           | AG-2611A | 2027-11-01 |
    Entonces la entrada de "MER-AGUA-500" es de 120 UND al lote "AG-2611A" a costo 1.200000
    Y el lote "AG-2611A" vence el "2027-11-01" y queda disponible para venta FEFO

  @UC-COM-02 @borde @RF-COM-06
  Escenario: Mercadería con lote exige lote y vencimiento en la compra
    Cuando registro una compra de 120 UND de "MER-AGUA-500" sin lote
    Entonces la operación es rechazada con el mensaje "MER-AGUA-500 controla lote: ingresa el código de lote y el vencimiento"

  @UC-COM-02 @borde @RF-COM-11
  Escenario: Documento del proveedor duplicado
    Dado una compra registrada a "Maltería del Sur" con factura "F001-000845"
    Cuando registro otra compra a "Maltería del Sur" con factura "F001-000845"
    Entonces la operación es rechazada con el mensaje "La factura F001-000845 de Maltería del Sur ya fue registrada en C-000001"

  @UC-COM-02 @borde @RF-COM-04 @RF-COM-12
  Esquema del escenario: Validaciones de la compra
    Cuando registro una compra con "<campo>" igual a "<valor>"
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | campo          | valor      | mensaje                                   |
      | fecha          | mañana     | La fecha de compra no puede ser futura    |
      | cantidad       | 0          | La cantidad debe ser mayor a 0            |
      | costo_unitario | -1         | El costo unitario no puede ser negativo   |
      | lineas         | ninguna    | La compra debe tener al menos una línea   |

  @UC-COM-03 @critico @RF-COM-15 @RF-COM-18
  Escenario: Anular compra revierte el stock al mismo costo y recalcula el promedio
    Dado "INS-MALTA" tenía stock 100 KG con valor 400.00
    Y la compra "C-000001" con documento "F001-000845" y 50 KG de "INS-MALTA" a 5.00
    Y "INS-MALTA" tiene stock 150 KG con valor 650.00 y costo promedio 4.333333
    Y no hubo salidas de "INS-MALTA" después de "C-000001"
    Cuando un usuario "gerente" anula "C-000001" con motivo "Factura errada"
    Entonces se registra una salida "ANULACION" de 50 KG de "INS-MALTA" a costo 5.000000
    Y "INS-MALTA" queda con stock 100 KG, valor 400.00 y costo promedio 4.000000
    Y "C-000001" queda "ANULADA" con usuario, fecha y motivo
    Y el documento "F001-000845" puede registrarse de nuevo

  @UC-COM-03 @borde @RF-COM-17
  Escenario: Doble anulación concurrente revierte una sola vez
    Dado la compra "C-000001" con 50 KG de "INS-MALTA" a 5.00
    Cuando dos usuarios "gerente" anulan "C-000001" al mismo tiempo
    Entonces solo una anulación tiene éxito
    Y la otra recibe el mensaje "La compra ya está anulada"
    Y existe una sola salida "ANULACION" para "C-000001"

  @UC-COM-03 @RN-INV-04 @borde @RF-COM-16 @RF-INV-21
  Escenario: No se anula una compra cuyo stock ya se consumió
    Dado la compra "C-000001" con 1200 UND de "ENV-BOT330"
    Y después se usaron 900 UND de "ENV-BOT330" en envasados
    Cuando un usuario "gerente" intenta anular "C-000001"
    Entonces la operación es rechazada con el mensaje "No se puede anular: ENV-BOT330 tuvo salidas posteriores a la compra. Corrija con un ajuste"

  @UC-COM-03 @borde @RF-COM-15
  Escenario: Rol almacén no puede anular
    Cuando un usuario "almacen" intenta anular "C-000001"
    Entonces la operación es denegada

  @UC-COM-01 @RF-COM-02
  Escenario: Proveedor con compras se desactiva en vez de eliminarse
    Dado que "Maltería del Sur" tiene compras
    Cuando intento eliminar "Maltería del Sur"
    Entonces la operación es rechazada con el mensaje "El proveedor tiene compras; puedes desactivarlo"
