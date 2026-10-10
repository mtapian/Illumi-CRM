# Spec 001 — Tenancy y accesos

Estado: borrador

## Contexto y objetivo

Cada cervecera (empresa) necesita un espacio propio donde sus datos estén aislados de las demás. La plataforma necesita **decidir qué módulos y funcionalidades contrata cada empresa**. Cada empresa necesita **decidir qué puede hacer cada uno de sus usuarios** dentro de lo contratado, sin depender de roles fijos.

**Alcance (decisión del PO, 2026-10-10, PRD Q11):** la spec entra completa en S0, incluidos planes, ajustes con vigencia y vista previa de impacto, aunque al inicio haya un solo cliente. Es una excepción aprobada al principio de simplicidad (constitución, art. 7.6), porque el modelo comercial por planes es parte del producto desde el lanzamiento.

**Objetivo:** que una empresa se registre y opere en minutos, y que el acceso de cada usuario sea exactamente el que su empresa le dio dentro de lo que la plataforma le habilitó.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Visitante | Registra su empresa con prueba gratis |
| Administrador de la empresa | Configura los datos de la empresa, gestiona usuarios y roles, crea tokens de API |
| Usuario de la empresa | Inicia sesión y opera según sus permisos |
| Super admin (plataforma) | Activa planes, define qué incluye cada plan, habilita o quita funcionalidades por empresa |

## Historias de usuario

- H1: Como visitante, quiero registrar mi empresa con una prueba gratis para empezar a usar el sistema sin hablar con ventas.
- H2: Como usuario, quiero iniciar sesión con mi email y contraseña para trabajar con los datos de mi empresa.
- H3: Como administrador, quiero crear usuarios y asignarles uno o más roles para que cada persona haga solo lo que le corresponde.
- H4: Como administrador, quiero configurar los datos fiscales de mi empresa para que aparezcan en los comprobantes.
- H5: Como plataforma, quiero restringir el acceso de una empresa con la suscripción vencida o suspendida para cobrar el servicio sin borrar sus datos.
- H6: Como super admin, quiero activar, suspender y reactivar planes de una empresa para administrar las suscripciones.
- H7: Como super admin, quiero definir qué funcionalidades incluye cada plan para empaquetar la oferta comercial.
- H8: Como super admin, quiero agregar o quitar funcionalidades a una empresa concreta, con vigencia opcional, para dar pruebas o hacer excepciones sin cambiar su plan.
- H9: Como administrador, quiero crear roles propios combinando permisos para adaptar el sistema a cómo se organiza mi empresa.
- H10: Como administrador, quiero ver quién cambió roles, permisos y usuarios para auditar los accesos.
- H11: Como administrador, quiero crear tokens de API con permisos limitados para integrar el sistema con n8n u otras herramientas.

## Definiciones

- **Empresa (tenant):** cliente del SaaS. Sus datos nunca son visibles para otra empresa.
- **Módulo:** área del sistema que aparece en el menú (Inventario, Producción…).
- **Funcionalidad:** capacidad comercializable dentro de un módulo (p. ej. "Envasado multipresentación"). Es lo que habilita el super admin.
- **Permiso:** acción concreta (p. ej. `ventas.venta.anular`). Es lo que el administrador de la empresa asigna a sus roles.
- **Habilitaciones de una empresa:** funcionalidades de su plan + las agregadas a esa empresa − las quitadas a esa empresa, considerando solo los ajustes vigentes. CORE siempre está habilitado.
- **Permisos efectivos de un usuario:** (unión de los permisos de sus roles activos) ∩ (permisos de las funcionalidades habilitadas). El rol de sistema "Administrador" equivale a todos los permisos habilitados (RN-TEN-10).
- **Ajuste vigente:** ajuste sin fecha de fin, o con fecha de fin igual o posterior a hoy (hora de Lima).
- **Usuario técnico:** usuario que no puede iniciar sesión en la interfaz y es dueño de uno o más tokens de API; sus roles definen qué puede leer cada token. Se crea y gestiona solo desde UC-TEN-11 y no cuenta para el límite de usuarios del plan.
- **Vencimiento de la prueba o la suscripción:** la empresa opera hasta el final del día de la fecha de término (hora de Lima) y queda vencida desde el día siguiente. Renovar es activar un plan con una nueva fecha de término (RF-TEN-22).

### Modelo de acceso en 3 niveles

```
NIVEL 1 · PLATAFORMA (super admin)
  Catálogo:  Módulo ─┬─ Funcionalidad ─┬─ Permiso (acción)
  Plan  ──► funcionalidades incluidas
  Empresa ──► habilitaciones = plan ± ajustes por empresa (vigencia opcional)

NIVEL 2 · EMPRESA (administrador)
  Rol propio ──► permisos elegidos SOLO entre las funcionalidades habilitadas
  Usuario ──► uno o más roles

NIVEL 3 · USUARIO
  Permisos efectivos = (∪ permisos de sus roles) ∩ (permisos habilitados y vigentes)
```

El catálogo de módulos, funcionalidades y permisos lo define el producto. El super admin lo **empaqueta y habilita**; no inventa permisos.

### Catálogo de módulos, funcionalidades y permisos (MVP)

| Módulo | Funcionalidad | Permisos | Depende de |
|---|---|---|---|
| **CORE** (siempre activo) | Administración de empresa | `core.empresa.gestionar`, `core.usuario.gestionar`, `core.rol.gestionar`, `core.auditoria.ver`, `core.suscripcion.ver` | — |
| | Dashboard | `core.dashboard.ver` | — |
| **CATALOGO** | Productos y presentaciones | `catalogo.producto.ver`, `catalogo.producto.gestionar`, `catalogo.unidad.gestionar`, `catalogo.isc.gestionar` | CORE |
| **INVENTARIO** | Stock y kardex | `inventario.stock.ver`, `inventario.kardex.ver`, `inventario.costo.ver` | CATALOGO |
| | Ajustes de inventario | `inventario.ajuste.registrar`, `inventario.ajuste.anular` | Stock y kardex |
| | Multialmacén | `inventario.almacen.gestionar` | Stock y kardex |
| | Lotes y vencimientos | `inventario.lote.ver` | Stock y kardex |
| **COMPRAS** | Compras y proveedores | `compras.proveedor.gestionar`, `compras.compra.ver`, `compras.compra.registrar`, `compras.compra.anular` | INVENTARIO |
| **PRODUCCION** | Recetas | `produccion.receta.ver`, `produccion.receta.gestionar` | INVENTARIO |
| | Órdenes de producción | `produccion.op.ver`, `produccion.op.planificar`, `produccion.op.ejecutar`, `produccion.op.anular`, `produccion.reporte.ver` | Recetas |
| | Envasado multipresentación | `produccion.envasado.registrar` | Órdenes de producción |
| **VENTAS** | Clientes | `ventas.cliente.ver`, `ventas.cliente.gestionar` | CATALOGO |
| | Pedidos | `ventas.pedido.ver`, `ventas.pedido.gestionar`, `ventas.pedido.cancelar` | Clientes, INVENTARIO |
| | Ventas | `ventas.venta.ver`, `ventas.venta.registrar`, `ventas.venta.anular` | Clientes, INVENTARIO |
| **FACTURACION** | Facturación electrónica | `facturacion.config.gestionar`, `facturacion.comprobante.ver`, `facturacion.comprobante.gestionar` | Ventas |
| **FINANZAS** | Gastos | `finanzas.gasto.ver`, `finanzas.gasto.registrar`, `finanzas.gasto.anular` | CORE |
| | Estado de resultados | `finanzas.resultados.ver` | Ventas |
| **TRANSVERSAL** | Exportación CSV | `reportes.exportar` | — |
| | API de integración | `api.token.gestionar` | — |

`inventario.costo.ver` controla si el usuario ve costos y valorizaciones en cualquier pantalla, exportación o respuesta de la API.

### Plantillas de rol iniciales

Se crean como roles **editables** al registrar la empresa, solo con los permisos de las funcionalidades habilitadas en ese momento. "Administrador" es un rol de sistema y no se edita.

| Permiso / grupo | Administrador (sistema) | Gerente | Producción | Almacén | Ventas |
|---|:-:|:-:|:-:|:-:|:-:|
| `core.*` (empresa, usuarios, roles, auditoría) | ✔ | — | — | — | — |
| `core.dashboard.ver`, `core.suscripcion.ver` | ✔ | ✔ | ✔ | ✔ | ✔ |
| Catálogo: ver | ✔ | ✔ | ✔ | ✔ | ✔ |
| Catálogo: gestionar | ✔ | ✔ | ✔ | ✔ | — |
| `catalogo.isc.gestionar` (categorías y tarifas de ISC) | ✔ | — | — | — | — |
| Inventario: stock y kardex | ✔ | ✔ | ✔ | ✔ | stock |
| `inventario.costo.ver` | ✔ | ✔ | ✔ | ✔ | — |
| Ajustes: registrar / anular | ✔ / ✔ | ✔ / ✔ | — | ✔ / — | — |
| Compras: registrar / anular | ✔ / ✔ | ✔ / ✔ | — | ✔ / — | — |
| Producción: recetas, OP, envasado | ✔ | ✔ | ✔ (sin anular OP) | — | — |
| `produccion.op.anular` | ✔ | ✔ | — | — | — |
| Ventas: clientes, pedidos, registrar venta | ✔ | ✔ | — | — | ✔ |
| `ventas.venta.anular` | ✔ | ✔ | — | — | — |
| Facturación: ver / gestionar comprobantes | ✔ | ✔ | — | — | ver |
| `facturacion.config.gestionar` | ✔ | — | — | — | — |
| Finanzas: gastos y estado de resultados | ✔ | ✔ | — | — | — |
| `reportes.exportar` | ✔ | ✔ | ✔ | ✔ | — |

En las demás specs (002–008), las menciones a roles ("solo admin/gerente") se refieren a estas plantillas. La regla real es siempre el **permiso** de cada caso de uso.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-TEN-01 Registrar empresa con prueba gratis

- RF-TEN-01: CUANDO un visitante envía el registro con RUC, razón social, nombre comercial (opcional), su nombre, email y contraseña, EL SISTEMA crea en una sola operación la empresa, su usuario administrador, el almacén "Principal", las unidades de medida SUNAT básicas, las categorías de gasto, las series de facturación por defecto, las habilitaciones del plan de prueba y los roles iniciales.
- RF-TEN-02: SI cualquier paso del registro falla, ENTONCES EL SISTEMA no crea nada (RN-TEN-01).
- RF-TEN-03: SI el RUC no tiene 11 dígitos, no empieza con 10, 15, 17 o 20, no pasa el dígito verificador (módulo 11) o ya pertenece a otra empresa, ENTONCES EL SISTEMA rechaza el registro e indica el motivo (RN-TEN-03).
- RF-TEN-04: SI el email ya existe en la plataforma, ENTONCES EL SISTEMA rechaza el registro (RN-TEN-02).
- RF-TEN-05: CUANDO el registro termina, EL SISTEMA deja la empresa en estado `trial` con el plan de prueba durante N días (14 por defecto, configurable por la plataforma), autentica al usuario y le muestra el dashboard con una guía de primeros pasos.

### UC-TEN-02 Iniciar sesión

- RF-TEN-06: CUANDO un usuario ingresa email y contraseña válidos, EL SISTEMA lo lleva al dashboard de su empresa; al super admin, al panel de plataforma.
- RF-TEN-07: SI el usuario está inactivo o su empresa está suspendida, ENTONCES EL SISTEMA no le permite entrar y muestra un mensaje que explica el motivo.
- RF-TEN-08: SI un usuario falla 5 intentos consecutivos, ENTONCES EL SISTEMA lo bloquea durante 15 minutos (valores propuestos, PRD Q6).
- RF-TEN-09: CUANDO un usuario pide recuperar su contraseña, EL SISTEMA le envía por email un enlace de un solo uso que vence en 60 minutos.

### UC-TEN-03 Gestionar usuarios

- RF-TEN-10: CUANDO un usuario con `core.usuario.gestionar` crea, edita, activa o desactiva un usuario de su empresa, EL SISTEMA guarda el cambio y permite asignarle uno o más roles.
- RF-TEN-11: SI crear o reactivar un usuario supera el límite de usuarios activos del plan, ENTONCES EL SISTEMA lo rechaza (RN-TEN-04). Los usuarios técnicos no cuentan. Un límite vacío significa ilimitado.
- RF-TEN-12: SI un cambio deja a la empresa sin ningún usuario activo con el rol "Administrador", ENTONCES EL SISTEMA lo rechaza, incluso si dos administradores se desactivan entre sí al mismo tiempo (RN-TEN-05).
- RF-TEN-53: SI un usuario intenta asignar a otro, o a sí mismo, un rol o un permiso que él mismo no tiene, ENTONCES EL SISTEMA lo rechaza. Solo un usuario con el rol "Administrador" puede asignar ese rol.
- RF-TEN-13: EL SISTEMA nunca borra usuarios: los desactiva y conserva la autoría de sus documentos.
- RF-TEN-14: CUANDO se abre la ficha de un usuario, EL SISTEMA muestra sus permisos efectivos agrupados por módulo, de qué rol viene cada uno y cuáles no están disponibles por el plan.

### UC-TEN-04 Configurar datos de empresa

- RF-TEN-15: CUANDO un usuario con `core.empresa.gestionar` edita la razón social, nombre comercial, dirección fiscal, ubigeo, teléfono, email, logo o % de IGV, EL SISTEMA guarda los cambios.
- RF-TEN-16: SI el % de IGV no está entre 0 y 100 con hasta 2 decimales, ENTONCES EL SISTEMA lo rechaza. Cada cambio de IGV se registra con su fecha de vigencia y los documentos usan el IGV vigente a su fecha de emisión (RN-TEN-07).
- RF-TEN-17: EL SISTEMA no permite editar el RUC después del registro.

### UC-TEN-05 Restringir acceso por suscripción

- RF-TEN-18: MIENTRAS la prueba o la suscripción de una empresa estén vencidas, o la empresa esté suspendida, EL SISTEMA solo permite a sus usuarios ver la página de suscripción y cerrar sesión, y rechaza sus tokens de API (RN-TEN-06). Los envíos pendientes a SUNAT continúan (spec 007, RF-FAC-15).
- RF-TEN-19: MIENTRAS falten 7 días o menos para que venza la prueba o la suscripción, EL SISTEMA muestra un aviso con los días restantes.
- RF-TEN-20: EL SISTEMA nunca borra datos por vencimiento o suspensión.
- RF-TEN-21: CUANDO una empresa es suspendida mientras un usuario tiene la sesión abierta, EL SISTEMA lo bloquea en su siguiente acción.

### UC-TEN-06 Activar plan (super admin)

- RF-TEN-22: CUANDO el super admin activa un plan con fecha de término, suspende o reactiva una empresa, EL SISTEMA aplica el cambio y lo registra con usuario, fecha y motivo.
- RF-TEN-23: CUANDO una empresa cambia de plan, EL SISTEMA reemplaza sus habilitaciones base por las del nuevo plan y conserva sus ajustes vigentes.
- RF-TEN-24: EL SISTEMA permite listar empresas filtrando por estado y plan.

### UC-TEN-07 Configurar funcionalidades de un plan (super admin)

- RF-TEN-25: CUANDO el super admin edita un plan, EL SISTEMA permite elegir sus funcionalidades (agrupadas por módulo) y sus límites de usuarios y productos.
- RF-TEN-26: SI se intenta incluir una funcionalidad sin todas las que requiere, ENTONCES EL SISTEMA lo rechaza e indica cuáles faltan (RN-TEN-09).
- RF-TEN-27: CUANDO el super admin guarda un cambio en un plan, EL SISTEMA le muestra cuántas empresas se verán afectadas y pide confirmación; al confirmar, el cambio aplica de inmediato a todas ellas sin tocar sus ajustes propios.

### UC-TEN-08 Habilitar funcionalidades por empresa (super admin)

- RF-TEN-28: CUANDO el super admin abre "Módulos y funcionalidades" de una empresa, EL SISTEMA muestra el estado de cada funcionalidad: **Incluida en el plan**, **Agregada**, **Quitada** o **No incluida**.
- RF-TEN-29: CUANDO el super admin agrega o quita una funcionalidad a una empresa, EL SISTEMA exige un motivo y acepta una fecha de fin opcional.
- RF-TEN-30: CUANDO vence la fecha de fin de un ajuste, EL SISTEMA deja de aplicarlo y la empresa vuelve a lo que indica su plan, sin intervención manual (RN-TEN-08).
- RF-TEN-31: SI agregar o quitar una funcionalidad rompe una dependencia (p. ej. quitar "Stock y kardex" con "Ventas" habilitada), ENTONCES EL SISTEMA lo rechaza e indica las funcionalidades afectadas (RN-TEN-09).
- RF-TEN-32: CUANDO el super admin va a quitar una funcionalidad que tiene operaciones en curso (p. ej. OP en proceso, comprobantes pendientes), EL SISTEMA le advierte cuántas hay y pide confirmación.
- RF-TEN-33: CUANDO se deshabilita una funcionalidad, EL SISTEMA no borra datos ni roles: sus permisos dejan de ser efectivos y los registros históricos siguen visibles donde corresponda (RN-GEN-11).
- RF-TEN-34: CUANDO el super admin habilita o deshabilita un módulo completo, EL SISTEMA aplica el cambio a todas sus funcionalidades.

### UC-TEN-09 Gestionar roles y permisos (administrador)

- RF-TEN-35: CUANDO un usuario con `core.rol.gestionar` crea, edita, duplica o desactiva un rol, EL SISTEMA muestra la matriz módulo → funcionalidad → permisos con solo las funcionalidades habilitadas; las demás aparecen bloqueadas con "No incluido en tu plan".
- RF-TEN-36: SI se intenta guardar en un rol un permiso de una funcionalidad no habilitada, incluso manipulando el formulario, ENTONCES EL SISTEMA lo rechaza (RN-TEN-11).
- RF-TEN-37: EL SISTEMA no permite editar ni eliminar el rol "Administrador"; ese rol tiene siempre todos los permisos habilitados, incluidos los que se habiliten después.
- RF-TEN-38: SI se intenta eliminar un rol con usuarios asignados, ENTONCES EL SISTEMA lo rechaza y ofrece desactivarlo; al desactivarlo, sus usuarios pierden esos permisos.
- RF-TEN-39: CUANDO un permiso deja de estar habilitado, EL SISTEMA lo conserva en el rol, pero no lo considera efectivo.
- RF-TEN-40: CUANDO cambian las habilitaciones, los roles o las asignaciones de un usuario, EL SISTEMA aplica el cambio desde su siguiente acción, sin cerrar su sesión (RN-TEN-13).
- RF-TEN-41: SI un usuario se queda sin ningún permiso efectivo, ENTONCES EL SISTEMA le permite iniciar sesión y le muestra "No tienes módulos asignados. Contacta al administrador de tu empresa".
- RF-TEN-42: SI una funcionalidad deja de estar disponible mientras un usuario trabaja, ENTONCES EL SISTEMA rechaza su siguiente acción con "Esta funcionalidad ya no está disponible en tu plan" y no guarda la operación.

### UC-TEN-10 Consultar la auditoría de accesos

- RF-TEN-43: CUANDO cambia un rol, sus permisos, la asignación de roles de un usuario o el estado de un usuario, o cuando se crea o revoca un token de API, EL SISTEMA registra quién, cuándo y el valor anterior y el nuevo (RN-TEN-14).
- RF-TEN-44: CUANDO un usuario con `core.auditoria.ver` consulta la auditoría, EL SISTEMA muestra ese historial con filtros; el super admin ve además el historial de habilitaciones de la empresa.

### UC-TEN-11 Gestionar tokens de API

- RF-TEN-45: CUANDO un usuario con `api.token.gestionar` crea un token con nombre, asociado a un usuario técnico (que crea si no existe), EL SISTEMA muestra el token completo **una única vez, en ese momento**, para que se copie; nunca lo guarda en claro y después solo muestra su prefijo, la fecha de creación y el último uso.
- RF-TEN-46: SI la funcionalidad "API de integración" no está habilitada para la empresa, o la empresa está suspendida o con la suscripción vencida, ENTONCES EL SISTEMA rechaza crear tokens y rechaza las llamadas con tokens existentes.
- RF-TEN-47: CUANDO se revoca un token, EL SISTEMA lo invalida de inmediato.
- RF-TEN-54: CUANDO se desactiva un usuario técnico, EL SISTEMA invalida de inmediato todos sus tokens.
- RF-TEN-48: CUANDO llega una llamada con un token válido, EL SISTEMA responde solo con datos de la empresa del token y según los permisos del usuario técnico. Las consultas disponibles en el MVP son stock, pedidos, ventas, productos y estado de resultados, todos paginados.

### Transversales

- RF-TEN-49: EL SISTEMA verifica el permiso de cada acción en el servidor; ocultar el menú o el botón no es suficiente (RN-TEN-12, RN-GEN-10).
- RF-TEN-50: EL SISTEMA muestra en el menú y en los botones solo lo que el usuario puede ejecutar; un módulo aparece si el usuario tiene al menos un permiso de ese módulo.
- RF-TEN-51: MIENTRAS un usuario no tenga `inventario.costo.ver`, EL SISTEMA oculta los costos unitarios y la valorización del inventario en pantallas, exportaciones y API. Los totales del estado de resultados (costo de ventas, márgenes) se rigen por `finanzas.resultados.ver` (spec 008).
- RF-TEN-52: EL SISTEMA nunca muestra ni permite modificar datos de una empresa a usuarios de otra (RN-GEN-01).

## Requisitos no funcionales

- RNF-TEN-01: Las contraseñas se guardan con un hash no reversible; nunca se muestran ni se envían en claro.
- RNF-TEN-02: Los tokens de API se guardan de forma que no se puedan recuperar en claro.
- RNF-TEN-03: La sesión expira por inactividad (tiempo según PRD Q6).
- RNF-TEN-04: Toda la plataforma se sirve solo por HTTPS.
- RNF-TEN-05: El aislamiento entre empresas se verifica con una prueba automática sobre todos los datos y todas las pantallas con identificador; si falla, no se publica la versión.
- RNF-TEN-06: Cada acción del sistema declara su permiso y existe una prueba que verifica que se rechaza sin él.

## Casos límite

- Un doble clic en el registro no crea dos empresas.
- El plan baja por debajo de los usuarios activos actuales: los existentes siguen activos, pero no se pueden crear ni reactivar otros hasta quedar bajo el límite.
- Se quita Producción a una empresa con OP en proceso: las OP quedan en su estado y nadie puede operarlas hasta rehabilitar la funcionalidad. El super admin ve "La empresa tiene 2 OP en proceso" antes de confirmar.
- Un ajuste vence a medianoche (hora de Lima) mientras un usuario trabaja: su siguiente acción se rechaza (RF-TEN-42).
- Un usuario de la empresa A abre por URL un registro de la empresa B: recibe "No encontrado", no "Acceso denegado" (no se revela que existe).

## Fuera de alcance

Impersonación de soporte, 2FA, SSO, cobro online de suscripciones, permisos a nivel de registro ("solo mis ventas", "solo el almacén X"), límites de uso por funcionalidad (N OP/mes), autoservicio para contratar módulos, edición del RUC por soporte.

## Criterios de finalización

- Todos los escenarios de `features/` en verde, incluidos `modulos_funcionalidades.feature` y `roles_permisos.feature`.
- Prueba de aislamiento entre empresas en verde (RNF-TEN-05).
- Prueba de cobertura de autorización en verde para **todas** las acciones de las specs 001–008 (RNF-TEN-06).
- Cada RF-TEN tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **PRD Q6:** tiempo de expiración de la sesión y política de contraseñas; confirmar 5 intentos / 15 minutos de bloqueo (RF-TEN-08).
- [NECESITA ACLARACIÓN] **PRD Q8:** qué funcionalidades y límites incluye cada plan comercial (Gratis, Emprendedor, Negocio), y cuál es el plan de prueba.
- [NECESITA ACLARACIÓN] Wireframes de "Módulos de la empresa" y "Roles y permisos".
