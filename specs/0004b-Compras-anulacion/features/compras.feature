# language: es
@E04 @E04b @mvp
Característica: Registro y anulación de compras
  Como encargado de almacén
  Quiero registrar las compras de insumos, envases y mercadería de reventa
  Para aumentar el stock al costo real y sin IGV recuperable

  Antecedentes:
    Dado que soy usuario "almacen" de "Cervecería Andina" con IGV 18 %
    Y el proveedor "Maltería del Sur" con RUC "20512345671"
    Y el insumo "INS-MALTA" con stock 100 KG y costo promedio 4.000000
    Y el envase "ENV-BOT330" sin stock

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
