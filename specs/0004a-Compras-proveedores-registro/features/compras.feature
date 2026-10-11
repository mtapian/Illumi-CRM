# language: es
@E04 @E04a @mvp
Característica: Registro de compras
  Como encargado de almacén
  Quiero registrar las compras de los bienes que compro
  Para aumentar el stock al costo real y sin IGV recuperable

  Salvo que el escenario diga otra cosa, "registro una compra" es crearla y finalizarla.

  Antecedentes:
    Dado que soy usuario "almacen" de "Cervecería Andina" con IGV 18 %
    Y el proveedor "Maltería del Sur" con RUC "20512345671"
    Y el bien que se compra "INS-MALTA" con stock 100 KG y costo promedio 4.000000
    Y el bien que se compra "ENV-BOT330" sin stock

  @UC-COM-02 @critico @RF-COM-04 @RF-COM-08 @RF-COM-09 @RF-COM-10
  Escenario: Compra con factura separa el IGV del costo
    Cuando registro una compra a "Maltería del Sur" con factura "F001-000845" al almacén "Principal":
      | producto   | cantidad | costo_unitario |
      | INS-MALTA  | 50       | 5.00           |
      | ENV-BOT330 | 1200     | 0.85           |
    Entonces la compra "C-000001" queda "FINALIZADA" con:
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
  Esquema del escenario: No se compra lo que no tiene la casilla "Se compra"
    Dado el <tipo> "<sku>" que no se compra
    Cuando registro una compra con el producto "<sku>"
    Entonces la operación es rechazada con el mensaje "Solo se pueden comprar bienes activos que se compran"

    Ejemplos:
      | tipo     | sku         |
      | bien     | TER-IPA-330 |
      | servicio | SRV-TOUR    |

  @UC-COM-02 @RN-COM-01 @critico @RF-COM-06 @RF-COM-07
  Escenario: Compra de mercadería perecible ingresa con lote y vencimiento
    Dado el bien "MER-AGUA-500" que se compra y se vende
    Y el proveedor "Distribuidora Lima" con RUC "20100047218"
    Cuando registro una compra a "Distribuidora Lima" con factura "F010-000321":
      | producto     | cantidad | costo_unitario | lote     | vence      |
      | MER-AGUA-500 | 120      | 1.20           | AG-2611A | 2027-11-01 |
    Entonces la entrada de "MER-AGUA-500" es de 120 UND al lote "AG-2611A" a costo 1.200000
    Y el lote "AG-2611A" vence el "2027-11-01" y queda disponible para venta FEFO

  @UC-COM-02 @RF-COM-06
  Escenario: El lote es opcional y su vencimiento se sugiere con la vida útil
    Dado el bien "MER-AGUA-500" que se compra y se vende, con vida útil de 365 días
    Cuando registro una compra de 120 UND de "MER-AGUA-500" sin lote
    Y registro una compra de 60 UND de "MER-AGUA-500" al lote "AG-2611B" sin vencimiento
    Entonces "MER-AGUA-500" tiene 120 UND sin lote
    Y el lote "AG-2611B" vence a los 365 días de la fecha de recepción

  @UC-COM-02 @borde @RF-COM-11
  Escenario: Documento del proveedor duplicado
    Dado una compra registrada a "Maltería del Sur" con factura "F001-000845"
    Cuando registro otra compra a "Maltería del Sur" con factura "F001-000845"
    Entonces la operación es rechazada con el mensaje "La factura F001-000845 de Maltería del Sur ya fue registrada en C-000001"

  @UC-COM-02 @borde @RF-COM-04
  Esquema del escenario: Validaciones de la compra
    Cuando registro una compra con "<campo>" igual a "<valor>"
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | campo          | valor      | mensaje                                   |
      | cantidad       | 0          | La cantidad debe ser mayor a 0            |
      | costo_unitario | -1         | El costo unitario no puede ser negativo   |
      | lineas         | ninguna    | La compra debe tener al menos una línea   |

  @UC-COM-02 @borde @RF-COM-19
  Escenario: Un lote existente con otro vencimiento se rechaza
    Dado el lote "AG-2611A" de "MER-AGUA-500" que vence el "2027-11-01"
    Cuando registro una compra de 60 UND de "MER-AGUA-500" al lote "AG-2611A" con vencimiento "2027-12-01"
    Entonces la operación es rechazada con el mensaje "El lote AG-2611A ya existe con vencimiento 2027-11-01"

  @UC-COM-02 @borde @RF-COM-07
  Escenario: Un lote existente con el mismo vencimiento suma la cantidad
    Dado el lote "AG-2611A" de "MER-AGUA-500" con 120 UND que vence el "2027-11-01"
    Cuando registro una compra de 60 UND de "MER-AGUA-500" al lote "AG-2611A" con vencimiento "2027-11-01"
    Entonces el lote "AG-2611A" queda con 180 UND

  @UC-COM-02 @borde @RF-COM-20
  Escenario: Una factura exige un proveedor con RUC
    Dado el proveedor "Juan Pérez" con DNI "45678912"
    Cuando registro una compra a "Juan Pérez" con factura "F001-000010"
    Entonces la operación es rechazada con el mensaje "Una factura requiere un proveedor con RUC"

  @UC-COM-02 @RF-COM-04
  Escenario: Bonificación del proveedor con costo cero
    Cuando registro una compra a "Maltería del Sur" con factura "F001-000900":
      | producto  | cantidad | costo_unitario | bonificacion |
      | INS-MALTA | 50       | 5.00           | no           |
      | INS-MALTA | 5        | 0.00           | sí           |
    Entonces la compra queda "FINALIZADA" con subtotal 250.00
    Y "INS-MALTA" queda con stock 155 KG, valor 650.00 y costo promedio 4.193548

  @UC-COM-02 @borde @RF-COM-23
  Escenario: No se compra a un proveedor desactivado
    Dado que "Maltería del Sur" está desactivado
    Cuando registro una compra a "Maltería del Sur" con boleta "B002-001200"
    Entonces la operación es rechazada con el mensaje "El proveedor está desactivado"

  @UC-COM-02 @RF-COM-24 @RF-COM-02
  Escenario: Un proveedor con compras ya no se elimina
    Dado una compra registrada a "Maltería del Sur" con factura "F001-000845"
    Cuando intento eliminar el proveedor "Maltería del Sur"
    Entonces la operación es rechazada con el mensaje "El proveedor tiene compras; puedes desactivarlo"

  @UC-COM-02 @critico @RF-COM-25 @RF-COM-26 @RF-COM-10
  Escenario: Solo al finalizar entra el stock
    Cuando creo una compra a "Maltería del Sur" con factura "F001-000950" de 50 KG de "INS-MALTA" a 5.00
    Entonces la compra queda "CREADA" y "INS-MALTA" sigue con stock 100 KG
    Cuando cambio la cantidad a 40 KG y la paso a "EN_PROCESO"
    Entonces la compra queda "EN_PROCESO" y "INS-MALTA" sigue con stock 100 KG
    Cuando finalizo la compra
    Entonces la compra queda "FINALIZADA" y "INS-MALTA" tiene stock 140 KG
    Y la compra ya no se puede editar

  @UC-COM-02 @borde @RF-COM-12 @RF-COM-26
  Escenario: La fecha de la compra es referencia y no impide finalizar
    Cuando creo una compra a "Maltería del Sur" con fecha "mañana"
    Entonces la compra queda "CREADA"
    Cuando finalizo la compra con fecha de recepción "hoy"
    Entonces la compra queda "FINALIZADA" con fecha "mañana"
    Y el movimiento de kardex tiene la fecha de hoy

  @UC-COM-02 @borde @RF-COM-27
  Escenario: Se finaliza con la fecha de recepción
    Dado una compra "CREADA" a "Maltería del Sur" de 40 KG de "INS-MALTA" con lote "M-01"
    Cuando finalizo la compra con fecha de recepción "hace 3 días"
    Entonces el movimiento de kardex y el ingreso del lote "M-01" tienen la fecha de hace 3 días
    Cuando intento finalizar otra compra con fecha de recepción "mañana"
    Entonces la operación es rechazada con el mensaje "La fecha de recepción no puede ser futura"

  @UC-COM-02 @RF-COM-27
  Escenario: Al confirmar la recepción se cambia el almacén y se registra la guía
    Dado el almacén "Cámara fría" activo
    Y una compra "EN_PROCESO" a "Maltería del Sur" de 40 KG de "INS-MALTA" con almacén "Principal"
    Cuando finalizo la compra con almacén "Cámara fría", fecha de recepción "hoy" y guía "T001-00004521"
    Entonces "INS-MALTA" tiene stock 40 KG en "Cámara fría" y sigue con 100 KG en "Principal"
    Y la compra muestra el almacén "Cámara fría" y la guía "T001-00004521"
    Cuando intento finalizar otra compra con guía "T1-ABC"
    Entonces la operación es rechazada con el mensaje "Guía de remisión inválida"
