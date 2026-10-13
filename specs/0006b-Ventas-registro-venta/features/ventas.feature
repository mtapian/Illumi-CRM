# language: es
@E06 @E06b @mvp
Característica: Facturación, entrega y cobranza de pedidos
  Como vendedor
  Quiero facturar y entregar los pedidos, vender en mostrador y cobrar
  Para descontar el stock correcto, conocer el costo real y saber qué me deben

  Antecedentes:
    Dado que soy usuario "ventas" de "Cervecería Andina"
    Y la fecha de hoy es "2026-12-01"
    Y el cliente "Bar El Lúpulo" con RUC "20512345671" y canal "B2B"
    Y el cliente "Ana Torres" con DNI "45678912"
    Y "TER-IPA-330" se vende a 12.00 con "IGV 18%", costo promedio 1.893080 y stock en "Principal":
      | lote     | vence      | cantidad |
      | IPA-0015 | 2026-12-15 | 10       |
      | IPA-0020 | 2027-03-25 | 1000     |

  @UC-VEN-05 @critico @RF-VEN-17 @RF-VEN-19 @RF-VEN-20 @RF-VEN-21 @RF-VEN-22 @RF-VEN-38
  Escenario: Facturar un pedido aprobado
    Dado un pedido aprobado de "Bar El Lúpulo" con 24 "TER-IPA-330"
    Cuando facturo el pedido desde "Principal" al contado
    Entonces el pedido queda Facturado
    Y salen 10 unidades del lote "IPA-0015" y 14 del lote "IPA-0020" con costo total 45.43
    Y el comprobante pendiente es una "Factura" del "2026-12-01" con una línea de 24 unidades:
      | valor  | isc  | igv   | total  |
      | 244.07 | 0.00 | 43.93 | 288.00 |
    Y la cobranza queda Pendiente por 288.00 con vencimiento "2026-12-01"

  @UC-VEN-05 @critico @RF-VEN-17 @RF-VEN-26
  Escenario: Facturar vuelve a validar el stock
    Dado un pedido aprobado de "Bar El Lúpulo" con 1000 "TER-IPA-330"
    Y una salida de 20 "TER-IPA-330" del lote "IPA-0020"
    Cuando facturo el pedido desde "Principal" al contado
    Entonces el resultado es "Stock insuficiente: TER-IPA-330 faltan 10"
    Y el pedido queda Aprobado
    Y no hay cobranzas

  @UC-VEN-05 @RF-VEN-20
  Escenario: Elegir el lote al facturar
    Dado un pedido aprobado de "Bar El Lúpulo" con 24 "TER-IPA-330"
    Cuando facturo el pedido eligiendo el lote "IPA-0020"
    Entonces salen 24 unidades del lote "IPA-0020"

  @UC-VEN-05 @borde @RF-VEN-23
  Escenario: Un producto desactivado después de aprobar no se factura
    Dado un pedido aprobado de "Bar El Lúpulo" con 24 "TER-IPA-330"
    Y el producto "TER-IPA-330" está inactivo
    Cuando facturo el pedido desde "Principal" al contado
    Entonces el resultado es "TER-IPA-330 ya no se vende"

  @UC-VEN-05 @borde @RF-VEN-24 @RF-VEN-25
  Esquema del escenario: El comprobante sale del cliente
    Dado un pedido aprobado de "<cliente>" con <cantidad> "TER-IPA-330"
    Cuando facturo el pedido desde "Principal" al contado
    Entonces el resultado es "<resultado>"

    Ejemplos:
      | cliente         | cantidad | resultado                                                        |
      | Bar El Lúpulo   | 60       | Factura                                                          |
      | Ana Torres      | 60       | Boleta                                                           |
      | Clientes varios | 24       | Boleta                                                           |
      | Clientes varios | 60       | Las boletas mayores a S/ 700.00 requieren identificar al cliente |

  @UC-VEN-05 @critico @RF-VEN-19 @RF-VEN-27 @RN-VEN-08
  Escenario: Factura a crédito en cuotas
    Dado un pedido aprobado de "Bar El Lúpulo" con 24 "TER-IPA-330"
    Cuando facturo el pedido a crédito con las cuotas:
      | monto  | vence      |
      | 144.00 | 2026-12-16 |
      | 144.00 | 2026-12-31 |
    Entonces el pedido queda Facturado
    Y la factura declara forma de pago "Crédito" con monto pendiente 288.00 y 2 cuotas
    Y la cobranza queda Pendiente por 288.00 con próximo vencimiento "2026-12-16"

  @UC-VEN-05 @borde @RF-VEN-27 @RN-VEN-08
  Esquema del escenario: Crédito inválido
    Dado un pedido aprobado de "<cliente>" con 24 "TER-IPA-330"
    Cuando facturo el pedido a crédito con las cuotas "<cuotas>"
    Entonces el resultado es "<mensaje>"
    Y el pedido queda Aprobado

    Ejemplos:
      | cliente       | cuotas                  | mensaje                                                                   |
      | Ana Torres    | 288.00 vence 2026-12-31 | La venta a crédito requiere factura (cliente con RUC)                     |
      | Bar El Lúpulo | ninguna                 | Una venta a crédito requiere al menos una cuota                           |
      | Bar El Lúpulo | 288.00 vence 2026-12-01 | El vencimiento de cada cuota debe ser posterior a la emisión              |
      | Bar El Lúpulo | 200.00 vence 2026-12-31 | La suma de las cuotas (200.00) debe ser igual al monto pendiente (288.00) |

  @UC-VEN-05 @critico @RF-VEN-26
  Escenario: Dos usuarios facturan a la vez el último stock
    Dado dos pedidos aprobados de "Bar El Lúpulo" con 1010 "TER-IPA-330" cada uno
    Cuando dos usuarios facturan los dos pedidos al mismo tiempo
    Entonces solo un pedido queda Facturado
    Y el stock de "TER-IPA-330" queda en 0

  @UC-VEN-05 @critico @RF-VEN-21
  Escenario: El costo de la venta no cambia cuando cambia el costo promedio
    Dado un pedido facturado de "Bar El Lúpulo" con 24 "TER-IPA-330" y costo total 45.43
    Cuando entra una compra de 100 "TER-IPA-330" a costo 3.00
    Entonces el costo total del pedido sigue siendo 45.43

  @UC-VEN-05 @RF-VEN-51
  Escenario: Confirmar la entrega
    Dado un pedido facturado de "Bar El Lúpulo" con 24 "TER-IPA-330" y costo total 45.43
    Cuando confirmo la entrega
    Entonces el pedido queda Entregado
    Y la cobranza sigue Pendiente

  @UC-VEN-07 @critico @RF-VEN-18
  Escenario: Venta directa con dos métodos de pago
    Cuando registro una venta directa desde "Principal" de 24 "TER-IPA-330" con los pagos:
      | método   | monto  |
      | Efectivo | 200.00 |
      | Yape     | 88.00  |
    Entonces el pedido de "Clientes varios" queda Entregado con total 288.00 y "Boleta"
    Y la cobranza queda Pagada

  @UC-VEN-07 @borde @RF-VEN-52
  Escenario: Los pagos de una venta directa deben sumar el total
    Cuando registro una venta directa desde "Principal" de 24 "TER-IPA-330" con los pagos:
      | método   | monto  |
      | Efectivo | 300.00 |
    Entonces el resultado es "Los pagos (300.00) deben sumar el total (288.00)"
    Y no hay cobranzas

  @UC-VEN-09 @critico @RF-VEN-53 @RF-VEN-54
  Escenario: Cobrar un pedido entregado en dos pagos
    Dado un pedido facturado de "Bar El Lúpulo" con 24 "TER-IPA-330" y costo total 45.43
    Cuando registro un pago de 100.00 por "Transferencia"
    Entonces la cobranza queda Parcial con saldo 188.00
    Cuando registro un pago de 188.00 por "Yape"
    Entonces la cobranza queda Pagada con saldo 0.00

  @UC-VEN-09 @borde @RF-VEN-55 @RF-VEN-57
  Esquema del escenario: Pagos que no se aceptan
    Dado un pedido facturado de "Bar El Lúpulo" con 24 "TER-IPA-330" y costo total 45.43
    Y un pago de <previo> por "Efectivo"
    Cuando registro un pago de <monto> por "Efectivo"
    Entonces el resultado es "<mensaje>"

    Ejemplos:
      | previo | monto  | mensaje                                                       |
      | 0.00   | 300.00 | El pago debe ser mayor a 0 y no superar el saldo (288.00)     |
      | 100.00 | 0.00   | El pago debe ser mayor a 0 y no superar el saldo (188.00)     |
      | 288.00 | 1.00   | La cobranza ya está pagada                                    |

  @UC-VEN-09 @RF-VEN-54 @RF-VEN-56 @RF-VEN-61
  Escenario: Anular un pago recalcula el estado de la cobranza
    Dado un pedido facturado de "Bar El Lúpulo" con 24 "TER-IPA-330" y costo total 45.43
    Y un pago de 100.00 por "Efectivo"
    Y un pago de 188.00 por "Yape"
    Cuando como usuario "gerente" anulo el pago de 188.00 con el motivo "Monto mal digitado"
    Entonces la cobranza queda Parcial con saldo 188.00
    Y el pago queda anulado con su motivo

  @UC-VEN-09 @RF-VEN-53
  Escenario: Cobranzas vencidas
    Dado un pedido de "Bar El Lúpulo" facturado a crédito el "2026-11-01" con las cuotas:
      | monto  | vence      |
      | 144.00 | 2026-11-16 |
      | 144.00 | 2026-12-16 |
    Y un pago de 100.00 por "Transferencia"
    Cuando abro las cobranzas con el filtro "solo vencidas"
    Entonces veo la cobranza de "Bar El Lúpulo" marcada Vencida con monto vencido 44.00

  @UC-VEN-10 @RF-VEN-58 @RF-VEN-59 @RF-VEN-64
  Escenario: Métodos de pago de la empresa
    Entonces la empresa tiene los métodos de pago "Efectivo, Yape, Plin, Tarjeta, Transferencia"
    Cuando como usuario "gerente" desactivo el método de pago "Plin"
    Entonces "Plin" no se ofrece en un pago nuevo
    Cuando como usuario "gerente" creo el método de pago "yape"
    Entonces el resultado es "Ya existe un método de pago con ese nombre"

  @UC-VEN-09 @RF-VEN-61
  Escenario: Quien registra pagos no los anula
    Dado un pedido facturado de "Bar El Lúpulo" con 24 "TER-IPA-330" y costo total 45.43
    Y un pago de 288.00 por "Efectivo"
    Cuando como usuario "ventas" intento anular el pago con el motivo "Error"
    Entonces el resultado es "Acceso denegado"
    Cuando como usuario "gerente" anulo el pago con el motivo "Error"
    Entonces la cobranza queda Pendiente con saldo 288.00

  @UC-VEN-09 @RF-VEN-62
  Escenario: Aviso de cobranzas vencidas en el inicio
    Dado un pedido de "Bar El Lúpulo" facturado a crédito el "2026-11-01" con las cuotas:
      | monto  | vence      |
      | 288.00 | 2026-11-16 |
    Cuando abro el inicio
    Entonces veo la alerta "1 cobranza vencida"
    Y la alerta lleva al listado de cobranzas filtrado por "solo vencidas"

  @UC-VEN-09 @RF-VEN-63
  Escenario: Estado de cobro en el listado de pedidos
    Dado un pedido facturado de "Bar El Lúpulo" con 24 "TER-IPA-330" y costo total 45.43
    Y un pago de 100.00 por "Efectivo"
    Cuando abro el listado de pedidos
    Entonces el pedido facturado muestra "Cobro parcial"
