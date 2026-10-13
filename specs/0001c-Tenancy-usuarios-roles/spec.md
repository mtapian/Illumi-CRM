# Spec 0001c — Usuarios, roles y permisos

Estado: implementada (2026-10-10)

Épica E01 (Tenancy y accesos), parte 3 de 4. Depende de: 0001a, 0001b. La usan: 0001d y 002–008 (cada caso de uso declara su permiso).

## Contexto y objetivo

Cada empresa necesita **decidir qué puede hacer cada uno de sus usuarios** dentro de lo que contrató, sin depender de roles fijos, y con la garantía de que nunca ve datos de otra empresa.

**Objetivo:** que el acceso de cada usuario sea exactamente el que su empresa le dio dentro de lo que la plataforma le habilitó, verificado en el servidor en cada acción.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Administrador de la empresa | Gestiona usuarios y roles |
| Usuario de la empresa | Opera según sus permisos efectivos |

## Historias de usuario

- H1: Como administrador, quiero crear usuarios y asignarles uno o más roles para que cada persona haga solo lo que le corresponde.
- H2: Como administrador, quiero crear roles propios combinando permisos para adaptar el sistema a cómo se organiza mi empresa.
- H3: Como usuario, quiero ver en el menú solo lo que puedo hacer, para no encontrarme con opciones que me rechazan.

## Definiciones

- **Módulo, funcionalidad, permiso, habilitaciones y catálogo:** ver spec 0001b, "Definiciones".
- **Permisos efectivos de un usuario:** (unión de los permisos de sus roles activos) ∩ (permisos de las funcionalidades habilitadas). El rol de sistema "Administrador" equivale a todos los permisos habilitados (RN-TEN-10).

### Plantillas de rol iniciales

Se crean como roles **editables** al registrar la empresa (spec 0001a, RF-TEN-01), solo con los permisos de las funcionalidades habilitadas en ese momento. "Administrador" es un rol de sistema y no se edita.

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
| Producción: órdenes de producción (0005a; la receta está en el catálogo y el envasado es una OP) | ✔ | ✔ | ✔ (sin anular OP) | — | — |
| `produccion.op.anular` | ✔ | ✔ | — | — | — |
| Ventas: clientes, pedidos, registrar venta | ✔ | ✔ | — | — | ✔ |
| `ventas.venta.anular` | ✔ | ✔ | — | — | — |
| Cobranzas: ver / registrar pagos (0006b) | ✔ | ✔ | — | — | ✔ |
| `ventas.cobranza.anular`, `ventas.metodo_pago.gestionar` (0006b, segregación de funciones) | ✔ | ✔ | — | — | — |
| Facturación: ver / gestionar comprobantes | ✔ | ✔ | — | — | ver |
| `facturacion.config.gestionar` | ✔ | — | — | — | — |
| Finanzas: gastos y estado de resultados | ✔ | ✔ | — | — | — |
| `reportes.exportar` | ✔ | ✔ | ✔ | ✔ | — |

En las demás specs (002–008), las menciones a roles ("solo admin/gerente") se refieren a estas plantillas. La regla real es siempre el **permiso** de cada caso de uso.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-TEN-03 Gestionar usuarios

- RF-TEN-10: CUANDO un usuario con `core.usuario.gestionar` crea, edita, activa o desactiva un usuario de su empresa, EL SISTEMA guarda el cambio y permite asignarle uno o más roles.
- RF-TEN-11: SI crear o reactivar un usuario supera el límite de usuarios activos del plan, ENTONCES EL SISTEMA lo rechaza (RN-TEN-04). Los usuarios técnicos (spec 0001d) no cuentan. Un límite vacío significa ilimitado.
- RF-TEN-12: SI un cambio deja a la empresa sin ningún usuario activo con el rol "Administrador", ENTONCES EL SISTEMA lo rechaza, incluso si dos administradores se desactivan entre sí al mismo tiempo (RN-TEN-05).
- RF-TEN-53: SI un usuario intenta asignar a otro, o a sí mismo, un rol o un permiso que él mismo no tiene, ENTONCES EL SISTEMA lo rechaza. Solo un usuario con el rol "Administrador" puede asignar ese rol.
- RF-TEN-13: EL SISTEMA nunca borra usuarios: los desactiva y conserva la autoría de sus documentos.
- RF-TEN-14: CUANDO se abre la ficha de un usuario, EL SISTEMA muestra sus permisos efectivos agrupados por módulo, de qué rol viene cada uno y cuáles no están disponibles por el plan.

### UC-TEN-09 Gestionar roles y permisos (administrador)

- RF-TEN-35: CUANDO un usuario con `core.rol.gestionar` crea, edita, duplica o desactiva un rol, EL SISTEMA muestra la matriz módulo → funcionalidad → permisos con solo las funcionalidades habilitadas; las demás aparecen bloqueadas con "No incluido en tu plan".
- RF-TEN-36: SI se intenta guardar en un rol un permiso de una funcionalidad no habilitada, incluso manipulando el formulario, ENTONCES EL SISTEMA lo rechaza (RN-TEN-11).
- RF-TEN-37: EL SISTEMA no permite editar ni eliminar el rol "Administrador"; ese rol tiene siempre todos los permisos habilitados, incluidos los que se habiliten después.
- RF-TEN-38: SI se intenta eliminar un rol con usuarios asignados, ENTONCES EL SISTEMA lo rechaza y ofrece desactivarlo; al desactivarlo, sus usuarios pierden esos permisos.
- RF-TEN-39: CUANDO un permiso deja de estar habilitado, EL SISTEMA lo conserva en el rol, pero no lo considera efectivo.
- RF-TEN-40: CUANDO cambian las habilitaciones, los roles o las asignaciones de un usuario, EL SISTEMA aplica el cambio desde su siguiente acción, sin cerrar su sesión (RN-TEN-13).
- RF-TEN-41: SI un usuario se queda sin ningún permiso efectivo, ENTONCES EL SISTEMA le permite iniciar sesión y le muestra "No tienes módulos asignados. Contacta al administrador de tu empresa".
- RF-TEN-42: SI una funcionalidad deja de estar disponible mientras un usuario trabaja, ENTONCES EL SISTEMA rechaza su siguiente acción con "Esta funcionalidad ya no está disponible en tu plan" y no guarda la operación.

### Transversales

- RF-TEN-49: EL SISTEMA verifica el permiso de cada acción en el servidor; ocultar el menú o el botón no es suficiente (RN-TEN-12, RN-GEN-10).
- RF-TEN-50: EL SISTEMA muestra en el menú y en los botones solo lo que el usuario puede ejecutar; un módulo aparece si el usuario tiene al menos un permiso de ese módulo.
- RF-TEN-51: MIENTRAS un usuario no tenga `inventario.costo.ver`, EL SISTEMA oculta los costos unitarios y la valorización del inventario en pantallas, exportaciones y API. Los totales del estado de resultados (costo de ventas, márgenes) se rigen por `finanzas.resultados.ver` (épica 0008).
- RF-TEN-52: EL SISTEMA nunca muestra ni permite modificar datos de una empresa a usuarios de otra (RN-GEN-01).

## Requisitos no funcionales

- RNF-TEN-05: El aislamiento entre empresas se verifica con una prueba automática sobre todos los datos y todas las pantallas con identificador; si falla, no se publica la versión.
- RNF-TEN-06: Cada acción del sistema declara su permiso y existe una prueba que verifica que se rechaza sin él.

## Casos límite

- El plan baja por debajo de los usuarios activos actuales: los existentes siguen activos, pero no se pueden crear ni reactivar otros hasta quedar bajo el límite.
- Un usuario de la empresa A abre por URL un registro de la empresa B: recibe "No encontrado", no "Acceso denegado" (no se revela que existe).
- Un usuario con `core.rol.gestionar` pero sin `ventas.venta.anular` intenta dárselo a otro rol: se rechaza (RF-TEN-53).

## Fuera de alcance

Permisos a nivel de registro ("solo mis ventas", "solo el almacén X"), impersonación de soporte.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Prueba de aislamiento entre empresas en verde (RNF-TEN-05).
- Prueba de cobertura de autorización en verde para **todas** las acciones de las épicas 0001–0008 (RNF-TEN-06).
- Cada RF-TEN de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] Wireframe de "Roles y permisos".
