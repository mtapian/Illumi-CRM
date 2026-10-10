# Plan 006 — Ventas y pedidos

Estado: borrador

Spec: `./spec.md` · Base técnica: `../000-arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/sales`. Usa `CatalogoQuery` (productos e ISC), `InventarioService` (salidas y reversiones), `TenancyService` (IGV y umbral vigentes), `ProduccionService` (desvincular pedidos) y `FacturacionService` (comprobantes por outbox).

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/sales/domain/cliente.py` | Validación de documentos (DNI, RUC, CE, sin documento) | RF-VEN-01 a 03 |
| `src/sales/domain/pedido.py` | Agregado `Pedido`: líneas, congelamiento, tabla de transiciones | RF-VEN-06 a 16, 35, 37, 41, 42 |
| `src/sales/domain/venta.py` | Agregado `Venta`: reglas de comprobante, crédito y cuotas, líneas comerciales, gratuitas | RF-VEN-17 a 31, 38 |
| `src/sales/domain/tributos.py` | `CalculadoraTributos`: desglose por línea comercial con y sin ISC; gratuitas | RF-VEN-22, 28, 30 |
| `src/sales/domain/errores.py` | `ComprobanteRequiereRuc`, `BoletaRequiereIdentificacion`, `CuotasInvalidas`, `CreditoRequiereFactura`, `PrecioMenorQueIsc`, `TransicionInvalida`, `ComprobanteNoAceptado`… | todos los `SI … ENTONCES` |
| `src/sales/application/clientes.py` | CRUD de clientes, ficha, cliente genérico | RF-VEN-01 a 05 |
| `src/sales/application/pedidos.py` | `CrearPedido`, `EditarPedido`, `ConfirmarPedido`, `MarcarListo`, `CancelarPedido`, tablero | RF-VEN-06 a 16, 37 |
| `src/sales/application/pedidos_port.py` | Implementación de `PedidosPort` para la spec 005 | RF-VEN-12, 13, 41, 42 |
| `src/sales/application/ventas.py` | `RegistrarVenta`, `AnularVenta`, `CorregirClienteVenta` | RF-VEN-17 a 36, 38 a 40 |
| `src/sales/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/sales/interfaces/views/*.py` + `templates/sales/*.html` | Pantallas de §5 | RF-VEN-01 a 42 |
| `src/sales/interfaces/impresion.py` | Representación A4 y ticket de 80 mm (con los datos del comprobante de la spec 007) | RF-VEN-31 |
| `src/sales/interfaces/api.py` | `GET /api/v1/pedidos`, `GET /api/v1/ventas` | (spec 001, RF-TEN-48) |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `sales_cliente` | empresa_id, tipo_doc, num_doc, razon_social, contacto, telefono, email, direccion, canal, notas, es_generico, activo | Documento único por empresa (salvo `SIN_DOC`); un genérico por empresa | RF-VEN-01 a 05 |
| `sales_pedido` | empresa_id, numero, cliente_id, fecha_entrega, estado, total, notas, confirmado_en, cancelado_en, motivo_cancelacion | UNIQUE(empresa_id, numero) | RF-VEN-06 a 16 |
| `sales_pedido_linea` | pedido_id, producto_id (vendible), cantidad, precio_unitario (con impuestos), total | `CHECK cantidad > 0` | RF-VEN-06, 08 |
| `sales_venta` | empresa_id, numero, pedido_id null, cliente_id, tipo_comprobante, almacen_id, fecha_emision `DATE`, forma_pago, metodo_pago null, monto_recibido null, vuelto, igv_pct (vigente), valor_venta, igv, isc, total, costo_total, estado (`EMITIDA`/`ANULADA`), idempotency_key, motivo_nc (`01`/`06`) null, reingresa_mercaderia null, anulado_por, anulado_en | UNIQUE(empresa_id, numero); UNIQUE(empresa_id, idempotency_key) | RF-VEN-17 a 21, 29, 32 a 36, 38 |
| `sales_venta_linea` | venta_id, producto_id, cantidad, precio_unitario, valor_unitario `NUMERIC(20,10)`, valor_venta, igv, isc, costo_total, es_gratuita, motivo_gratuito, valor_referencial, tributos_asumidos | Una fila por línea comercial | RF-VEN-21, 22, 28, 30 |
| `sales_venta_linea_lote` | venta_linea_id, lote_id null, cantidad, costo_unitario, costo_total, movimiento_id | Reparto FEFO (solo stock y costo) | RF-VEN-20, 21 |
| `sales_venta_cuota` | venta_id, numero, monto, fecha_vencimiento | UNIQUE(venta_id, numero) | RF-VEN-27 |
| `sales_venta_correccion` | venta_id, cliente_anterior_id, cliente_nuevo_id, comprobante_original_id, nc_id, comprobante_nuevo_id, created_by | Historial de correcciones de cliente | RF-VEN-39 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `validar_documento(tipo, numero)` | DNI 8 dígitos, RUC módulo 11, CE ≤ 12 alfanuméricos | RF-VEN-01, 02 |
| `faltantes(lineas, stock_por_producto) -> list` | Por línea: disponible sin vencer (todos los almacenes) y faltante; marca `MERCADERIA` como "por comprar" | RF-VEN-08 a 10 |
| `transicion_pedido(estado, evento) -> estado` | Tabla de transiciones de la spec; `TransicionInvalida` fuera de ella | RF-VEN-11 a 16, 35, 37, 41 |
| `atrasado(fecha_entrega, estado, hoy) -> bool` | Fecha vencida y estado ∉ {`ENTREGADO`, `CANCELADO`} | RF-VEN-15 |
| `estado_tras_anular_venta(reingresa) -> estado` | `LISTO` con reingreso; `CONFIRMADO` sin él | RF-VEN-35 |
| `revertir_a_confirmado(pedido, ops_en_proceso, stock_cubre) -> bool` | Regla de RF-VEN-41 | RF-VEN-41 |
| `desglose(total_linea, igv_pct, isc_dto) -> (valor, isc, igv)` | Sin ISC: `valor = round(total / (1 + igv), 2)`. Con ISC: `isc = round(cant × L × tarifa, 2)`, `valor = round(total / (1 + igv) − isc, 2)`, `igv = total − valor − isc` | RF-VEN-22 |
| `desglose_gratuito(valor_referencial, isc_dto, igv_pct) -> (isc, igv, tributos_asumidos)` | ISC por litros e IGV sobre `valor_referencial + isc` | RF-VEN-30 |
| `validar_valor_linea(valor, es_gratuita)` | `PrecioMenorQueIsc` si `valor ≤ 0` en una línea pagada | RF-VEN-28 |
| `validar_comprobante(tipo, cliente, total, umbral)` | Factura con RUC; boleta > umbral con cliente identificado | RF-VEN-24, 25 |
| `validar_credito(tipo, cuotas, total, fecha_emision)` | Solo factura; ≥ 1 cuota; Σ = total; vencimientos > emisión | RF-VEN-27 |
| `vuelto(total, recibido) -> Money` | Solo contado en efectivo | RF-VEN-19 |
| `comprobante_para(cliente) -> tipo` | Factura si tiene RUC, boleta en otro caso (entregas gratuitas) | RF-VEN-30 |
| `total_ultimos_90_dias(ventas, hoy) -> Money` | Para la ficha del cliente | RF-VEN-04 |

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

**Anular venta** (RF-VEN-32 a 36):
```
AnularVenta(id, motivo ∈ {01, 06}, reingresa=True):
  venta = select_for_update(id); si venta.estado ≠ EMITIDA → EstadoInvalido               # RF-VEN-36
  si reingresa: InventarioService.revertir('VENTA', id)       # mismos lotes y costo        # RF-VEN-33
  venta.estado = ANULADA                                       # el costo se mantiene sin reingreso: RF-VEN-34
  si venta.pedido: pedido.estado = estado_tras_anular_venta(reingresa)                     # RF-VEN-35
  FacturacionService.registrar_anulacion(comprobante, motivo)   # NC; espera si el original no fue aceptado
```

**Corregir el cliente** (RF-VEN-39, 40):
```
CorregirClienteVenta(id, cliente_nuevo):
  venta = select_for_update(id); validar_comprobante(venta.tipo, cliente_nuevo, …)
  si comprobante original no ACEPTADO/OBSERVADO → ComprobanteNoAceptado                    # RF-VEN-40
  FacturacionService.registrar_correccion(original, ComprobanteDTO(cliente_nuevo, mismas líneas))
  venta.cliente = cliente_nuevo; guardar sales_venta_correccion     # sin stock, sin cambio de costo
```

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/clientes/` | CRUD con validación del documento en vivo; ficha con pedidos, ventas, total de 90 días y última compra | RF-VEN-01 a 05 |
| `/pedidos/` | Tablero por estado (columnas) con fecha de entrega y marca de atraso | RF-VEN-15 |
| `/pedidos/nuevo`, `/pedidos/<id>` | Líneas con precio de lista precargado; al confirmar, tabla de disponible y faltante; botón "Planificar producción" solo con faltante de presentaciones; "por comprar" para mercadería; marcar listo; cancelar con motivo | RF-VEN-06 a 14, 16, 37 |
| `/ventas/nueva` | Pantalla tipo POS: búsqueda de presentaciones y mercadería, lote opcional, totales en vivo; método de pago y vuelto solo al contado; cuotas solo con factura a crédito; casilla "gratuita" por línea con motivo y valor referencial | RF-VEN-17 a 30, 38 |
| `/ventas/<id>` | Detalle, estado del comprobante, imprimir A4 o ticket; botones "Anular" (motivo 01/06 y "¿vuelve la mercadería?") y "Corregir cliente" | RF-VEN-31 a 36, 39, 40 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Impuestos por línea comercial y reparto por lote en otra tabla | Una línea por lote | El reparto FEFO no puede cambiar el total ni duplicar líneas en el XML |
| Comprobante por outbox dentro de la transacción de la venta | Emitir en `on_commit` | Ninguna venta queda sin comprobante si el proceso se cae (art. 5.2) |
| Corrección de cliente como caso de uso propio (NC `02` + comprobante nuevo) | Anular y registrar otra venta | Evita la doble salida de stock por una sola entrega |
| La fecha de emisión es la de registro | Permitir fecha pasada | Los comprobantes y los períodos no se manipulan |
| Sin reserva de stock | Reservar al confirmar el pedido | Simplicidad (art. 7.6); la venta valida el stock |
| Tabla de transiciones explícita del pedido | Diagrama con transiciones implícitas | Hace verificable RF-VEN-16 |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/sales tests/acceptance -k "E06"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/sales/unit/test_cliente.py` | Documentos válidos e inválidos | RF-VEN-01, 02 |
| Unitario | `tests/sales/unit/test_pedido.py` | Tabla de transiciones completa (parametrizada), atraso con `hoy`, faltantes | RF-VEN-08 a 16, 35, 37, 41 |
| Unitario | `tests/sales/unit/test_tributos.py` | 288,00 → 244,07 / 43,93; con ISC 19,88 / 224,19 / 43,93; FEFO en 2 lotes no cambia el total; gratuita 251,00 / 135,18; valor ≤ 0 | RF-VEN-22, 28, 30 |
| Unitario | `tests/sales/unit/test_venta.py` | Factura con RUC, umbral de boleta vigente, crédito solo con factura, cuotas, vuelto | RF-VEN-19, 24, 25, 27 |
| Caso de uso | `tests/sales/usecases/test_registrar.py` | Desde pedido y directa, mixta (presentación + mercadería), FEFO, costo congelado, fecha = hoy, idempotencia | RF-VEN-17, 18, 20, 21, 23, 29, 38 |
| Caso de uso | `tests/sales/usecases/test_anular.py` | Con y sin reingreso, estado del pedido, NC registrada | RF-VEN-32 a 35 |
| Caso de uso | `tests/sales/usecases/test_corregir_cliente.py` | NC `02` + comprobante nuevo, sin stock; original no aceptado ⇒ rechazo | RF-VEN-39, 40 |
| Caso de uso | `tests/sales/usecases/test_pedidos_port.py` | Varias OP por pedido; regreso a `CONFIRMADO`; `ENTREGADO`/`CANCELADO` no cambian | RF-VEN-12, 13, 41, 42 |
| Integración | `tests/sales/integration/test_concurrencia.py` | Dos ventas por el último stock; doble anulación | RF-VEN-26, 36 |
| Integración | `tests/sales/integration/test_clientes.py` | Cliente genérico, ficha, no eliminar con documentos | RF-VEN-03 a 05 |
| Integración | `tests/sales/integration/test_impresion.py` | A4 y ticket de 80 mm | RF-VEN-31 |
| Aceptación | `features/clientes_pedidos.feature`, `features/ventas.feature` | Escenarios de la spec | todos |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-VEN-01, RF-VEN-02, RF-VEN-03, RF-VEN-04, RF-VEN-05 | §1 `cliente.py`, `clientes.py` · §3 `validar_documento`, `total_ultimos_90_dias` · §5 `/clientes/` · §7 |
| RF-VEN-06, RF-VEN-07, RF-VEN-08, RF-VEN-09, RF-VEN-10, RF-VEN-11 | §1 `pedido.py`, `pedidos.py` · §3 `faltantes` · §5 pedidos · §7 `test_pedido.py` |
| RF-VEN-12, RF-VEN-13, RF-VEN-14, RF-VEN-15, RF-VEN-16 | §3 `transicion_pedido`, `atrasado` · §5 tablero · §7 |
| RF-VEN-17, RF-VEN-18, RF-VEN-19, RF-VEN-20, RF-VEN-21, RF-VEN-22, RF-VEN-23, RF-VEN-24, RF-VEN-25, RF-VEN-26, RF-VEN-27, RF-VEN-28, RF-VEN-29, RF-VEN-30, RF-VEN-31, RF-VEN-38 | §1 `venta.py`, `tributos.py`, `ventas.py`, `impresion.py` · §3 `desglose`, `desglose_gratuito`, `validar_*`, `vuelto`, `comprobante_para` · §4 registrar venta · §5 `/ventas/nueva` · §7 |
| RF-VEN-32, RF-VEN-33, RF-VEN-34, RF-VEN-35, RF-VEN-36 | §3 `estado_tras_anular_venta` · §4 anular venta · §5 `/ventas/<id>` · §7 `test_anular.py` |
| RF-VEN-37 | §1 `pedidos.py` · §3 `transicion_pedido` · §5 cancelar · §7 |
| RF-VEN-39, RF-VEN-40 | §2 `sales_venta_correccion` · §4 corregir cliente · §5 · §7 `test_corregir_cliente.py` |
| RF-VEN-41, RF-VEN-42 | §1 `pedidos_port.py` · §3 `revertir_a_confirmado` · §7 `test_pedidos_port.py` |

## 9. Dependencias de dudas abiertas

- **Q3 (taproom B2C):** si no hay venta al público, el ticket de 80 mm y los métodos YAPE/PLIN salen del MVP (§5).
- **Validación del contador (RF-VEN-32):** que la venta se anule sin esperar a SUNAT.
- **Umbral de S/ 700:** es un parámetro con vigencia (spec 001); no cambia el código.
