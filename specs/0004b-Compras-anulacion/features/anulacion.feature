# language: es
@E04 @E04b @mvp @borrador
Característica: Anulación de compras
  Como gerente
  Quiero anular una compra mal registrada
  Para corregirla sin descuadrar el inventario

  Antecedentes:
    Dado que soy usuario "gerente" de "Cervecería Andina" con IGV 18 %
    Y el proveedor "Maltería del Sur" con RUC "20512345671"
    Y el bien que se compra "INS-MALTA" con stock 100 KG y costo promedio 4.000000
    Y el bien que se compra "ENV-BOT330" sin stock

  @UC-COM-03 @critico @RF-COM-15 @RF-COM-18
  Escenario: Anular una compra finalizada revierte el stock al mismo costo
    Dado una compra registrada a "Maltería del Sur" con factura "F001-000845" de 50 KG de "INS-MALTA" a 5.00
    Y "INS-MALTA" queda con stock 150 KG, valor 650.00 y costo promedio 4.333333
    Cuando anulo la compra con motivo "Factura errada"
    Entonces se registra una salida "ANULACION" de 50 KG de "INS-MALTA" a costo 5.000000
    Y "INS-MALTA" queda con stock 100 KG, valor 400.00 y costo promedio 4.000000
    Y la compra queda "ANULADA" con usuario, fecha y motivo "Factura errada"
    Y puedo registrar otra compra a "Maltería del Sur" con factura "F001-000845"

  @UC-COM-03 @RF-COM-28
  Escenario: Anular una compra creada no mueve stock
    Dado una compra "CREADA" a "Maltería del Sur" de 40 KG de "INS-MALTA"
    Cuando anulo la compra con motivo "Pedido cancelado"
    Entonces la compra queda "ANULADA" con usuario, fecha y motivo "Pedido cancelado"
    Y no hay movimientos de la compra en el kardex

  @UC-COM-03 @borde @RF-COM-17
  Escenario: Doble anulación concurrente revierte una sola vez
    Dado una compra registrada a "Maltería del Sur" con factura "F001-000845" de 50 KG de "INS-MALTA" a 5.00
    Cuando dos usuarios "gerente" anulan la compra al mismo tiempo
    Entonces solo una anulación tiene éxito
    Y la otra recibe el mensaje "La compra ya está anulada"
    Y existe una sola salida "ANULACION" de la compra

  @UC-COM-03 @RN-INV-04 @borde @RF-COM-16 @RF-INV-21
  Escenario: No se anula una compra cuyo stock ya se consumió
    Dado una compra registrada a "Maltería del Sur" con factura "F001-000900" de 1200 UND de "ENV-BOT330" a 0.85
    Y después salieron 900 UND de "ENV-BOT330"
    Cuando anulo la compra con motivo "Precio errado"
    Entonces la operación es rechazada con el mensaje "No se puede anular: ENV-BOT330 tuvo salidas posteriores a la compra. Corrígela con un ajuste CORRECCION"
    Y la compra sigue "FINALIZADA"

  @UC-COM-03 @borde @RF-COM-29
  Escenario: La anulación exige motivo y es definitiva
    Dado una compra "CREADA" a "Maltería del Sur" de 40 KG de "INS-MALTA"
    Cuando anulo la compra con motivo ""
    Entonces la operación es rechazada con el mensaje "El motivo es obligatorio"
    Cuando anulo la compra con motivo "Duplicada"
    Y anulo la compra con motivo "Otra vez"
    Entonces la operación es rechazada con el mensaje "La compra ya está anulada"

  @UC-COM-03 @borde @RF-COM-15
  Escenario: El rol Almacén no puede anular
    Dado una compra "CREADA" a "Maltería del Sur" de 40 KG de "INS-MALTA"
    Cuando un usuario "almacen" intenta anular la compra
    Entonces recibe "Acceso denegado"
