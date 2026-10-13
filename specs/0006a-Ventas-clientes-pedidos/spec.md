# Spec 0006a — Ventas: clientes y pedidos

Estado: **implementada** (2026-10-13; aprobada por el PO: "si") · alineada el 2026-10-13 · **estados ajustados por el PO el 2026-10-13: Creado ▸ Aprobado ▸ Facturado ▸ Entregado** con lo implementado (0002a enmienda 4: productos con "Se vende"; 0002e: precio con impuestos; 0003a: stock y lotes; 0005a: la OP no se vincula a pedidos) y con las decisiones del PO del 2026-10-13

Épica E06 (Ventas y pedidos), parte 1 de 3. Depende de: 0001c (permisos), 0002a, 0002e, 0003a. La usa: 0006b (la venta entrega el pedido).

## Contexto y objetivo

La cervecera vende sobre todo a pedido (bares, restaurantes, distribuidores) y en menor medida al público. Necesita registrar a sus clientes y sus pedidos, saber en todo momento si tiene stock para entregarlos y ver qué pedidos están atrasados.

**Objetivo:** registrar clientes con su documento validado y pedidos con fecha de entrega, mostrando en cada pedido el stock disponible, lo que falta y la alerta de quiebre de stock, para que el usuario decida si produce o compra.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Ventas, Gerente, Administrador | Gestionan clientes y pedidos y cancelan pedidos (plantillas de rol de 0001c) |
| Producción, Almacén | Consultan los pedidos y sus faltantes (lectura) |

## Historias de usuario

- H1: Como vendedor, quiero registrar, consultar y editar a mis clientes con su documento validado para facturarles sin errores.
- H4: Como vendedor, quiero buscar al cliente por nombre o documento al tomar un pedido o vender, y si no existe, registrarlo ahí mismo con sus datos mínimos.
- H2: Como vendedor, quiero crear un pedido con fecha de entrega y ver, por línea, el stock disponible y lo que falta.
- H3: Como vendedor, quiero ver los pedidos por estado, con los atrasados y los que tienen quiebre de stock, para cumplir lo comprometido.

## Definiciones

- **Producto vendible:** un producto activo con la casilla **Se vende** (bien o servicio; 0002a, RF-CAT-38 y 39).
- **Cliente genérico "Clientes varios":** cliente sin documento para ventas al público. Existe uno por empresa; no se elimina ni se desactiva.
- **Precio:** el precio unitario del pedido incluye sus impuestos, como el precio de lista (0002e, RF-CAT-59); se precarga con el de lista del producto y se puede cambiar.
- **Stock disponible de una línea:** el stock sin vencer del producto en todos los almacenes, hoy. No hay reserva: varios pedidos comparten el mismo disponible.
- **Faltante:** max(0, cantidad de la línea − stock disponible). Un servicio no lleva stock: no tiene faltante.
- **Quiebre de stock:** una línea, o un pedido, con faltante mayor a 0.
- **Atrasado:** un pedido no Entregado ni Cancelado cuya fecha de entrega ya pasó.

**Estados del pedido** (PO, 2026-10-13, modelo de pedido de venta): **Creado ▸ Aprobado ▸ Facturado ▸ Entregado**, y **Cancelado** fuera de la barra. La venta no es un documento aparte: es el pedido facturado.

| Desde | Hacia | Cuándo |
|---|---|---|
| Creado | Aprobado | El usuario aprueba el pedido; exige stock suficiente |
| Aprobado | Facturado | Se factura: vuelve a validar el stock, se emite el comprobante, **se descuenta el stock** y se genera la cobranza (0006b) |
| Facturado | Entregado | Se confirma la entrega al cliente (0006b) |
| Creado, Aprobado | Cancelado | El usuario cancela el pedido con motivo |

Una venta directa (B2C, mostrador) crea el pedido ya **Facturado y Entregado**, con su cobranza **Pagada** con el método elegido (0006b). La **cobranza** de un pedido facturado pasa de Pendiente a Pagada cuando sus pagos, con uno o varios métodos, suman su total (0006b).

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-VEN-01 Gestionar clientes

- RF-VEN-01 (PO, 2026-10-13: "básico el CRU"): CUANDO un usuario con `ventas.cliente.gestionar` registra o edita un cliente con nombre o razón social, tipo de documento, número, teléfono, email, estado (activo o inactivo) y comentarios, y opcionalmente dirección fiscal, contacto y canal (`B2B` o `B2C`), EL SISTEMA lo guarda si los datos son válidos y el documento no existe en la empresa. Son obligatorios el nombre, el tipo de documento y el número (salvo "sin documento"); teléfono y email son opcionales. Los clientes se crean, se consultan y se editan; no se eliminan. Los tipos salen del **maestro de tipos de documento** (RF-VEN-49).
- RF-VEN-02: SI el número no cumple las reglas de su tipo de documento (RF-VEN-49: obligatorio o no, longitud, caracteres y validación especial; p. ej. un DNI que no tiene 8 dígitos o un RUC que no pasa el dígito verificador), o el email no es válido, ENTONCES EL SISTEMA rechaza el cliente e indica el motivo junto al campo.
- RF-VEN-03: CUANDO se registra una empresa, EL SISTEMA le crea el cliente genérico "Clientes varios" (`SIN_DOC`, `B2C`). Las empresas ya registradas lo reciben al aplicar esta spec.
- RF-VEN-04: CUANDO se abre la ficha de un cliente, EL SISTEMA muestra sus datos y sus pedidos. Sus ventas, el total comprado en los últimos 90 días y la fecha de su última compra se agregan con 0006b.
- RF-VEN-05: EL SISTEMA no elimina clientes: un cliente que ya no se usa se **desactiva** (y se puede volver a activar). "Clientes varios" no se desactiva.
- RF-VEN-49 (PO, 2026-10-13: "en casos similares colócalo en el maestro"; constitución, art. 5.1): EL SISTEMA mantiene un **maestro de tipos de documento de identidad** a nivel de plataforma (el catálogo 06 de SUNAT es el mismo para todas las empresas), que administra el super admin: código SUNAT (único), nombre, si exige número, longitud mínima y máxima, caracteres permitidos (solo dígitos, o letras y dígitos), **validación especial** (ninguna o "dígito verificador del RUC", de una lista fija que sí está en el código) y activo. Se siembra con: DNI (1; 8 dígitos), carné de extranjería (4; 1 a 12 alfanuméricos), RUC (6; 11 dígitos con dígito verificador), pasaporte (7; 1 a 12 alfanuméricos) y sin documento (0; sin número). Un tipo desactivado no se ofrece, pero quien ya lo tiene lo conserva; un tipo en uso no se elimina ni cambia de código. Lo usan los clientes y también los **proveedores** (0002d, que hoy valida RUC y DNI en el código).
- RF-VEN-43: EL SISTEMA lista los clientes con la grilla estándar (docs/ux.md §5): buscador por nombre o documento y filtros por canal y estado.
- RF-VEN-44: SI el cliente está desactivado, ENTONCES EL SISTEMA no lo ofrece en pedidos nuevos; los pedidos que ya lo tienen lo conservan.
- RF-VEN-50 (PO, 2026-10-13): CUANDO un usuario elige el cliente de un pedido (y de una venta, 0006b), EL SISTEMA lo **busca por nombre o número de documento** entre los clientes activos, mientras escribe. SI no lo encuentra y el usuario tiene `ventas.cliente.gestionar`, ENTONCES EL SISTEMA le permite **registrarlo ahí mismo** con los datos mínimos (nombre o razón social, tipo y número de documento, teléfono y email opcionales, comentarios), con las mismas validaciones de RF-VEN-01 y 02, y lo deja elegido sin salir del pedido.

### UC-VEN-02 Crear y editar un pedido

- RF-VEN-06: CUANDO un usuario con `ventas.pedido.gestionar` crea un pedido con cliente activo, fecha de entrega comprometida, líneas (producto vendible, cantidad mayor a 0 con 4 decimales y precio unitario mayor a 0 con 2 decimales, precargado con el de lista) y comentario, EL SISTEMA lo guarda como **Creado** con un número correlativo por empresa (`P-000001`). Un producto puede ir en una sola línea del pedido.
- RF-VEN-07: MIENTRAS el pedido esté Creado, EL SISTEMA permite editarlo: cliente, fecha, líneas y comentario.
- RF-VEN-48: EL SISTEMA muestra el total del pedido = Σ cantidad × precio, con 2 decimales half-up por línea (los precios ya incluyen los impuestos; el desglose lo hace la venta, 0006b).

### UC-VEN-03 Confirmar un pedido

- RF-VEN-08: CUANDO un usuario con `ventas.pedido.gestionar` aprueba un pedido Creado con al menos una línea, EL SISTEMA vuelve a validar el cliente y los productos, **exige stock disponible suficiente** en cada línea de un bien y lo pasa a **Aprobado**: sus precios y cantidades quedan fijos. SI alguna línea tiene faltante, ENTONCES no lo aprueba e indica todos los faltantes ("Stock insuficiente: <SKU> faltan <n>; …"). Facturar vuelve a validar el stock (doble validación, PO 2026-10-13; 0006b), porque no hay reserva.
- RF-VEN-11: SI se intenta cambiar las líneas de un pedido que ya no está Creado, ENTONCES EL SISTEMA lo rechaza: para cambiarlas se cancela y se crea otro (RN-VEN-06). Mientras esté Aprobado, su fecha de entrega y su comentario sí se pueden cambiar.

### UC-VEN-04 Stock del pedido y quiebre de stock

- RF-VEN-45: EL SISTEMA muestra en cada línea de un pedido Creado o Aprobado el **stock disponible** y el **faltante**, y la alerta **"Quiebre de stock"** si el faltante es mayor a 0 (PO, 2026-10-13: el sistema solo informa; el usuario decide si produce o compra). Reemplaza RF-VEN-09 y 10.
- RF-VEN-46: EL SISTEMA muestra los pedidos en dos vistas que el usuario alterna (PO, 2026-10-13): **Lista** (la grilla estándar, ordenada por fecha de entrega: número, cliente, fecha de entrega, total y estado) y **Kanban** (una columna por estado: Creado, Aprobado, Facturado y Entregado; Cancelado solo si se filtra por él), con tarjetas de número, cliente, fecha de entrega y total. En las dos se ven los indicadores **Atrasado** y **Quiebre de stock** y se aplican los mismos filtros: estado, cliente, fechas de entrega, número, "solo atrasados" y "solo con quiebre de stock". La vista elegida queda en la dirección de la página (se puede guardar o compartir). En el kanban las tarjetas no se arrastran: los estados cambian con sus acciones (aprobar, facturar, confirmar la entrega, cancelar).
- RF-VEN-15: MIENTRAS la fecha de entrega de un pedido Creado, Aprobado o Facturado esté vencida, EL SISTEMA lo marca como **Atrasado**.
- RF-VEN-47: CUANDO un usuario con `ventas.pedido.ver` abre el inicio, EL SISTEMA le muestra una **alerta** con la cantidad de pedidos Creados o Aprobados con quiebre de stock, que lleva al listado **filtrado** por "solo con quiebre de stock" (como los avisos de stock bajo, 0003c). El filtro también se puede elegir en el listado.

### UC-VEN-05 Entregar y cancelar

- RF-VEN-14: EL SISTEMA pasa un pedido Aprobado a **Facturado** al facturarlo y un pedido Facturado a **Entregado** al confirmar su entrega; ambas acciones, la cobranza y la venta directa son de 0006b. La anulación de un pedido facturado es de 0006c.
- RF-VEN-37: CUANDO un usuario con `ventas.pedido.cancelar` cancela con motivo un pedido Creado o Aprobado, EL SISTEMA lo pasa a **Cancelado** y registra quién, cuándo y por qué.
- RF-VEN-16: SI se intenta una transición que no está en la tabla de estados, ENTONCES EL SISTEMA la rechaza.

## Requisitos no funcionales

- Ninguno propio.

## Casos límite

- **Sin reserva de stock:** aprobar exige stock, pero no lo aparta: dos pedidos aprobados pueden contar el mismo stock. Cuando uno se factura y lo descuenta, el otro pasa a "Quiebre de stock" y no se podrá facturar hasta reponer (doble validación).
- **Stock vencido:** no cuenta como disponible.
- **Producto desactivado después de aprobar:** el pedido lo conserva; facturar decidirá (0006b).
- **Servicio en un pedido:** no tiene stock ni faltante.
- **Fecha de entrega pasada al crear:** se permite (el pedido nace Atrasado), para registrar pedidos tomados antes.

## Fuera de alcance

Vínculo del pedido con las OP o las compras (PO, 2026-10-13: el usuario decide y actúa; ver 0005a), reserva de stock, entregas parciales, cotizaciones, leads y oportunidades, listas de precios por cliente, descuentos por volumen, cuentas por cobrar, guía de remisión.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Impacto en otras specs

- **0001b (plataforma):** pantalla nueva "Tipos de documento" para el super admin (RF-VEN-49).
- **0002d (implementada):** el tipo de documento del proveedor sale del maestro (RF-COM-01 ajustado); los proveedores existentes conservan su RUC o DNI.

- **0006b (se reescribe):** pasa a ser **facturación del pedido, entrega, venta directa y cobranza**: facturar un pedido Aprobado (comprobante y salida de stock), confirmar la entrega, la venta directa B2C (pedido Facturado y Entregado con cobranza Pagada), y la cobranza con pagos de uno o varios métodos (maestro de métodos de pago por empresa) y su listado. Usa la búsqueda y el registro rápido del cliente (RF-VEN-50).
- **0005a:** sin cambios (la OP solo lleva un comentario libre).

## RF retirados (historia)

Indicador "Listo para facturar" (PO, 2026-10-13: "no debe aparecer, no es un estado"; se retira de la lista, el kanban y la ficha) · RF-VEN-09 (ofrecer producción) y RF-VEN-10 ("por comprar") → RF-VEN-45 · RF-VEN-12 y 13 (estados movidos por las OP) · RF-VEN-41 y 42 (pedido con varias OP): la OP no se vincula a pedidos (0005a, PO 2026-10-12) · estados `BORRADOR`, `EN_PRODUCCION` y `LISTO` → Creado y Aprobado (PO, 2026-10-13: modelo de pedido de venta Creado ▸ Aprobado ▸ Facturado ▸ Entregado).

## Dudas abiertas

- Ninguna.
