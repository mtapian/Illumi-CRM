# Plan 0006a — Ventas: clientes y pedidos

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/sales`. Usa `CatalogoQuery` (productos e ISC), `InventarioService` (salidas y reversiones), `TenancyService` (IGV y umbral vigentes), `ProduccionService` (desvincular pedidos) y `FacturacionService` (comprobantes por outbox). Requiere: 0002a, 0003a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/sales/domain/cliente.py` | Validación de documentos (DNI, RUC, CE, sin documento) | RF-VEN-01 a 03 |
| `src/sales/domain/pedido.py` | Agregado `Pedido`: líneas, congelamiento, tabla de transiciones | RF-VEN-06 a 16, 37, 41, 42 |
| `src/sales/domain/errores.py` | `ComprobanteRequiereRuc`, `BoletaRequiereIdentificacion`, `CuotasInvalidas`, `CreditoRequiereFactura`, `PrecioMenorQueIsc`, `TransicionInvalida`, `ComprobanteNoAceptado`… | todos los `SI … ENTONCES` |
| `src/sales/application/clientes.py` | CRUD de clientes, ficha, cliente genérico | RF-VEN-01 a 05 |
| `src/sales/application/pedidos.py` | `CrearPedido`, `EditarPedido`, `ConfirmarPedido`, `MarcarListo`, `CancelarPedido`, tablero | RF-VEN-06 a 16, 37 |
| `src/sales/application/pedidos_port.py` | Implementación de `PedidosPort` para la épica 0005 | RF-VEN-12, 13, 41, 42 |
| `src/sales/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/sales/interfaces/views/*.py` + `templates/sales/*.html` | Pantallas de §5 | RF-VEN-01 a 16, 37, 41, 42 |
| `src/sales/interfaces/api.py` | `GET /api/v1/pedidos`, `GET /api/v1/ventas` | (épica 0001, RF-TEN-48) |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `sales_cliente` | empresa_id, tipo_doc, num_doc, razon_social, contacto, telefono, email, direccion, canal, notas, es_generico, activo | Documento único por empresa (salvo `SIN_DOC`); un genérico por empresa | RF-VEN-01 a 05 |
| `sales_pedido` | empresa_id, numero, cliente_id, fecha_entrega, estado, total, notas, confirmado_en, cancelado_en, motivo_cancelacion | UNIQUE(empresa_id, numero) | RF-VEN-06 a 16 |
| `sales_pedido_linea` | pedido_id, producto_id (vendible), cantidad, precio_unitario (con impuestos), total | `CHECK cantidad > 0` | RF-VEN-06, 08 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `validar_documento(tipo, numero)` | DNI 8 dígitos, RUC módulo 11, CE ≤ 12 alfanuméricos | RF-VEN-01, 02 |
| `faltantes(lineas, stock_por_producto) -> list` | Por línea: disponible sin vencer (todos los almacenes) y faltante; marca `MERCADERIA` como "por comprar" | RF-VEN-08 a 10 |
| `transicion_pedido(estado, evento) -> estado` | Tabla de transiciones de la spec; `TransicionInvalida` fuera de ella | RF-VEN-11 a 16, 37, 41 |
| `atrasado(fecha_entrega, estado, hoy) -> bool` | Fecha vencida y estado ∉ {`ENTREGADO`, `CANCELADO`} | RF-VEN-15 |
| `revertir_a_confirmado(pedido, ops_en_proceso, stock_cubre) -> bool` | Regla de RF-VEN-41 | RF-VEN-41 |
| `total_ultimos_90_dias(ventas, hoy) -> Money` | Para la ficha del cliente | RF-VEN-04 |

## 4. Algoritmos clave

Sin algoritmos no triviales: la lógica está en las funciones puras de §3.

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/clientes/` | CRUD con validación del documento en vivo; ficha con pedidos, ventas, total de 90 días y última compra | RF-VEN-01 a 05 |
| `/pedidos/` | Tablero por estado (columnas) con fecha de entrega y marca de atraso | RF-VEN-15 |
| `/pedidos/nuevo`, `/pedidos/<id>` | Líneas con precio de lista precargado; al confirmar, tabla de disponible y faltante; botón "Planificar producción" solo con faltante de presentaciones; "por comprar" para mercadería; marcar listo; cancelar con motivo | RF-VEN-06 a 14, 16, 37 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Sin reserva de stock | Reservar al confirmar el pedido | Simplicidad (art. 7.6); la venta valida el stock |
| Tabla de transiciones explícita del pedido | Diagrama con transiciones implícitas | Hace verificable RF-VEN-16 |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/sales tests/acceptance -k "E06a"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/sales/unit/test_cliente.py` | Documentos válidos e inválidos | RF-VEN-01, 02 |
| Unitario | `tests/sales/unit/test_pedido.py` | Tabla de transiciones completa (parametrizada), atraso con `hoy`, faltantes | RF-VEN-08 a 16, 35, 37, 41 |
| Caso de uso | `tests/sales/usecases/test_pedidos_port.py` | Varias OP por pedido; regreso a `CONFIRMADO`; `ENTREGADO`/`CANCELADO` no cambian | RF-VEN-12, 13, 41, 42 |
| Integración | `tests/sales/integration/test_clientes.py` | Cliente genérico, ficha, no eliminar con documentos | RF-VEN-03 a 05 |
| Aceptación | `features/clientes_pedidos.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-VEN-01, RF-VEN-02, RF-VEN-03, RF-VEN-04, RF-VEN-05 | §1 `cliente.py`, `clientes.py` · §3 `validar_documento`, `total_ultimos_90_dias` · §5 `/clientes/` · §7 |
| RF-VEN-06, RF-VEN-07, RF-VEN-08, RF-VEN-09, RF-VEN-10, RF-VEN-11 | §1 `pedido.py`, `pedidos.py` · §3 `faltantes` · §5 pedidos · §7 `test_pedido.py` |
| RF-VEN-12, RF-VEN-13, RF-VEN-14, RF-VEN-15, RF-VEN-16 | §3 `transicion_pedido`, `atrasado` · §5 tablero · §7 |
| RF-VEN-37 | §1 `pedidos.py` · §3 `transicion_pedido` · §5 cancelar · §7 |
| RF-VEN-41, RF-VEN-42 | §1 `pedidos_port.py` · §3 `revertir_a_confirmado` · §7 `test_pedidos_port.py` |

## 9. Dependencias de dudas abiertas

- Ninguna.
