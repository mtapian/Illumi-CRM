# language: es
@E08 @E08b @mvp
Característica: Gastos operativos y estado de resultados
  Como dueño de la cervecera
  Quiero ver la utilidad bruta y operativa de un período
  Para saber cuánto gano realmente

  Antecedentes:
    Dado que soy usuario "admin" de "Cervecería Andina" con IGV 18 %

  @UC-FIN-03 @critico @RF-FIN-06 @RF-FIN-07 @RF-FIN-09
  Escenario: Estado de resultados del mes
    Dado en noviembre de 2026:
      | documento | fecha      | evento                   | valor_venta | costo  |
      | V-000101  | 2026-11-05 | venta emitida            | 1000.00     | 400.00 |
      | V-000102  | 2026-11-18 | venta emitida            | 500.00      | 200.00 |
      | V-000090  | 2026-11-20 | venta de octubre anulada | 100.00      | 40.00  |
    Y ajustes de inventario de noviembre con salidas por 106.67 y entradas por 20.00
    Y un "SALDO_INICIAL" de noviembre por 5000.00
    Y gastos de noviembre: "Alquiler" 300.00 y "Planilla" 200.00
    Cuando consulto el estado de resultados del "2026-11-01" al "2026-11-30"
    Entonces veo:
      | linea                         | importe |
      | Ventas netas                  | 1400.00 |
      | Costo de ventas               | 560.00  |
      | Mermas y ajustes              | 86.67   |
      | Pérdidas de producción        | 0.00    |
      | Utilidad bruta                | 753.33  |
      | Gastos operativos             | 500.00  |
      | Utilidad operativa            | 253.33  |
      | Margen bruto %                | 53.81   |
      | Margen operativo %            | 18.10   |

  @UC-FIN-03 @critico @RF-FIN-08
  Escenario: La anulación resta en el período en que se anula
    Dado la venta "V-000090" emitida el "2026-10-28" con valor 100.00 y costo 40.00
    Y anulada el "2026-11-20"
    Entonces el estado de resultados de octubre incluye ventas por 100.00 y costo 40.00
    Y el estado de resultados de noviembre resta ventas por 100.00 y costo 40.00

  @UC-FIN-03 @borde @pendiente-q10 @RF-FIN-06 @RF-PRD-15
  Escenario: Pérdida de producción en el período
    Dado la OP "OP-000020" terminada con 0 L el "2026-11-12" con costo 798.00
    Cuando consulto el estado de resultados de noviembre de 2026
    Entonces la línea "Pérdidas de producción" es 798.00

  @UC-FIN-03 @borde @RF-FIN-13
  Escenario: Período sin ventas
    Cuando consulto el estado de resultados de un período sin ventas
    Entonces las ventas netas son 0.00
    Y los márgenes se muestran como "—"

  @UC-FIN-03 @RF-FIN-11
  Escenario: Detalle de una línea
    Cuando abro el detalle de "Costo de ventas" de noviembre de 2026
    Entonces veo las ventas "V-000101" y "V-000102" con su costo y la anulación "V-000090" restando 40.00

  @UC-FIN-04 @RF-FIN-14
  Escenario: El dashboard respeta los permisos
    Dado que soy usuario "ventas"
    Cuando abro el dashboard
    Entonces veo ventas de hoy, pedidos atrasados y stock bajo
    Pero no veo la utilidad bruta ni el margen

  @UC-FIN-05 @RF-FIN-15
  Escenario: Exportación CSV compatible con Excel
    Cuando exporto el estado de resultados de noviembre de 2026
    Entonces descargo un CSV en UTF-8 con BOM con las mismas líneas e importes de la pantalla

  @UC-FIN-03 @RN-FIN-07 @borde @RF-FIN-10
  Escenario: Entrega gratuita va a gastos de venta, no a ventas ni a costo de ventas
    Dado la categoría de ISC "Cerveza" con tarifa de S/ 2.51 por litro vigente
    Y una entrega gratuita el "2026-11-15" de 5 barriles de 20 L de "TER-IPA-BARRIL" con valor referencial 100.00 y costo 60.00 por barril
    Cuando consulto el estado de resultados de noviembre de 2026
    Entonces la entrega no suma en "Ventas netas" ni en "Costo de ventas"
    Y "Gastos de venta: entregas gratuitas" es 686.18, compuesto por:
      | concepto          | importe |
      | Costo del producto | 300.00 |
      | ISC asumido       | 251.00  |
      | IGV asumido       | 135.18  |

  @UC-FIN-03 @borde @RF-FIN-12
  Escenario: Pendientes tributarios listados aparte
    Dado en noviembre la venta anulada "V-000110" cuya nota de crédito está "ESPERANDO_ORIGINAL"
    Y la venta "V-000111" con comprobante "RECHAZADO" sin reemitir
    Cuando consulto el estado de resultados de noviembre
    Entonces veo aparte "Pendientes tributarios" con "V-000110" y "V-000111"

  @UC-FIN-05 @borde @RF-FIN-16 @RF-TEN-51
  Escenario: Exportación sin permiso de costos
    Dado el usuario "ana@andina.pe" con `reportes.exportar` y `finanzas.resultados.ver`, sin `inventario.costo.ver`
    Cuando exporta el stock valorizado y el estado de resultados
    Entonces el CSV de stock no tiene costo promedio ni valor
    Y el CSV del estado de resultados sí tiene el costo de ventas y los márgenes
