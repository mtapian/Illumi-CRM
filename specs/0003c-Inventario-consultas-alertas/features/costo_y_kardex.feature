# language: es
@E03 @E03c @mvp
Característica: Costo promedio ponderado y kardex
  Como gerente
  Quiero que cada movimiento registre su costo y el saldo resultante
  Para conocer el valor real del inventario y el costo de lo consumido

  Antecedentes:
    Dado que soy usuario "almacen" de "Cervecería Andina"
    Y existe el insumo "INS-MALTA" en KG sin stock
    Y el almacén "Principal"

  @UC-INV-03 @critico @RF-INV-06 @RF-INV-17
  Escenario: Reconciliación del kardex con el stock
    Dado que "INS-MALTA" tiene 25 movimientos en distintos almacenes
    Entonces la suma de entradas menos salidas del kardex es igual al stock total
    Y el último saldo de promedio del kardex es igual al costo promedio actual
