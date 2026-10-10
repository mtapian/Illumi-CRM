# Plan 0006c — Ventas: anulación y corrección de cliente

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/sales`. Usa `CatalogoQuery` (productos e ISC), `InventarioService` (salidas y reversiones), `TenancyService` (IGV y umbral vigentes), `ProduccionService` (desvincular pedidos) y `FacturacionService` (comprobantes por outbox). Requiere: 0006b.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/sales/domain/pedido.py` | Agregado `Pedido`: líneas, congelamiento, tabla de transiciones | RF-VEN-35 |
| `src/sales/domain/errores.py` | `ComprobanteRequiereRuc`, `BoletaRequiereIdentificacion`, `CuotasInvalidas`, `CreditoRequiereFactura`, `PrecioMenorQueIsc`, `TransicionInvalida`, `ComprobanteNoAceptado`… | todos los `SI … ENTONCES` |
| `src/sales/application/ventas.py` | `RegistrarVenta`, `AnularVenta`, `CorregirClienteVenta` | RF-VEN-32 a 36, 39, 40 |
| `src/sales/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/sales/interfaces/views/*.py` + `templates/sales/*.html` | Pantallas de §5 | RF-VEN-32 a 36, 39, 40 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `sales_venta` | empresa_id, numero, pedido_id null, cliente_id, tipo_comprobante, almacen_id, fecha_emision `DATE`, forma_pago, metodo_pago null, monto_recibido null, vuelto, igv_pct (vigente), valor_venta, igv, isc, total, costo_total, estado (`EMITIDA`/`ANULADA`), idempotency_key, motivo_nc (`01`/`06`) null, reingresa_mercaderia null, anulado_por, anulado_en | UNIQUE(empresa_id, numero); UNIQUE(empresa_id, idempotency_key) | RF-VEN-32 a 36 |
| `sales_venta_correccion` | venta_id, cliente_anterior_id, cliente_nuevo_id, comprobante_original_id, nc_id, comprobante_nuevo_id, created_by | Historial de correcciones de cliente | RF-VEN-39 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `transicion_pedido(estado, evento) -> estado` | Tabla de transiciones de la spec; `TransicionInvalida` fuera de ella | RF-VEN-35 |
| `estado_tras_anular_venta(reingresa) -> estado` | `LISTO` con reingreso; `CONFIRMADO` sin él | RF-VEN-35 |

## 4. Algoritmos clave

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
| `/ventas/<id>` | Detalle, estado del comprobante, imprimir A4 o ticket; botones "Anular" (motivo 01/06 y "¿vuelve la mercadería?") y "Corregir cliente" | RF-VEN-32 a 36, 39, 40 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Corrección de cliente como caso de uso propio (NC `02` + comprobante nuevo) | Anular y registrar otra venta | Evita la doble salida de stock por una sola entrega |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/sales tests/acceptance -k "E06c"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/sales/unit/test_pedido.py` | Tabla de transiciones completa (parametrizada), atraso con `hoy`, faltantes | RF-VEN-08 a 16, 35, 37, 41 |
| Caso de uso | `tests/sales/usecases/test_anular.py` | Con y sin reingreso, estado del pedido, NC registrada | RF-VEN-32 a 35 |
| Caso de uso | `tests/sales/usecases/test_corregir_cliente.py` | NC `02` + comprobante nuevo, sin stock; original no aceptado ⇒ rechazo | RF-VEN-39, 40 |
| Integración | `tests/sales/integration/test_concurrencia.py` | Dos ventas por el último stock; doble anulación | RF-VEN-26, 36 |
| Aceptación | `features/ventas.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-VEN-32, RF-VEN-33, RF-VEN-34, RF-VEN-35, RF-VEN-36 | §3 `estado_tras_anular_venta` · §4 anular venta · §5 `/ventas/<id>` · §7 `test_anular.py` |
| RF-VEN-39, RF-VEN-40 | §2 `sales_venta_correccion` · §4 corregir cliente · §5 · §7 `test_corregir_cliente.py` |

## 9. Dependencias de dudas abiertas

- **Validación del contador (RF-VEN-32):** que la venta se anule sin esperar a SUNAT.
