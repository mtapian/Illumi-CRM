# language: es
@E05 @E05b @mvp
Característica: Envasado de un lote en varias presentaciones
  Como maestro cervecero
  Quiero envasar el granel de un lote en botellas y barriles
  Para tener stock vendible con costo unitario y trazabilidad de lote

  Antecedentes:
    Dado que soy usuario "produccion" de "Cervecería Andina"
    Y la OP "OP-000020" en estado "TERMINADA" con el lote "IPA-0020" de 425 L de "GRA-IPA" a 2.000000 por L
    Y no hay otro stock de "GRA-IPA"
    Y las presentaciones de "GRA-IPA":
      | presentacion | contenido_l | vida_util_dias | materiales por unidad                                                  |
      | TER-IPA-330  | 0.3300      | 120            | ENV-BOT330 1, ENV-TAPA 1, ENV-ETQ-IPA 1, ENV-CAJA24 0.0417               |
      | TER-IPA-B20  | 20.0000     | 60             | ENV-PREC 1                                                             |
    Y el stock de envases en "Principal" con costo promedio:
      | envase      | stock | costo    |
      | ENV-BOT330  | 1200  | 0.850000 |
      | ENV-TAPA    | 2000  | 0.050000 |
      | ENV-ETQ-IPA | 1500  | 0.200000 |
      | ENV-CAJA24  | 60    | 2.400000 |
      | ENV-PREC    | 20    | 1.500000 |

  @UC-PRD-06 @critico @RF-PRD-20 @RF-PRD-24
  Escenario: Envasado multipresentación con merma absorbida en el costo
    Cuando registro el envasado de "OP-000020" el "2026-11-25" en "Principal":
      | presentacion | unidades |
      | TER-IPA-330  | 1000     |
      | TER-IPA-B20  | 3        |
    Y declaro 19.5 L de merma de envasado
    Entonces el envasado "E-000031" queda registrado
    Y se registra una salida "CONSUMO_ENVASADO" de 409.5 L de "GRA-IPA" del lote "IPA-0020" por 819.00
    Y se registran salidas de materiales:
      | envase      | cantidad | costo_total |
      | ENV-BOT330  | 1000     | 850.00      |
      | ENV-TAPA    | 1000     | 50.00       |
      | ENV-ETQ-IPA | 1000     | 200.00      |
      | ENV-CAJA24  | 41.7000  | 100.08      |
      | ENV-PREC    | 3        | 4.50        |
    Y se registran entradas "ENVASADO" con lote "IPA-0020":
      | presentacion | unidades | costo_unitario | costo_total | vence      |
      | TER-IPA-330  | 1000     | 1.893080       | 1893.08     | 2027-03-25 |
      | TER-IPA-B20  | 3        | 43.500000      | 130.50      | 2027-01-24 |
    Y el lote "IPA-0020" de "GRA-IPA" queda con 15.5 L
    Y "OP-000020" sigue "TERMINADA"

  @UC-PRD-06 @critico @RF-PRD-24
  Escenario: Conservación del costo en el envasado
    Dado un envasado registrado de "OP-000020"
    Entonces la suma del costo de las entradas de terminados es igual al costo del granel consumido más el costo de los materiales consumidos

  @UC-PRD-06 @critico @borde @RF-PRD-21
  Escenario: Envasado que excede el granel disponible del lote
    Cuando registro el envasado de "OP-000020" con 22 unidades de "TER-IPA-B20"
    Entonces la operación es rechazada con el mensaje "El envasado requiere 440.0000 L y el lote IPA-0020 tiene 425.0000 L"

  @UC-PRD-06 @borde @RF-PRD-23
  Escenario: Materiales insuficientes
    Cuando registro el envasado de "OP-000020" con 1250 unidades de "TER-IPA-330"
    Entonces la operación es rechazada con el mensaje "Stock insuficiente: ENV-BOT330 requiere 1250 y hay 1200"
    Y no se registra ningún movimiento

  @UC-PRD-06 @borde @RF-PRD-22
  Escenario: Solo presentaciones del mismo granel
    Dado la presentación "TER-STOUT-330" del granel "GRA-STOUT"
    Cuando registro el envasado de "OP-000020" con 100 unidades de "TER-STOUT-330"
    Entonces la operación es rechazada con el mensaje "TER-STOUT-330 no es una presentación de GRA-IPA"

  @UC-PRD-06 @RF-PRD-25 @RF-PRD-29
  Escenario: Segundo envasado del mismo lote en otra fecha
    Dado un envasado previo de 1000 unidades de "TER-IPA-330" del lote "IPA-0020" que vencen el "2027-03-25"
    Cuando registro otro envasado de "OP-000020" el "2026-12-01" con 40 unidades de "TER-IPA-330"
    Entonces el lote "IPA-0020" de "TER-IPA-330" tiene 1040 unidades
    Y su vencimiento sigue siendo "2027-03-25"

  @UC-PRD-07 @critico @RF-PRD-30 @RF-PRD-26
  Escenario: La OP se cierra automáticamente al agotar el granel
    Dado que el lote "IPA-0020" de "GRA-IPA" tiene 15.5 L
    Cuando registro el envasado de "OP-000020" con 0 unidades y 15.5 L de merma
    Entonces se registra una salida "MERMA" de 15.5 L de "GRA-IPA" por 31.00
    Y el lote "IPA-0020" de "GRA-IPA" queda con 0 L
    Y "OP-000020" queda "CERRADA"

  @UC-PRD-07 @RF-PRD-31
  Escenario: Cierre manual con saldo registra merma
    Dado que el lote "IPA-0020" de "GRA-IPA" tiene 15.5 L
    Cuando cierro "OP-000020" con motivo "Fondo de tanque"
    Entonces se registra una salida "MERMA" de 15.5 L de "GRA-IPA" por 31.00
    Y "OP-000020" queda "CERRADA"

  @UC-PRD-08 @RF-PRD-34
  Escenario: Reporte de costo y rendimiento del lote
    Dado "OP-000020" con el envasado "E-000031" registrado
    Cuando consulto el reporte de "OP-000020"
    Entonces veo:
      | indicador                | valor    |
      | Litros planificados      | 500.00   |
      | Litros reales            | 425.00   |
      | Rendimiento              | 85.00 %  |
      | Costo por litro          | 2.000000 |
      | Litros envasados         | 390.00   |
      | Merma de envasado        | 19.50 L  |
      | Merma de envasado %      | 4.76 %   |
      | Costo unitario botella   | 1.893080 |
      | Costo unitario barril    | 43.500000|
      | Saldo de granel          | 15.50 L  |
