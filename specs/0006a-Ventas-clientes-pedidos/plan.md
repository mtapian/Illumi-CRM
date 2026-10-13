# Plan 0006a — Ventas: clientes y pedidos

Estado: implementado (2026-10-13; aprobado por el PO: "go"), para la spec aprobada el 2026-10-13 ("si")

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto nuevo: `src/sales` (app `sales`), con las mismas capas que compras y producción. Usa la fachada del catálogo (productos vendibles y su precio), el `InventarioService` (stock disponible) y la fachada de tenancy (tipos de documento). El maestro de tipos de documento es dato de plataforma y vive en tenancy; lo usan clientes y proveedores.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/shared/domain/documentos.py` | `ReglasDocumento` (abreviatura, código SUNAT, nombre, exige número, longitud mínima y máxima, caracteres, validación especial) y `validar_numero(reglas, numero)`: reglas genéricas y la especial `RUC` (11 dígitos, prefijo y dígito verificador, el `Ruc` actual). Se retiran `TIPOS` y `validar_documento` fijos | RF-VEN-02, 49 |
| `src/tenancy/infrastructure/models.py` + migración | `TipoDocumento` (plataforma, sin empresa) sembrado con DNI, CE, RUC, PAS y SD | RF-VEN-49 |
| `src/tenancy/application/plataforma.py`, `fachada.py` | `GuardarTipoDocumento` (super admin); fachada `tipos_documento(solo_activos)` y `reglas_documento(abreviatura)` | RF-VEN-49 |
| `src/tenancy/interfaces/` | `/plataforma/tipos-documento/` (listado de maestro y formulario, sin eliminar) en el menú de plataforma | RF-VEN-49 |
| `src/purchasing/...` | El proveedor valida su documento con las reglas del maestro (por la fachada de tenancy); el selector ofrece los tipos activos | 0002d RF-COM-01 |
| `src/sales/domain/cliente.py`, `pedido.py`, `errores.py` | Datos y validación del cliente; pedido: estados y transiciones, líneas, total, faltante, indicadores (quiebre, listo, atrasado) | RF-VEN-01, 02, 06 a 08, 11, 14 a 16, 37, 45, 48 |
| `src/sales/application/clientes.py`, `pedidos.py` | `GuardarCliente` (crea o edita; también el registro rápido), `CambiarEstadoCliente`, búsqueda por nombre o documento; sin eliminar (CRU, PO 2026-10-13); `CrearPedido`, `EditarPedido`, `AprobarPedido`, `CancelarPedido`; consulta de disponibilidad | todos |
| `src/sales/infrastructure/` | Modelos, repositorios, contenedor, sembrador de "Clientes varios" (0001a) y migración que lo crea en las empresas existentes | RF-VEN-03 |
| `src/sales/interfaces/` | `/ventas/clientes/`, `/ventas/pedidos/` (Lista y Kanban), `/ventas/pedidos/nuevo/`, `/ventas/pedidos/<id>/`; menú "Ventas"; alerta del inicio | RF-VEN-04, 43, 45 a 47 |
| `src/inventory/application/servicio.py` | `disponibles(producto_ids, hoy)`: stock sin vencer por producto, sumando almacenes (lectura) | RF-VEN-45 |
| `pyproject.toml` | `sales` en import-linter (contrato como el de compras; nadie depende de ventas) | — |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `tenancy_tipodocumento` | abreviatura (DNI, CE, RUC, PAS, SD), codigo_sunat, nombre, exige_numero, longitud_min, longitud_max, caracteres (`DIGITOS`/`ALFANUMERICO`), validacion (`NINGUNA`/`RUC`), activo | UNIQUE abreviatura y codigo_sunat; CHECK 0 ≤ min ≤ max; sin número ⇒ min = max = 0 | RF-VEN-49 |
| `sales_cliente` | empresa, nombre, tipo_doc (abreviatura), num_doc, telefono, email, comentarios, activo; opcionales: direccion, contacto, canal (`B2B`/`B2C`); es_generico | UNIQUE(empresa, tipo_doc, num_doc) salvo `SD`; un solo genérico por empresa; el genérico siempre activo | RF-VEN-01, 03, 05 |
| `sales_pedido` | empresa, numero, cliente, fecha_entrega, comentario, estado (`CREADO`/`APROBADO`/`FACTURADO`/`ENTREGADO`/`CANCELADO`; Facturado y Entregado los pone 0006b), total, creado_por/en, aprobado_por/en, cancelado_por/en, motivo_cancelacion | UNIQUE(empresa, numero); CHECK total ≥ 0; Cancelado ⇒ motivo | RF-VEN-06, 08, 37, 48 |
| `sales_pedidolinea` | pedido, producto, cantidad `NUMERIC(14,4)`, precio `NUMERIC(14,2)`, subtotal | UNIQUE(pedido, producto); CHECK cantidad > 0, precio > 0; trigger: las líneas de un pedido que no está Creado no cambian | RF-VEN-06, 11 |

Número `P-000001` con `SequencePort.siguiente("PEDIDO")`. Clientes y proveedores guardan la **abreviatura** del tipo (hoy los proveedores ya guardan `RUC`/`DNI`): no hace falta convertir datos.

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `validar_numero(reglas, numero)` | Sin número si no lo exige; longitud, caracteres; especial `RUC`. Mensajes: "El DNI debe tener 8 dígitos", "El Carné de extranjería debe tener de 1 a 12 letras o números", "El RUC no es válido", "Sin documento no lleva número" | RF-VEN-02 |
| `validar_cliente(datos, reglas)` | Nombre obligatorio, documento según su tipo, email con formato simple, canal | RF-VEN-01, 02 |
| `transicion(estado, accion)` | Tabla de estados de la spec | RF-VEN-14, 16, 37 |
| `validar_lineas(lineas)` | Al menos una para confirmar; cantidad > 0 (4 decimales), precio > 0 (2 decimales), sin repetir producto | RF-VEN-06, 08 |
| `total(lineas)` | Σ cantidad × precio, half-up a 2 decimales por línea | RF-VEN-48 |
| `faltante(cantidad, disponible, es_servicio)` y `indicadores(pedido, faltantes, hoy)` | Quiebre de stock y Atrasado (no Entregado ni Cancelado, con fecha vencida); "Listo para facturar" se retiró (PO, 2026-10-13: no es un estado) | RF-VEN-15, 45, 46 |

## 4. Algoritmos clave

```
AprobarPedido(actor, pedido_id):                   # RF-VEN-08
  en una transacción, con el pedido bloqueado (FOR UPDATE):
    transicion(estado, "aprobar")
    cliente activo; productos activos y vendibles; validar_lineas
    disponibles = InventarioService.disponibles(bienes del pedido, hoy)
    faltantes de todas las líneas → rechaza con todos ("Stock insuficiente: …"), sin cambiar el estado
    estado = APROBADO; aprobado_por/en          # facturar (0006b) vuelve a validar: no hay reserva

Disponibilidad(pedidos, hoy):                      # RF-VEN-45, 46, 47 (lectura)
  productos = líneas de los pedidos Creados o Aprobados
  disponibles = InventarioService.disponibles(productos, hoy)   # una consulta
  por línea: faltante = max(0, cantidad − disponible) (0 en servicios)
  quiebre del pedido = algún faltante > 0
```

ponytail: la disponibilidad se calcula al vuelo para los pedidos abiertos (sin reserva ni columnas guardadas); si el volumen crece, guardar un resumen por pedido.

## 5. Interfaz

Patrones de docs/ux.md (grilla §5, barra de acciones abajo, "Más acciones" con lo destructivo al final, confirmaciones que explican qué ocurre).

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/plataforma/tipos-documento/` | Listado de maestro y formulario (código SUNAT, abreviatura, nombre, reglas, validación especial, activo); abreviatura y código fijos una vez creados; sin eliminar | RF-VEN-49 |
| `/ventas/clientes/` | Grilla: buscador por nombre o documento, filtros por canal y estado; `?nuevo=1` y `?editar=<id>` abren el formulario (sin eliminar; activar o desactivar); la ficha muestra sus pedidos | RF-VEN-01 a 05, 43, 44 |
| Selector de cliente (pedido; luego la venta) | Campo de búsqueda con sugerencias (`/ventas/clientes/buscar/?q=`, JSON con los activos que coinciden por nombre o documento, máximo 10) y "+ Nuevo cliente", que abre un `<dialog>` con los datos mínimos y lo deja elegido (POST que devuelve el cliente creado o los errores por campo) | RF-VEN-50 |
| `/ventas/pedidos/` | `?vista=lista` (grilla por fecha de entrega) o `?vista=kanban` (columnas Creado, Aprobado, Facturado, Entregado; Cancelado solo si se filtra), mismos filtros (estado, cliente, fechas, número, `atrasados=1`, `quiebre=1`) e indicadores | RF-VEN-15, 46 |
| `/ventas/pedidos/nuevo/` y `/ventas/pedidos/<id>/` | Cliente, fecha de entrega, comentario y líneas dinámicas (producto, cantidad, precio precargado con el de lista, subtotal); por línea, disponible, faltante y "Quiebre de stock"; total. Barra **Creado ▸ Aprobado ▸ Facturado ▸ Entregado**; acción principal "Aprobar" (Facturar y Confirmar entrega llegan con 0006b); "Más acciones" › Cancelar (con motivo). Aprobado: solo fecha de entrega y comentario editables | RF-VEN-06 a 08, 11, 37, 45, 48 |
| Inicio | Alerta "N pedidos con quiebre de stock" → `/ventas/pedidos/?quiebre=1`, solo con `ventas.pedido.ver` (registro de avisos, `shared/interfaces/avisos.py`) | RF-VEN-47 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Maestro de tipos de documento en tenancy, a nivel de plataforma; las reglas son datos y solo la validación especial (`RUC`) es código | Enum en el código; maestro por empresa | PO ("en casos similares colócalo en el maestro") y constitución art. 5.1; el catálogo 06 es de SUNAT, igual para todas las empresas |
| Clientes y proveedores guardan la abreviatura; abreviatura y código del tipo no se editan ni el tipo se elimina (solo se desactiva) | FK al tipo; borrar tipos sin uso | Sin conversión de datos; tenancy no necesita saber qué contexto usa un tipo |
| Contexto `sales` con contrato de import-linter como compras; nadie depende de ventas | Ventas dentro del catálogo | Mismo patrón que compras y producción |
| Disponibilidad calculada al vuelo con una consulta agrupada (`InventarioService.disponibles`) | Reservar stock o guardar el faltante | La spec no reserva; el dato debe ser el de hoy |
| Kanban sin arrastrar tarjetas, con los mismos filtros que la lista | Arrastrar para cambiar de estado | Los estados cambian con su acción (aprobar, facturar, entregar, cancelar) |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/sales tests/acceptance -k "E06a"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/shared/unit/test_documentos.py` | Reglas genéricas y especial RUC con los tipos sembrados | RF-VEN-02, 49 |
| Unitario | `tests/sales/unit/test_cliente.py`, `test_pedido.py` | Cliente; transiciones, líneas, total, faltante e indicadores | RF-VEN-01, 02, 06 a 08, 11, 14 a 16, 45, 48 |
| Caso de uso | `tests/tenancy/usecases/test_tipos_documento.py` | Guardar, código y abreviatura fijos, desactivar | RF-VEN-49 |
| Caso de uso | `tests/sales/usecases/test_clientes.py`, `test_pedidos.py` | Documento único, genérico intocable, eliminar o desactivar, desactivado no se ofrece; crear, editar, confirmar, cancelar, permisos | RF-VEN-01 a 08, 11, 16, 37, 44 |
| Integración | `tests/sales/integration/test_modelos.py`, `test_pantallas.py` | Constraints y trigger; listado de clientes, Lista y Kanban con filtros, alerta del inicio, aislamiento | RF-VEN-15, 43, 46, 47 |
| Integración | `tests/purchasing/...` (existentes) | Proveedores con el maestro: 0002d sigue en verde | RF-COM-01 |
| Aceptación | `features/clientes_pedidos.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-VEN-49 | §1 documentos, tenancy · §2 `tenancy_tipodocumento` · §5 plataforma · §7 |
| RF-VEN-01 a 05, 43, 44 | §1 `cliente.py`, `clientes.py` · §2 `sales_cliente` · §5 clientes · §7 |
| RF-VEN-06 a 08, 11, 14, 16, 37, 48 | §1 `pedido.py`, `pedidos.py` · §2 · §4 · §5 · §7 |
| RF-VEN-15, 45, 46, 47 | §3 indicadores · §4 disponibilidad · §5 · §7 |

## 9. Dependencias

- RF-VEN-14: Facturado y Entregado los ponen las acciones de 0006b; aquí solo se prueban las transiciones en el dominio.
- RF-VEN-04: ventas, total de 90 días y última compra llegan con 0006b.
