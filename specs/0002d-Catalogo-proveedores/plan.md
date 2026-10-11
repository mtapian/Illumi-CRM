# Plan 0002d — Catálogo: proveedores y proveedores del producto

Estado: borrador (2026-10-10)

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto nuevo: `src/purchasing` (compras). En esta spec solo tiene proveedores; las compras llegan con 0004a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/shared/domain/documentos.py` | Se mueve `Ruc` desde `tenancy/domain/ruc.py` (lo usan tenancy y compras) y se agrega la validación de DNI (8 dígitos) | RF-COM-01 |
| `src/purchasing/domain/proveedor.py` | `validar_proveedor()`, `validar_proveedor_producto()` | RF-COM-01, 21 |
| `src/purchasing/application/proveedores.py` | `CrearProveedor`, `EditarProveedor`, `CambiarEstadoProveedor`, `EliminarProveedor`, `AsociarProveedorProducto`, `QuitarProveedorProducto` (todos `compras.proveedor.gestionar`) | RF-COM-01 a 03, 21, 22 |
| `src/purchasing/application/puertos.py` | `ComprasPort.tiene_compras(proveedor_id)`: falso hasta que 0004a lo implemente | RF-COM-02 |
| `src/purchasing/infrastructure/models.py` | Modelos de §2 | §2 |
| `src/purchasing/interfaces/` | `/compras/proveedores/` y la pestaña "Compras" registrada en `catalog/interfaces/pestanas.py` | RF-COM-01 a 03, 22 |
| `pyproject.toml` | Contratos: `catalog` y `tenancy` no importan `purchasing`; `purchasing.domain/application` no importan infraestructura ni interfaces de otros contextos | — |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `purchasing_proveedor` | empresa_id, tipo_doc (`RUC`/`DNI`), num_doc, razon_social, contacto, telefono, email, direccion, activo | UNIQUE(empresa_id, tipo_doc, num_doc) | RF-COM-01 a 03 |
| `purchasing_proveedor_producto` | empresa_id, proveedor_id, producto_id, precio_referencial `NUMERIC(14,2)`, plazo_entrega_dias, codigo_proveedor | UNIQUE(proveedor_id, producto_id); `CHECK precio ≥ 0 AND plazo ≥ 0` | RF-COM-21, 22 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `validar_documento(tipo, numero)` | RUC con módulo 11 (`Ruc`), DNI de 8 dígitos | RF-COM-01 |
| `validar_proveedor_producto(tipo_producto, precio, plazo)` | Solo comprables; precio y plazo ≥ 0 | RF-COM-21 |

## 4. Algoritmos clave

Sin algoritmos no triviales. Asociar es "crear o actualizar" por (proveedor, producto).

## 5. Interfaz

**Referencia visual del PO (2026-10-10):** listado "Proveedores" con el patrón "listado de maestro" del ADR-12: migas Inicio / Compras / Proveedores, buscador por nombre o RUC, botón "+ Nuevo proveedor", columnas nombre, RUC, contacto, teléfono, estado y acciones (lápiz, tacho o desactivar si tiene compras).

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/compras/proveedores/` | Listado con búsqueda; alta y edición; activar/desactivar; eliminar si no tiene compras | RF-COM-01 a 03 |
| Ficha de producto, pestaña "Compras" | Tabla proveedor · precio referencial · plazo · código; agregar y quitar (como la pestaña Compras de Odoo) | RF-COM-21, 22 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Proveedores en el contexto `purchasing`, adelantado | Ponerlos en `catalog` | El dueño natural es compras; 0004a solo agrega las compras sin mover tablas |
| Pestaña "Compras" registrada por `purchasing` en la ficha | Que el catálogo consulte a compras | El catálogo es de una capa inferior y no conoce a compras (contratos de import-linter) |
| `Ruc` en `shared/domain` | Que compras importe `tenancy.domain` | Un contexto usa a otro solo por su fachada (art. 7.2) |

## 7. Estrategia de tests (pytest)

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/purchasing/unit/test_proveedor.py` | RUC y DNI, comprables, precio y plazo | RF-COM-01, 21 |
| Caso de uso | `tests/purchasing/usecases/test_proveedores.py` | Duplicado por empresa, eliminar con compras (puerto falso), desactivado no se asocia, asociar = crear o actualizar | RF-COM-01 a 03, 21 |
| Integración | `tests/purchasing/integration/test_pantallas.py` | Pestaña Compras solo en comprables; permisos | RF-COM-22 |
| Meta | `tests/meta/test_aislamiento.py`, `test_autorizacion.py` | Rutas con `<int:…>` y casos de uso nuevos | RF-TEN-49, 52 |
| Aceptación | `features/proveedores.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-COM-01, 02, 03 | §1 `proveedores.py`, `documentos.py` · §2 `purchasing_proveedor` · §5 `/compras/proveedores/` · §7 |
| RF-COM-21, 22 | §1 `proveedores.py` · §2 `purchasing_proveedor_producto` · §5 pestaña Compras · §7 |
