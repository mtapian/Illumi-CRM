# language: es
@E03 @mvp
Característica: Ajustes, lotes, almacenes y alertas
  Como encargado de almacén
  Quiero corregir el stock con evidencia y controlar lotes y vencimientos
  Para que el sistema refleje lo que hay físicamente

  Antecedentes:
    Dado que soy usuario "almacen" de "Cervecería Andina"
    Y la fecha de hoy es "2026-11-01"
    Y el producto terminado "TER-IPA-330" con stock por lote en "Principal":
      | lote      | vence      | cantidad |
      | IPA-0012  | 2026-10-30 | 10       |
      | IPA-0015  | 2026-12-15 | 48       |
      | IPA-0018  | 2027-02-20 | 120      |

  @UC-INV-04 @critico @RF-INV-08
  Escenario: Ajuste por conteo físico calcula la diferencia
    Dado que "INS-LUP-CS" tiene stock 1500 G con promedio 0.120000
    Cuando registro un ajuste "CONTEO" de "INS-LUP-CS" con cantidad contada 1420 G y motivo "Inventario mensual"
    Entonces se registra una salida de 80 G a costo 0.120000
    Y el stock de "INS-LUP-CS" es 1420 G

  @UC-INV-04 @RF-INV-11
  Escenario: Conteo igual al sistema no mueve stock
    Dado que "INS-LUP-CS" tiene stock 1500 G
    Cuando registro un ajuste "CONTEO" con cantidad contada 1500 G
    Entonces el ajuste queda registrado con diferencia 0
    Y no se genera movimiento de kardex

  @UC-INV-04 @borde @RF-INV-09
  Escenario: Saldo inicial sin costo es rechazado
    Cuando registro un ajuste "SALDO_INICIAL" de 20 KG de "INS-MALTA" sin costo unitario
    Entonces la operación es rechazada con el mensaje "El saldo inicial requiere un costo unitario mayor a 0"

  @UC-INV-04 @borde @RF-INV-08
  Escenario: Ajuste sin motivo es rechazado
    Cuando registro un ajuste "MERMA" de 1 UND de "ENV-BOT330" sin motivo
    Entonces la operación es rechazada con el mensaje "El motivo es obligatorio"

  @UC-INV-04 @RF-INV-10
  Escenario: Saldo inicial de producto con lote crea el lote
    Cuando registro un ajuste "SALDO_INICIAL" de 60 UND de "TER-IPA-330" a costo 4.100000 con lote "IPA-0009" que vence el "2026-12-01"
    Entonces existe el lote "IPA-0009" de "TER-IPA-330" con 60 UND en "Principal"

  @UC-INV-04 @borde @RF-INV-13 @RF-INV-20
  Escenario: Anular un ajuste revierte sus movimientos
    Dado un ajuste "MERMA" de 20 KG de "INS-MALTA" a costo 4.333333
    Cuando un usuario "gerente" lo anula con motivo "Saco recuperado"
    Entonces se registra una entrada "ANULACION" de 20 KG a costo 4.333333
    Y el ajuste queda en estado "ANULADO"

  @UC-INV-04 @RN-INV-06 @critico @RF-INV-22
  Escenario: Asignación FEFO excluye lotes vencidos
    Cuando se solicita la salida de 60 UND de "TER-IPA-330" sin indicar lote
    Entonces se asignan 48 UND del lote "IPA-0015"
    Y se asignan 12 UND del lote "IPA-0018"
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

  @UC-INV-04 @borde @RF-INV-12 @RF-FIN-09
  Escenario: Transferencia entre almacenes no cambia el costo ni el resultado
    Dado el almacén "Taproom"
    Y "INS-MALTA" con stock 100 KG en "Principal" y costo promedio 4.000000
    Cuando registro un ajuste "TRANSFERENCIA" de 20 KG de "INS-MALTA" de "Principal" a "Taproom"
    Entonces "Principal" queda con 80 KG y "Taproom" con 20 KG
    Y la salida y la entrada se registran a costo 4.000000
    Y el costo promedio de "INS-MALTA" sigue siendo 4.000000
    Y la transferencia no aparece en "Mermas y ajustes" del estado de resultados

  @UC-INV-06 @RF-INV-15
  Escenario: Alerta de lotes por vencer
    Dado que el umbral de alerta de vencimiento es 45 días
    Cuando abro el dashboard
    Entonces el widget "Por vencer" muestra el lote "IPA-0015" con 44 días restantes
    Y muestra el lote "IPA-0012" como "Vencido"
    Y no muestra el lote "IPA-0018"

  @UC-INV-05 @RF-INV-14
  Escenario: Alerta de stock bajo mínimo
    Dado que "ENV-TAPA" tiene stock mínimo 500 y stock 320
    Cuando abro el dashboard
    Entonces el widget "Stock bajo" muestra "ENV-TAPA" con 320 de 500

  @UC-INV-01 @borde @RF-INV-03
  Escenario: Almacén con stock no se desactiva
    Dado que el almacén "Taproom" tiene stock
    Cuando intento desactivar "Taproom"
    Entonces la operación es rechazada con el mensaje "El almacén tiene stock"

  @UC-INV-02 @RF-INV-04 @RF-INV-05
  Escenario: Stock valorizado por tipo
    Cuando consulto el stock con filtro tipo "TERMINADO"
    Entonces veo cada presentación con su stock total, el detalle por almacén y lote, el costo promedio y el valor total
