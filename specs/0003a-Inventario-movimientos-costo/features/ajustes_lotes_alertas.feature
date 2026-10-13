# language: es
@E03 @E03a @mvp
Característica: Ajustes, lotes, almacenes y alertas
  Como encargado de almacén
  Quiero corregir el stock con evidencia y controlar lotes y vencimientos
  Para que el sistema refleje lo que hay físicamente

  Antecedentes:
    Dado que soy usuario "almacen" de "Cervecería Andina"
    Y la fecha de hoy es "2026-11-01"
    Y el bien "TER-IPA-330" que se fabrica y se vende, con stock por lote en "Principal":
      | lote      | vence      | cantidad |
      | IPA-0012  | 2026-10-30 | 10       |
      | IPA-0015  | 2026-12-15 | 48       |
      | IPA-0018  | 2027-02-20 | 120      |

  @UC-INV-04 @RN-INV-06 @critico @RF-INV-22
  Escenario: Asignación FEFO excluye lotes vencidos
    Cuando se solicita la salida de 60 UND de "TER-IPA-330" sin indicar lote
    Entonces se asignan 48 UND del lote "IPA-0015"
    Y se asignan 12 UND del lote "IPA-0018"
    Y no se asigna nada del lote "IPA-0012" porque está vencido

  @UC-INV-04 @borde @RF-INV-22 @RF-CAT-62
  Escenario: Un producto con estrategia FIFO saca primero el lote más antiguo
    Dado que "TER-IPA-330" tiene la estrategia de salida "FIFO"
    Y que el lote "IPA-0018" ingresó el "2026-09-01" y el lote "IPA-0015" el "2026-10-01"
    Cuando se solicita la salida de 60 UND de "TER-IPA-330" sin indicar lote
    Entonces se asignan 60 UND del lote "IPA-0018"
    Y no se asigna nada del lote "IPA-0012" porque está vencido

  @UC-INV-04 @RN-INV-06 @borde @RF-INV-19 @RF-INV-22
  Escenario: Stock disponible insuficiente sin contar vencidos
    Cuando se solicita la salida de 170 UND de "TER-IPA-330" sin indicar lote
    Entonces la operación es rechazada con el mensaje "Stock disponible insuficiente: 168 UND sin vencer"

  @UC-INV-04 @RN-INV-07 @borde @RF-INV-23
  Escenario: Lote vencido solo sale por merma
    Cuando registro un ajuste "MERMA" de 10 UND de "TER-IPA-330" del lote "IPA-0012" con motivo "Vencido"
    Entonces el lote "IPA-0012" queda con stock 0

  @UC-INV-04 @RN-INV-07 @borde @RF-INV-23
  Escenario: Lote vencido no sale por corrección
    Cuando registro un ajuste "CORRECCION" de salida de 10 UND de "TER-IPA-330" del lote "IPA-0012"
    Entonces la operación es rechazada con el mensaje "El lote IPA-0012 está vencido: solo puede salir por merma"

  @UC-INV-01 @borde @RF-INV-03
  Escenario: Almacén con stock no se desactiva
    Dado que el almacén "Taproom" tiene stock
    Cuando intento desactivar el almacén "Taproom"
    Entonces la operación es rechazada con el mensaje "El almacén tiene stock"

  @UC-INV-04 @RN-INV-06 @borde @RF-INV-22
  Escenario: El stock sin lote sale al final en FEFO
    Dado que "TER-IPA-330" también tiene 5 UND sin lote en "Principal"
    Cuando se solicita la salida de 170 UND de "TER-IPA-330" sin indicar lote
    Entonces se asignan 48 UND del lote "IPA-0015"
    Y se asignan 120 UND del lote "IPA-0018"
    Y se asignan 2 UND sin lote

  @UC-INV-04 @borde @RF-INV-26
  Escenario: Lote nuevo con vencimiento sugerido por la vida útil
    Dado que "TER-IPA-330" tiene vida útil de 120 días
    Cuando entra un lote "IPA-0020" de 24 UND de "TER-IPA-330" sin indicar vencimiento
    Entonces el lote "IPA-0020" vence el "2027-03-01"

  @UC-INV-04 @borde @RF-INV-26
  Escenario: Lote existente con otro vencimiento
    Cuando entra el lote "IPA-0015" de 12 UND de "TER-IPA-330" con vencimiento "2027-01-31"
    Entonces la operación es rechazada con el mensaje "El lote IPA-0015 ya existe con vencimiento 2026-12-15"

  @UC-INV-04 @borde @RF-INV-25
  Escenario: Un servicio no lleva stock
    Dado que existe el servicio "SRV-TOUR" (visita guiada)
    Cuando se intenta registrar una entrada de 1 SERV de "SRV-TOUR"
    Entonces la operación es rechazada con el mensaje "Un servicio no lleva stock"
