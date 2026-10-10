# language: es
@E03 @E03a @mvp
Característica: Costo promedio ponderado y kardex
  Como gerente
  Quiero que cada movimiento registre su costo y el saldo resultante
  Para conocer el valor real del inventario y el costo de lo consumido

  Antecedentes:
    Dado que soy usuario "almacen" de "Cervecería Andina"
    Y existe el insumo "INS-MALTA" en KG sin stock
    Y el almacén "Principal"

  @UC-INV-04 @UC-INV-03 @critico @RF-INV-06 @RF-INV-17 @RF-INV-18
  Escenario: Secuencia de entradas y salidas recalcula el promedio
    Cuando registro un ajuste "SALDO_INICIAL" de 100 KG de "INS-MALTA" a costo 4.000000
    Y se registra una compra de 50 KG de "INS-MALTA" a costo 5.000000
    Y se consumen 30 KG de "INS-MALTA" en una OP
    Y registro un ajuste "MERMA" de 20 KG de "INS-MALTA" con motivo "Saco roto"
    Entonces el kardex de "INS-MALTA" muestra:
      | motivo        | tipo    | cantidad | costo_unitario | costo_total | saldo    | promedio |
      | SALDO_INICIAL | ENTRADA | 100.0000 | 4.000000       | 400.00      | 100.0000 | 4.000000 |
      | COMPRA        | ENTRADA | 50.0000  | 5.000000       | 250.00      | 150.0000 | 4.333333 |
      | CONSUMO_OP    | SALIDA  | 30.0000  | 4.333333       | 130.00      | 120.0000 | 4.333333 |
      | MERMA         | SALIDA  | 20.0000  | 4.333333       | 86.67       | 100.0000 | 4.333333 |
    Y el stock de "INS-MALTA" es 100 KG valorizado en 433.33

  @UC-INV-04 @borde @RF-INV-18
  Escenario: Entrada con stock en cero toma el costo de la entrada
    Dado que "INS-MALTA" tuvo stock y quedó en 0 con promedio 4.333333
    Cuando se registra una compra de 10 KG a costo 6.000000
    Entonces el costo promedio de "INS-MALTA" es 6.000000

  @UC-INV-04 @critico @borde @RF-INV-19
  Escenario: Una salida no puede dejar stock negativo
    Dado que "INS-MALTA" tiene stock 5 KG en "Principal"
    Cuando registro un ajuste "MERMA" de 6 KG de "INS-MALTA"
    Entonces la operación es rechazada con el mensaje "Stock insuficiente de INS-MALTA en Principal: disponible 5.0000, requerido 6.0000"
    Y no se registra ningún movimiento

  @UC-INV-04 @critico @borde @RF-INV-19
  Escenario: Concurrencia sobre el último stock
    Dado que "INS-MALTA" tiene stock 10 KG en "Principal"
    Cuando dos usuarios registran simultáneamente salidas de 8 KG de "INS-MALTA"
    Entonces exactamente una operación tiene éxito
    Y la otra es rechazada con "Stock insuficiente"
    Y el stock final es 2 KG

  @UC-INV-03 @critico @RF-INV-17
  Escenario: El kardex es inmutable
    Dado un movimiento registrado de "INS-MALTA"
    Cuando cualquier usuario intenta editarlo o eliminarlo
    Entonces la operación no está disponible
    Y un intento directo en la base de datos es rechazado
