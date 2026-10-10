# Plan 0006b — Ventas: registro de la venta

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/sales`. Usa `CatalogoQuery` (productos e ISC), `InventarioService` (salidas y reversiones), `TenancyService` (IGV y umbral vigentes), `ProduccionService` (desvincular pedidos) y `FacturacionService` (comprobantes por outbox). Requiere: 0006a, 0002c, 0003a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/sales/domain/venta.py` | Agregado `Venta`: reglas de comprobante, crédito y cuotas, líneas comerciales, gratuitas | RF-VEN-17 a 31, 38 |
| `src/sales/domain/tributos.py` | `CalculadoraTributos`: desglose por línea comercial con y sin ISC; gratuitas | RF-VEN-22, 28, 30 |
| `src/sales/domain/errores.py` | `ComprobanteRequiereRuc`, `BoletaRequiereIdentificacion`, `CuotasInvalidas`, `CreditoRequiereFactura`, `PrecioMenorQueIsc`, `TransicionInvalida`, `ComprobanteNoAceptado`… | todos los `SI … ENTONCES` |
| `src/sales/application/ventas.py` | `RegistrarVenta`, `AnularVenta`, `CorregirClienteVenta` | RF-VEN-17 a 31, 38 |
| `src/sales/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/sales/interfaces/views/*.py` + `templates/sales/*.html` | Pantallas de §5 | RF-VEN-17 a 31, 38 |
| `src/sales/interfaces/impresion.py` | Representación A4 y ticket de 80 mm (con los datos del comprobante de la épica 0007) | RF-VEN-31 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `sales_venta` | empresa_id, numero, pedido_id null, cliente_id, tipo_comprobante, almacen_id, fecha_emision `DATE`, forma_pago, metodo_pago null, monto_recibido null, vuelto, igv_pct (vigente), valor_venta, igv, isc, total, costo_total, estado (`EMITIDA`/`ANULADA`), idempotency_key, motivo_nc (`01`/`06`) null, reingresa_mercaderia null, anulado_por, anulado_en | UNIQUE(empresa_id, numero); UNIQUE(empresa_id, idempotency_key) | RF-VEN-17 a 21, 29, 38 |
| `sales_venta_linea` | venta_id, producto_id, cantidad, precio_unitario, valor_unitario `NUMERIC(20,10)`, valor_venta, igv, isc, costo_total, es_gratuita, motivo_gratuito, valor_referencial, tributos_asumidos | Una fila por línea comercial | RF-VEN-21, 22, 28, 30 |
| `sales_venta_linea_lote` | venta_linea_id, lote_id null, cantidad, costo_unitario, costo_total, movimiento_id | Reparto FEFO (solo stock y costo) | RF-VEN-20, 21 |
| `sales_venta_cuota` | venta_id, numero, monto, fecha_vencimiento | UNIQUE(venta_id, numero) | RF-VEN-27 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `desglose(total_linea, igv_pct, isc_dto) -> (valor, isc, igv)` | Sin ISC: `valor = round(total / (1 + igv), 2)`. Con ISC: `isc = round(cant × L × tarifa, 2)`, `valor = round(total / (1 + igv) − isc, 2)`, `igv = total − valor − isc` | RF-VEN-22 |
| `desglose_gratuito(valor_referencial, isc_dto, igv_pct) -> (isc, igv, tributos_asumidos)` | ISC por litros e IGV sobre `valor_referencial + isc` | RF-VEN-30 |
| `validar_valor_linea(valor, es_gratuita)` | `PrecioMenorQueIsc` si `valor ≤ 0` en una línea pagada | RF-VEN-28 |
| `validar_comprobante(tipo, cliente, total, umbral)` | Factura con RUC; boleta > umbral con cliente identificado | RF-VEN-24, 25 |
| `validar_credito(tipo, cuotas, total, fecha_emision)` | Solo factura; ≥ 1 cuota; Σ = total; vencimientos > emisión | RF-VEN-27 |
| `vuelto(total, recibido) -> Money` | Solo contado en efectivo | RF-VEN-19 |
| `comprobante_para(cliente) -> tipo` | Factura si tiene RUC, boleta en otro caso (entregas gratuitas) | RF-VEN-30 |

## 4. Algoritmos clave

**Registrar venta** (RF-VEN-17 a 31, 38):

```
RegistrarVenta(cmd):
  actor.exige(ventas.venta.registrar)
  si existe venta con cmd.idempotency_key → devolverla                                 # RF-VEN-29
  fecha = hoy (Lima)                                                                     # RF-VEN-38
  si viene de pedido: pedido = select_for_update; transicion_pedido(pedido, ENTREGAR)     # RF-VEN-17
  por línea: producto vendible y activo (RF-VEN-23)
             isc = CatalogoQuery.isc_aplicable(producto, fecha)
             si gratuita: desglose_gratuito(…)  si no: desglose(total, igv_vigente(fecha), isc); validar_valor_linea
  validar_comprobante(…, umbral=parametro_vigente('umbral_boleta', fecha))              # RF-VEN-24, 25
  si CREDITO: validar_credito(…)                                                         # RF-VEN-27
  numero = SequencePort.siguiente('VENTA', 'V')
  movs = InventarioService.registrar_salida(VENTA, almacén, fefo o lote)                 # RF-VEN-20, 26
  copiar costos a venta_linea_lote (costo congelado)                                     # RF-VEN-21
  pedido → ENTREGADO                                                                     # RF-VEN-14
  FacturacionService.registrar_emision(ComprobanteDTO)        # outbox, misma transacción
  on_commit: FacturacionService.intentar_envio(id)
```

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/ventas/nueva` | Pantalla tipo POS: búsqueda de presentaciones y mercadería, lote opcional, totales en vivo; método de pago y vuelto solo al contado; cuotas solo con factura a crédito; casilla "gratuita" por línea con motivo y valor referencial | RF-VEN-17 a 30, 38 |
| `/ventas/<id>` | Detalle, estado del comprobante, imprimir A4 o ticket; botones "Anular" (motivo 01/06 y "¿vuelve la mercadería?") y "Corregir cliente" | RF-VEN-31 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Impuestos por línea comercial y reparto por lote en otra tabla | Una línea por lote | El reparto FEFO no puede cambiar el total ni duplicar líneas en el XML |
| Comprobante por outbox dentro de la transacción de la venta | Emitir en `on_commit` | Ninguna venta queda sin comprobante si el proceso se cae (art. 5.2) |
| La fecha de emisión es la de registro | Permitir fecha pasada | Los comprobantes y los períodos no se manipulan |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/sales tests/acceptance -k "E06b"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/sales/unit/test_tributos.py` | 288,00 → 244,07 / 43,93; con ISC 19,88 / 224,19 / 43,93; FEFO en 2 lotes no cambia el total; gratuita 251,00 / 135,18; valor ≤ 0 | RF-VEN-22, 28, 30 |
| Unitario | `tests/sales/unit/test_venta.py` | Factura con RUC, umbral de boleta vigente, crédito solo con factura, cuotas, vuelto | RF-VEN-19, 24, 25, 27 |
| Caso de uso | `tests/sales/usecases/test_registrar.py` | Desde pedido y directa, mixta (presentación + mercadería), FEFO, costo congelado, fecha = hoy, idempotencia | RF-VEN-17, 18, 20, 21, 23, 29, 38 |
| Integración | `tests/sales/integration/test_concurrencia.py` | Dos ventas por el último stock; doble anulación | RF-VEN-26, 36 |
| Integración | `tests/sales/integration/test_impresion.py` | A4 y ticket de 80 mm | RF-VEN-31 |
| Aceptación | `features/ventas.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-VEN-17, RF-VEN-18, RF-VEN-19, RF-VEN-20, RF-VEN-21, RF-VEN-22, RF-VEN-23, RF-VEN-24, RF-VEN-25, RF-VEN-26, RF-VEN-27, RF-VEN-28, RF-VEN-29, RF-VEN-30, RF-VEN-31, RF-VEN-38 | §1 `venta.py`, `tributos.py`, `ventas.py`, `impresion.py` · §3 `desglose`, `desglose_gratuito`, `validar_*`, `vuelto`, `comprobante_para` · §4 registrar venta · §5 `/ventas/nueva` · §7 |

## 9. Dependencias de dudas abiertas

- **Q3 (taproom B2C):** si no hay venta al público, el ticket de 80 mm y los métodos YAPE/PLIN salen del MVP (§5).

- **Umbral de S/ 700:** es un parámetro con vigencia (épica 0001); no cambia el código.
