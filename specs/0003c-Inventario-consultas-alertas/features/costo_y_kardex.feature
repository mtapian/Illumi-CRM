# language: es
@E03 @E03c @mvp
Característica: Costo promedio ponderado y kardex
  Como gerente
  Quiero que cada movimiento registre su costo y el saldo resultante
  Para conocer el valor real del inventario y el costo de lo consumido

  Antecedentes:
    Dado que soy usuario "almacen" de "Cervecería Andina"
    Y existe el bien "INS-MALTA" que se compra, en KG, sin stock
    Y el almacén "Principal"

  @UC-INV-03 @critico @RF-INV-06 @RF-INV-17
  Escenario: Reconciliación del kardex con el stock
    Dado que "INS-MALTA" tiene 25 movimientos en distintos almacenes
    Entonces la suma de entradas menos salidas del kardex es igual al stock total
    Y el último saldo de promedio del kardex es igual al costo promedio actual

  @UC-INV-03 @RF-INV-07
  Escenario: Exportar el kardex filtrado a CSV
    Dado que "INS-MALTA" tiene 25 movimientos en distintos almacenes
    Cuando exporto a CSV el kardex de "INS-MALTA" del almacén "Principal"
    Entonces el CSV tiene una fila por cada movimiento de "INS-MALTA" en "Principal", con su saldo y promedio
