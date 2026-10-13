# language: es
@E08 @E08c @mvp @borrador
Característica: Dashboard, exportación e indicadores de los listados
  Como dueño o vendedor
  Quiero ver al entrar cómo van las ventas, llevar las grillas a Excel y ver los estados de un vistazo
  Para decidir sin planillas paralelas

  Antecedentes:
    Dado que soy usuario "gerente" de "Cervecería Andina"
    Y la fecha de hoy es "2026-12-10"
    Y "TER-IPA-330" de la categoría "Cervezas" se vende a 12.00 con "IGV 18%" y stock 1000
    Y el cliente "Bar El Lúpulo" con RUC "20512345671" y canal "B2B"
    Y las ventas facturadas:
      | pedido   | emisión    | cantidad | estado    |
      | P-000001 | 2026-11-20 | 10       | Entregado |
      | P-000002 | 2026-12-01 | 24       | Entregado |
      | P-000003 | 2026-12-10 | 5        | Facturado |
    Y los pagos de "P-000002": 200.00 por "Efectivo" y 88.00 por "Yape"

  @UC-FIN-04 @critico @RF-FIN-14 @RF-FIN-22 @RF-FIN-23
  Escenario: Tarjetas, más vendidos y últimas ventas
    Cuando abro el inicio
    Entonces veo las tarjetas:
      | tarjeta           | valor     |
      | Ventas de hoy     | S/ 60.00  |
      | Ventas del mes    | S/ 348.00 |
      | Productos activos | 1         |
      | Clientes activos  | 2         |
    Y en "Productos más vendidos" veo "TER-IPA-330" con 29 unidades y S/ 348.00
    Y en "Últimas ventas" el primero es "P-000003"

  @UC-FIN-04 @RF-FIN-18 @RF-FIN-19 @RF-FIN-20 @RF-FIN-21
  Escenario: Gráficos con sus valores
    Cuando abro el inicio
    Entonces el gráfico "Ventas de los últimos 14 días" tiene 14 puntos y el del "2026-12-01" vale 288.00
    Y el gráfico "Ventas por mes" tiene 12 meses, noviembre 120.00 y diciembre 348.00
    Y el gráfico "Cobrado por método de pago" muestra Efectivo 200.00 y Yape 88.00
    Y el gráfico "Ventas por categoría" muestra Cervezas 348.00

  @UC-FIN-04 @RF-FIN-14 @RF-FIN-17
  Escenario: Cada uno ve lo que su permiso habilita
    Dado que soy usuario "produccion" de la misma empresa
    Cuando abro el inicio
    Entonces no veo "Ventas de hoy" ni "Cobrado por método de pago"
    Y veo "Productos activos"

  @UC-FIN-04 @borde @RF-FIN-24
  Escenario: Sin ventas no hay errores
    Dado una empresa sin ventas
    Cuando abro el inicio
    Entonces veo "Aún no hay ventas" y las tarjetas de ventas en S/ 0.00

  @UC-FIN-05 @critico @RF-FIN-15
  Esquema del escenario: Exportar los pedidos, una fila por SKU
    Cuando exporto los pedidos filtrados por cliente "Bar El Lúpulo" en "<formato>"
    Entonces el archivo tiene 3 filas de datos con las columnas de la grilla y el SKU de cada línea

    Ejemplos:
      | formato |
      | XLSX    |
      | CSV     |

  @UC-FIN-05 @RF-FIN-16
  Escenario: Sin permiso de costos, la exportación no los lleva
    Dado que soy usuario "ventas" de la misma empresa
    Cuando exporto el kardex de "TER-IPA-330" en "XLSX"
    Entonces el archivo no tiene columnas de costo

  @UC-FIN-05 @borde @RF-FIN-25
  Escenario: Demasiadas filas
    Dado que la exportación tendría más de 50 000 filas
    Cuando exporto los productos en "XLSX"
    Entonces el resultado es "Hay más de 50 000 filas: agrega filtros para exportar"

  @UC-FIN-06 @RF-FIN-26
  Escenario: Indicadores por estado en pedidos y cobranzas
    Cuando abro el listado de pedidos
    Entonces veo las tarjetas Creados 0, Aprobados 0, Facturados 1 y Entregados 2
    Cuando abro el listado de cobranzas
    Entonces veo las tarjetas Pendientes 2, Parciales 0, Pagadas 1 y Vencidas 0
    Cuando pulso la tarjeta "Pagadas"
    Entonces el listado muestra solo las cobranzas pagadas
