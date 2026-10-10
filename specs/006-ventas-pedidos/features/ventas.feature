# language: es
@E06 @mvp
Característica: Registro y anulación de ventas
  Como vendedor
  Quiero registrar ventas con su lote y comprobante
  Para entregar al cliente y conocer el costo real de lo vendido

  Antecedentes:
    Dado que soy usuario "ventas" de "Cervecería Andina" con IGV 18 %
    Y la fecha de hoy es "2026-12-01"
    Y el ISC está desactivado para este escenario
    Y el cliente "Bar El Lúpulo" con RUC "20512345671"
    Y el cliente genérico "Clientes varios"
    Y "TER-IPA-330" con costo promedio 1.893080 y stock por lote en "Principal":
      | lote      | vence      | cantidad |
      | IPA-0015  | 2026-12-15 | 10       |
      | IPA-0020  | 2027-03-25 | 1000     |

  @UC-VEN-05 @critico @RF-VEN-18 @RF-VEN-19 @RF-VEN-20 @RF-VEN-21 @RF-VEN-22
  Escenario: Venta directa con boleta, FEFO y snapshot de costo
    Cuando registro una venta "BOLETA" a "Clientes varios" en "Principal" con pago "EFECTIVO" recibido 300.00:
      | presentacion | cantidad | precio |
      | TER-IPA-330  | 24       | 12.00  |
    Entonces la venta "V-000001" queda "EMITIDA" con:
      | valor_venta | igv   | total  | vuelto |
      | 244.07      | 43.93 | 288.00 | 12.00  |
    Y se asignan 10 unidades del lote "IPA-0015" y 14 del lote "IPA-0020"
    Y el comprobante tiene una sola línea de 24 unidades con valor de venta 244.07 e IGV 43.93
    Y el reparto por lote guarda costo unitario 1.893080 y costo total 45.43
    Y el kardex registra salidas "VENTA" que referencian "V-000001"
    Y se solicita la emisión del comprobante electrónico

  @UC-VEN-05 @critico @RF-VEN-14 @RF-VEN-17 @RF-VEN-27
  Escenario: Venta desde pedido con factura a crédito en cuotas
    Dado el pedido "P-000001" de "Bar El Lúpulo" en estado "LISTO" con 96 unidades de "TER-IPA-330" a 11.00
    Cuando registro la venta del pedido "P-000001" con "FACTURA", forma de pago "CREDITO" y cuotas:
      | numero | monto  | vence      |
      | 1      | 528.00 | 2026-12-16 |
      | 2      | 528.00 | 2026-12-31 |
    Entonces la venta tiene total 1056.00
    Y el comprobante informa forma de pago "Crédito", monto pendiente 1056.00 y las 2 cuotas
    Y "P-000001" queda "ENTREGADO"

  @UC-VEN-05 @critico @RF-VEN-21
  Escenario: El costo histórico no cambia cuando cambia el costo promedio
    Dado la venta "V-000001" con costo total 45.43
    Cuando el costo promedio de "TER-IPA-330" cambia a 2.100000 por un nuevo envasado
    Entonces el costo total de "V-000001" sigue siendo 45.43

  @UC-VEN-05 @borde @RF-VEN-24 @RF-VEN-25
  Esquema del escenario: Reglas del comprobante según el cliente
    Cuando registro una venta "<comprobante>" a "<cliente>" por un total de <total>
    Entonces el resultado es "<resultado>"

    Ejemplos:
      | comprobante | cliente         | total  | resultado                                                    |
      | FACTURA     | Clientes varios | 288.00 | La factura requiere un cliente con RUC                       |
      | BOLETA      | Clientes varios | 720.00 | Las boletas mayores a S/ 700.00 requieren identificar al cliente |
      | BOLETA      | Bar El Lúpulo   | 720.00 | emitida                                                      |
      | FACTURA     | Bar El Lúpulo   | 288.00 | emitida                                                      |

  @UC-VEN-05 @borde @RF-VEN-26
  Escenario: Stock insuficiente sin contar lotes vencidos
    Dado que el lote "IPA-0015" vence el "2026-11-30"
    Cuando registro una venta de 1001 unidades de "TER-IPA-330"
    Entonces la operación es rechazada con el mensaje "Stock disponible insuficiente: 1000 UND sin vencer"

  @UC-VEN-05 @borde @RF-VEN-20
  Escenario: Selección manual de lote
    Cuando registro una venta de 24 unidades de "TER-IPA-330" eligiendo el lote "IPA-0020"
    Entonces se asignan 24 unidades del lote "IPA-0020"

  @UC-VEN-05 @borde @RF-VEN-29
  Escenario: Doble envío no duplica la venta
    Cuando envío dos veces el mismo formulario de venta con el mismo token
    Entonces existe una sola venta

  @UC-VEN-05 @RN-VEN-08 @borde @RF-VEN-27
  Esquema del escenario: Cuotas inválidas en una venta a crédito
    Cuando registro una venta "FACTURA" a crédito por 1056.00 con las cuotas "<cuotas>"
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | cuotas                               | mensaje                                                       |
      | ninguna                              | Una venta a crédito requiere al menos una cuota               |
      | 1056.00 vence 2026-12-01             | La fecha de vencimiento debe ser posterior a la emisión       |
      | 500.00 vence 2026-12-31              | La suma de las cuotas (500.00) debe ser igual al total (1056.00) |

  @UC-VEN-05 @borde @RF-VEN-26
  Escenario: Dos ventas simultáneas por el último stock
    Dado que de "TER-IPA-330" solo quedan 10 unidades sin vencer en "Principal"
    Cuando dos usuarios registran al mismo tiempo una venta de 10 unidades de "TER-IPA-330"
    Entonces solo una venta tiene éxito
    Y la otra es rechazada con el mensaje "Stock disponible insuficiente: 0 UND sin vencer"
    Y el stock de "TER-IPA-330" queda en 0

  @UC-VEN-05 @RN-VEN-01 @borde @RF-VEN-23
  Escenario: Solo se venden presentaciones y mercadería activas
    Cuando registro una venta de 5 KG de "INS-MALTA"
    Entonces la operación es rechazada con el mensaje "Solo se pueden vender presentaciones y mercadería activas"

  @UC-VEN-05 @RN-VEN-01 @critico @RF-VEN-18 @RF-VEN-22
  Escenario: Venta mixta de cerveza propia y mercadería de reventa
    Dado "MER-AGUA-500" con costo promedio 1.200000 y stock en "Principal" del lote "AG-2611A" (vence 2027-11-01): 120
    Y "MER-POLO-M" sin lote, con costo promedio 18.000000 y stock 10 en "Principal"
    Cuando registro una venta "BOLETA" a "Clientes varios" en "Principal" con pago "EFECTIVO":
      | producto     | cantidad | precio |
      | TER-IPA-330  | 6        | 12.00  |
      | MER-AGUA-500 | 2        | 3.00   |
      | MER-POLO-M   | 1        | 45.00  |
    Entonces la venta tiene total 123.00
    Y se registran salidas "VENTA" de 6 "TER-IPA-330" por FEFO, 2 "MER-AGUA-500" del lote "AG-2611A" y 1 "MER-POLO-M" sin lote
    Y el costo de la venta es 11.36 + 2.40 + 18.00 = 31.76

  @UC-VEN-06 @critico @RF-VEN-32 @RF-VEN-33
  Escenario: Anular venta revierte stock a los mismos lotes y costo
    Dado la venta "V-000001" que tomó 10 unidades del lote "IPA-0015" y 14 del lote "IPA-0020" a 1.893080
    Cuando un usuario "gerente" anula "V-000001" con motivo SUNAT "06 Devolución total" y reingreso de mercadería
    Entonces se registran entradas "ANULACION" de 10 unidades al lote "IPA-0015" y 14 al lote "IPA-0020" a costo 1.893080
    Y "V-000001" queda "ANULADA"
    Y se registra la nota de crédito del comprobante en la misma operación

  @UC-VEN-08 @borde @RF-VEN-39
  Escenario: Corregir el RUC de una factura no mueve stock ni costo
    Dado la venta "V-000001" con factura "F001-00000007" aceptada a "Bar El Lúpulo" que tomó 24 unidades a 1.893080
    Y el cliente correcto es "Bar El Lúpulo SAC" con RUC "20601234565"
    Cuando un usuario "gerente" corrige el cliente de "V-000001" a "Bar El Lúpulo SAC"
    Entonces se emite una nota de crédito con motivo SUNAT "02 Anulación por error en el RUC" sobre "F001-00000007"
    Y se emite una factura nueva a "Bar El Lúpulo SAC" con las mismas líneas e importes
    Y "V-000001" sigue "EMITIDA" con costo de ventas 45.43
    Y no se registran movimientos de stock

  @UC-VEN-06 @RN-VEN-09 @borde @RF-VEN-34
  Escenario: Anular sin reingreso de mercadería mantiene el costo de ventas
    Dado la venta "V-000001" que tomó 24 unidades a 1.893080
    Cuando un usuario "gerente" anula "V-000001" con motivo SUNAT "01 Anulación de la operación" sin reingreso de mercadería
    Entonces no se registran entradas de stock
    Y "V-000001" queda "ANULADA"
    Y su costo de ventas de 45.43 se mantiene

  @UC-VEN-06 @borde @RF-VEN-36
  Escenario: Doble anulación concurrente revierte una sola vez
    Dado la venta "V-000001" que tomó 10 unidades del lote "IPA-0015" y 14 del lote "IPA-0020"
    Cuando dos usuarios "gerente" anulan "V-000001" al mismo tiempo
    Entonces solo una anulación tiene éxito
    Y existe una sola entrada "ANULACION" por cada lote de "V-000001"

  @UC-VEN-06 @borde @RF-VEN-35
  Escenario: Anular venta de un pedido devuelve el pedido a LISTO
    Dado la venta "V-000002" generada desde el pedido "P-000001"
    Cuando un usuario "gerente" anula "V-000002"
    Entonces "P-000001" vuelve a "LISTO"

  @UC-VEN-06 @borde @RF-VEN-32
  Escenario: Rol ventas no puede anular
    Cuando un usuario "ventas" intenta anular "V-000001"
    Entonces la operación es denegada
