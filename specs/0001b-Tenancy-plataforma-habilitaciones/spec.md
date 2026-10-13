# Spec 0001b — Plataforma: planes y habilitaciones

Estado: implementada (2026-10-10)

Épica E01 (Tenancy y accesos), parte 2 de 4. Depende de: 0001a. La usan: 0001c, 0001d y 002–008 (catálogo de permisos).

## Contexto y objetivo

La plataforma necesita **decidir qué módulos y funcionalidades contrata cada empresa**: empaquetarlos en planes, activar y suspender suscripciones, y hacer excepciones por empresa sin cambiar su plan.

**Alcance (decisión del PO, 2026-10-10, PRD Q11):** esta spec entra completa en S0, incluidos planes, ajustes con vigencia y vista previa de impacto, aunque al inicio haya un solo cliente. Es una excepción aprobada al principio de simplicidad (constitución, art. 7.6), porque el modelo comercial por planes es parte del producto desde el lanzamiento.

**Objetivo:** que el super admin controle lo que cada empresa tiene habilitado, con vigencia y sin borrar datos.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Super admin (plataforma) | Activa planes, define qué incluye cada plan, habilita o quita funcionalidades por empresa |

## Historias de usuario

- H1: Como super admin, quiero activar, suspender y reactivar planes de una empresa para administrar las suscripciones.
- H2: Como super admin, quiero definir qué funcionalidades incluye cada plan para empaquetar la oferta comercial.
- H3: Como super admin, quiero agregar o quitar funcionalidades a una empresa concreta, con vigencia opcional, para dar pruebas o hacer excepciones sin cambiar su plan.

## Definiciones

- **Módulo:** área del sistema que aparece en el menú (Inventario, Producción…).
- **Funcionalidad:** capacidad comercializable dentro de un módulo (p. ej. "Órdenes de producción"). Es lo que habilita el super admin.
- **Permiso:** acción concreta (p. ej. `ventas.venta.anular`). Es lo que el administrador de la empresa asigna a sus roles (spec 0001c).
- **Habilitaciones de una empresa:** funcionalidades de su plan + las agregadas a esa empresa − las quitadas a esa empresa, considerando solo los ajustes vigentes. CORE siempre está habilitado.
- **Ajuste vigente:** ajuste sin fecha de fin, o con fecha de fin igual o posterior a hoy (hora de Lima).
- **Operación en curso:** registro de otra spec que quedaría sin poder operarse si se quita la funcionalidad (p. ej. OP en proceso, comprobantes pendientes). Cada spec define cuáles son las suyas.

### Modelo de acceso en 3 niveles

```
NIVEL 1 · PLATAFORMA (super admin, esta spec)
  Catálogo:  Módulo ─┬─ Funcionalidad ─┬─ Permiso (acción)
  Plan  ──► funcionalidades incluidas
  Empresa ──► habilitaciones = plan ± ajustes por empresa (vigencia opcional)

NIVEL 2 · EMPRESA (administrador, spec 0001c)
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
| **PRODUCCION** | Órdenes de producción | `produccion.op.ver`, `produccion.op.planificar`, `produccion.op.ejecutar`, `produccion.op.anular`, `produccion.reporte.ver` | Stock y kardex *(0005a, 2026-10-12: se retiran "Recetas", que pasa al catálogo, y "Envasado multipresentación", que es una OP)* |
| **VENTAS** | Clientes | `ventas.cliente.ver`, `ventas.cliente.gestionar` | CATALOGO |
| | Pedidos | `ventas.pedido.ver`, `ventas.pedido.gestionar`, `ventas.pedido.cancelar` | Clientes, INVENTARIO |
| | Ventas | `ventas.venta.ver`, `ventas.venta.registrar`, `ventas.venta.anular` | Clientes, INVENTARIO |
| **FACTURACION** | Facturación electrónica | `facturacion.config.gestionar`, `facturacion.comprobante.ver`, `facturacion.comprobante.gestionar` | Ventas |
| **FINANZAS** | Gastos | `finanzas.gasto.ver`, `finanzas.gasto.registrar`, `finanzas.gasto.anular` | CORE |
| | Estado de resultados | `finanzas.resultados.ver` | Ventas |
| **TRANSVERSAL** | Exportación CSV | `reportes.exportar` | — |
| | API de integración | `api.token.gestionar` | — |

`inventario.costo.ver` controla si el usuario ve costos y valorizaciones en cualquier pantalla, exportación o respuesta de la API.

## Requisitos funcionales (criterios de aceptación en EARS)

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

## Requisitos no funcionales

- Ninguno propio; aplican los de 0001a y 0001c.

## Casos límite

- Se quita Producción a una empresa con OP en proceso: las OP quedan en su estado y nadie puede operarlas hasta rehabilitar la funcionalidad. El super admin ve "La empresa tiene 2 OP en proceso" antes de confirmar.
- Un ajuste vence a medianoche (hora de Lima) mientras un usuario trabaja: su siguiente acción se rechaza (spec 0001c, RF-TEN-42).
- El plan baja su límite de usuarios por debajo de los activos de una empresa: ver spec 0001c, "Casos límite".

## Fuera de alcance

Límites de uso por funcionalidad (N OP/mes), autoservicio para contratar módulos, cobro online de suscripciones.

## Criterios de finalización

- Escenarios de `features/` en verde, incluido `modulos_funcionalidades.feature`.
- Cada RF-TEN de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- **PRD Q8 (resuelta por el PO con el valor por defecto, 2026-10-10):** el plan de prueba incluye todas las funcionalidades y no tiene límites; el contenido de los planes comerciales es un dato que carga el super admin.
- [NECESITA ACLARACIÓN] Wireframe de "Módulos de la empresa".
