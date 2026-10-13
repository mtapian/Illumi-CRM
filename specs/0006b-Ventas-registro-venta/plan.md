# Plan 0006b — Ventas: facturación, entrega y cobranza

Estado: aprobado (PO: "ok", 2026-10-13), para la spec aprobada el 2026-10-13 (PO: "ok")

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.2.0)

Se extiende el contexto `sales` de 0006a. Usa la fachada del catálogo (`producto`, `desglose_de_linea`), el `InventarioService` (`bloquear`, `existencias_en_orden`, `registrar_salida`, `consumido`) y la fachada de tenancy (`parametro_vigente("umbral_boleta_identificada", fecha)`). Nadie nuevo depende de `sales`; 0007a leerá los pedidos facturados.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/sales/domain/cobranza.py` | `estado(total, pagado)`, `validar_pago(estado, monto, saldo)`, `vencida(estado, vencimiento, hoy)` | 53 a 57 |
| `src/sales/domain/facturacion.py` | `comprobante_para`, `validar_boleta`, `cronograma`, `validar_pagos_directa`, `validar_valor` | 19, 24, 25, 27, 28, 52 |
| `src/sales/application/facturacion.py` | `DatosFactura`, `FacturarPedido`, `EntregarPedido`, `VentaDirecta` | 17 a 29, 38, 51, 52 |
| `src/sales/application/cobranzas.py` | `RegistrarPago`, `AnularPago`, `GuardarMetodoPago`, `CambiarEstadoMetodoPago` | 54 a 59 |
| `src/sales/infrastructure/models.py` | Campos de facturación en `Pedido` y `PedidoLinea`; `Cobranza`, `Cuota`, `Pago`, `MetodoPago` | — |
| `src/sales/infrastructure/migrations/0002_facturacion_cobranza.py` | Tablas, CHECK, trigger de líneas ajustado, métodos de pago de las empresas existentes, permisos de cobranza a los roles existentes con `ventas.venta.registrar` | 58 |
| `src/sales/infrastructure/repositorios.py` | `PedidosOrm` (facturar, entregar), `CobranzasOrm`, `MetodosPagoOrm` | — |
| `src/sales/infrastructure/contenedor.py` | `caso_de_factura`, `caso_de_cobranza`, sembrador de métodos de pago | 58 |
| `src/shared/domain/accesos.py`, `src/tenancy/domain/plantillas.py` | Permisos `ventas.cobranza.ver` y `ventas.cobranza.gestionar` en "Ventas"; plantillas Ventas y Gerente | 53, 54 |
| `src/sales/interfaces/views.py`, `urls.py`, plantillas | Facturar y entregar en la ficha del pedido; venta directa; cobranzas; métodos de pago; ficha del cliente | 04, 17 a 59 |

## 2. Modelo de datos

- **`Pedido`** (+): `comprobante` (`FACTURA`/`BOLETA`, vacío antes de facturar; sale del cliente), `almacen` (FK, nulo), `forma_pago` (`CONTADO`/`CREDITO`, vacío), `fecha_emision` (nula), `costo_total` (2), `facturado_por/en`, `entregado_por/en`, `token` (UUID nulo; único por empresa: RF-VEN-29). CHECK: Facturado o Entregado ⇔ comprobante, forma de pago y fecha de emisión; Entregado ⇒ `entregado_en`.
- **`PedidoLinea`** (+): `valor`, `isc`, `igv`, `costo` (2 decimales, nulos hasta facturar). CHECK: los cuatro nulos o los cuatro presentes, y `valor + isc + igv = subtotal`.
- **Trigger de líneas** (0006a): además de Creado, deja actualizar **solo** `valor`, `isc`, `igv` y `costo` mientras el pedido está Aprobado (facturar actualiza las líneas antes de cambiar el estado, en la misma transacción).
- **`MetodoPago`** (empresa): `nombre`, `activo`. Único `(empresa, lower(nombre))`. Sin borrado (PROTECT desde `Pago`).
- **`Cobranza`** (empresa): `numero` (correlativo por empresa con `fn_siguiente_correlativo`, secuencia `COBRANZA`; se muestra `COB-000001`; único), `pedido` (OneToOne), `cliente`, `emision`, `total`, `pagado`, `estado` (`PENDIENTE`/`PARCIAL`/`PAGADA`). CHECK: `0 ≤ pagado ≤ total`; `PENDIENTE ⇔ pagado = 0`, `PARCIAL ⇔ 0 < pagado < total`, `PAGADA ⇔ pagado = total`.
- **`Cuota`** (empresa): `cobranza`, `numero`, `monto > 0`, `vencimiento` (se guarda la fecha; los días son solo la forma de ingresarla). Al contado, una cuota por el total con vencimiento en la emisión; a crédito, el cronograma de la factura (0007a lo envía a SUNAT). Inmutables (trigger). Σ cuotas = total se valida en el dominio y con un test.
- **`Pago`** (empresa): `cobranza`, `metodo`, `monto > 0`, `fecha`, `referencia`, `registrado_por/en`, `anulado_por/en`, `motivo_anulacion`. CHECK: anulado ⇔ fecha y motivo. Sin borrado.
- Las salidas de stock son movimientos `SALIDA` con motivo `VENTA` y referencia `("VENTA", pedido_id)`; los lotes y el costo por lote se leen del kardex (`consumido`), no se copian.

Decisión: el **comprobante pendiente son los datos del pedido facturado** (tipo, fecha de emisión, cliente, líneas con su desglose). 0007a crea su propio comprobante con serie y correlativo a partir de ellos. Alternativa descartada: una tabla de comprobante en `sales`, que duplicaría la de 0007a.

## 3. Funciones puras

- `comprobante_para(tipo_doc)` → `FACTURA` si es RUC, `BOLETA` en otro caso (RF-VEN-19, 24); `validar_boleta(es_generico, total, umbral)` (RF-VEN-25).
- `cronograma(forma, comprobante, cuotas, total, emision)` → cuotas efectivas (contado: una por el total en la emisión; crédito: exige factura, al menos una cuota, montos > 0, vencimientos posteriores a la emisión y Σ = total) (RF-VEN-19, 27).
- `monto_vencido(cuotas, pagado, hoy)` y `proximo_vencimiento(cuotas, pagado)` (RF-VEN-53).
- `validar_valor(sku, desglose)` → error si `valor ≤ 0` (RF-VEN-28).
- `validar_pagos_directa(montos, total)` (RF-VEN-52).
- `estado(total, pagado)`, `validar_pago(estado, monto, saldo)` (RF-VEN-55, 57), `vencida(estado, vencimiento, hoy)` (RF-VEN-53).

## 4. Algoritmos clave

```
FacturarPedido(actor, pedido_id, datos, hoy):
  atomic:
    estado, pedido = repo.bloquear(pedido_id)              # FOR UPDATE
    transicion(estado, "facturar")
    validar cliente activo y productos vendibles            # RF-VEN-23 (doble validación)
    comprobante = comprobante_para(cliente.tipo_doc); si BOLETA: validar_boleta(…, tenancy.parametro_vigente(umbral, hoy))
    cuotas = cronograma(datos.forma, datos.comprobante, datos.cuotas, total, hoy)
    desgloses = {linea: catalogo.desglose_de_linea(p, subtotal, cantidad, hoy)}; validar_valor
    bienes = líneas que no son servicio
    inventario.bloquear(ids de bienes)                      # antes de mirar el stock (RF-VEN-26)
    disponible por línea = Σ existencias_en_orden(p, almacen, hoy) [del lote elegido, si hay]
    faltantes(requeridos, disponibles) → error con todos     # shared/domain/stock.py
    por línea: ids = registrar_salida("VENTA", "VENTA", pedido_id, [Linea(p, almacen, q, lote)], …, hoy)
               costo = Σ consumido(ids).importe
    repo.facturar(pedido_id, líneas con desglose y costo, comprobante, almacén, forma, hoy, actor)
    repo.crear_cobranza(pedido_id, total, hoy, cuotas)

VentaDirecta(actor, datos, pagos, token, hoy):
  validar_pagos_directa
  atomic:
    si existe pedido con token → devolver su id             # RF-VEN-29
    id = crear (como CrearPedido, con token) → aprobar (sin exigir stock aparte: lo valida facturar)
    FacturarPedido (contado) → registrar cada pago → entregar
```

`RegistrarPago` bloquea la cobranza (`FOR UPDATE`), valida con `validar_pago` y suma a `pagado`; `AnularPago` bloquea la cobranza y el pago, resta y recalcula el estado. Dos pagos simultáneos se serializan con el bloqueo.

## 5. Interfaz

- **Ficha del pedido** (`/ventas/pedidos/<id>/`): Aprobado → acción principal **Facturar** (diálogo: comprobante que resulta del cliente, solo lectura; almacén, forma de pago solo si el cliente tiene RUC (si no, Contado fijo, sin selector), cronograma de cuotas si es crédito: filas de monto y días (vencimiento = emisión + días, calculado al vuelo y en el servidor; una cuota por el total a 30 días por defecto), lote opcional por línea con los lotes disponibles y su vencimiento; la confirmación explica que sale el stock y se crea la cobranza). Facturado → **Confirmar entrega**. Facturado o Entregado: desglose por línea, totales, comprobante pendiente, enlace a la cobranza y, con `inventario.costo.ver`, el costo.
- **Venta directa** (`/ventas/venta-directa/`): cliente con la búsqueda de 0006a ("Clientes varios" por defecto), líneas dinámicas, comprobante, almacén y pagos dinámicos (método, monto) con el total y lo que falta; token oculto.
- **Cobranzas** (`/ventas/cobranzas/` y `/ventas/cobranzas/<id>/`): grilla estándar con filtros, monto vencido e indicador Vencida; ficha con cuotas, pagos, "Registrar pago" y, en "Más acciones" de cada pago, "Anular pago" con motivo.
- **Métodos de pago** (`/ventas/metodos-pago/`): listado de maestro (nombre, pagos, estado; sin eliminar).
- **Ficha del cliente:** comprado en 90 días, última compra y saldo por cobrar.
- Menú "Ventas": Venta directa, Cobranzas, Métodos de pago. Rutas con id en la prueba de aislamiento.

### Enmienda 1 (revisión de ventas)

- **C1 (RF-VEN-61, 64):** permisos `ventas.cobranza.anular` y `ventas.metodo_pago.gestionar` en la funcionalidad "Ventas"; `AnularPago` y los casos de uso de métodos de pago pasan a ellos; plantilla Gerente; migración que los da a los roles con `ventas.venta.anular`; botones y menú solo con el permiso.
- **U2 (RF-VEN-62):** `avisos.agregar("cobranzas_vencidas", …, permiso=ventas.cobranza.ver)` con la misma consulta del filtro "solo vencidas" (cuotas vencidas − pagado > 0, en la base); `_aviso_vencidas.html` enlaza a `/ventas/cobranzas/?vencidas=1`.
- **U3 (RF-VEN-63):** `disponibilidad()` suma a los indicadores de un pedido Facturado o Entregado con saldo su estado de cobro (sin marca si está pagado), con una sola consulta de cobranzas (y sus cuotas) para la página.
- Correcciones de la revisión (sin RF nuevo): la búsqueda de clientes exige `ventas.cliente.ver` (no `ventas.pedido.gestionar`); un pago no puede ser anterior a la emisión (RF-VEN-54); el kardex enlaza la salida `VENTA` con su pedido.

### Enmienda 2 (RF-VEN-65)

Buscador en el parcial de líneas que comparten el pedido y la venta directa (`_cliente_y_lineas.html` y `_buscar_producto.html`): filtra en el navegador sobre los productos vendibles que la pantalla ya carga (cada opción lleva `data-sku`, `data-barras` y `data-precio`); Enter con coincidencia exacta agrega o suma 1. Alternativa descartada por ahora: búsqueda en el servidor (más lenta para la lectora y un endpoint más). Mejora técnica registrada en `MEMORY.md` (PO, 2026-10-13): pasar al servidor con más de ~500 SKUs vendibles.

## 6. Decisiones técnicas

- **Sin tabla de venta ni de comprobante** (§2): la venta es el pedido facturado.
- **`pagado` desnormalizado en la cobranza** con CHECK, bajo bloqueo; alternativa descartada: sumar los pagos en cada lectura (el listado filtra por saldo y estado).
- **Permisos de cobranza dentro de la funcionalidad "Ventas"** (sin funcionalidad nueva): no cambia los planes; la migración se los da a los roles que ya registran ventas.
- **Venta directa reutiliza `FacturarPedido`**: una sola implementación de la doble validación y la salida de stock.
- **Idempotencia por token** único en la base (RF-VEN-29), además del envío único del navegador (`docs/ux.md`).

## 7. Estrategia de tests (pytest)

- **Dominio** (`tests/sales/unit/`): reglas del comprobante con el umbral, cronograma de crédito (factura, cuotas, suma, vencimientos), monto vencido y próximo vencimiento, valor ≤ 0, pagos de la venta directa, estados y validación de pagos, vencida.
- **Casos de uso** (`tests/sales/usecases/`): facturar (desglose, costo congelado, lote elegido, FEFO, servicios, todos los faltantes, producto desactivado, nada cambia si falla), entregar, venta directa (token repetido), pagos (parcial, total, sobre el saldo, cobranza pagada, anular), métodos de pago, permisos.
- **Integración**: CHECK y trigger, concurrencia de dos facturaciones por el último stock y de dos pagos por el último saldo (dos hilos), sembrador y migración de métodos de pago, pantallas.
- **Aceptación**: `tests/acceptance/test_e06b.py` con los 16 escenarios.

## 8. Cobertura de RF

| RF | Dónde |
|---|---|
| 17, 19 a 28, 38 | `FacturarPedido` + dominio; escenarios de facturar |
| 51 | `EntregarPedido`; escenario de entrega |
| 18, 29, 52 | `VentaDirecta`; escenarios de venta directa y test de token |
| 53 a 57 | `cobranzas.py` + dominio; escenarios de cobranza |
| 58, 59 | sembrador, migración, `GuardarMetodoPago`; escenario de métodos |
| 04 | ficha del cliente; test de pantalla |

## 9. Dependencias

0006a (pedidos, clientes, búsqueda), 0002e (`desglose_de_linea`), 0003a (`InventarioService`), 0001b/c (catálogo de accesos y plantillas), parámetro `umbral_boleta_identificada` de la plataforma (0001a).
