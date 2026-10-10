# language: es
@E06 @E06c @mvp
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

  @UC-VEN-08 @borde @RF-VEN-40
  Escenario: No se corrige el cliente si el comprobante aún no fue aceptado
    Dado la venta "V-000007" con factura "F001-00000007" en estado "PENDIENTE"
    Cuando un usuario "gerente" intenta corregir el cliente de "V-000007"
    Entonces la operación es rechazada con el mensaje "El comprobante F001-00000007 todavía no fue aceptado por SUNAT; intenta cuando lo esté"
