# Plan 0002b — Catálogo: presentaciones y materiales

Estado: implementada (2026-10-10)

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/catalog`. Es mayormente CRUD; tiene dominio puro solo para los tipos de producto, las presentaciones y el ISC. Requiere: 0002a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/catalog/domain/presentacion.py` | Validación de la presentación y `materiales_para(unidades)` | RF-CAT-15 a 18 |
| `src/catalog/domain/errores.py` | `SkuDuplicado`, `CampoInmutable`, `LimiteProductosPlan`, `MaterialNoEsEnvase`, `ContenidoInmutable`, `IscSinTarifaVigente`… | todos los `SI … ENTONCES` |
| `src/catalog/application/presentaciones.py` | `DefinirPresentacion` | RF-CAT-15 a 18 |
| `src/catalog/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios filtrados por tenant | §2 |
| `src/catalog/interfaces/views/*.py` + `templates/catalog/*.html` | Pantallas de §5 | RF-CAT-15 a 18 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `catalog_presentacion` | empresa_id, producto_id (TERMINADO), granel_id, contenido_litros `NUMERIC(10,4)` | UNIQUE(producto_id); `CHECK contenido_litros > 0` | RF-CAT-15, 17, 18 |
| `catalog_presentacion_material` | presentacion_id, material_id (ENVASE), cantidad_por_unidad `NUMERIC(14,4)` | UNIQUE(presentacion_id, material_id); `CHECK > 0` | RF-CAT-16 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `validar_presentacion(granel, contenido, materiales)` | Granel activo, contenido > 0, ≥ 1 material `ENVASE` con cantidad > 0 | RF-CAT-15, 16 |
| `materiales_para(presentacion, unidades) -> dict` | Material → cantidad (4 decimales); la usa la épica 0005 | RF-CAT-16 |

## 4. Algoritmos clave

**Editar una presentación** (RF-CAT-18):

```
si cambia contenido_litros y InventarioConsultaPort.tiene_movimientos(producto) → ContenidoInmutable
si cambian materiales → se guardan; aplican a envasados futuros (el costo existente no se toca)
```

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/catalogo/productos/nuevo?tipo=` | Formulario que muestra solo los campos del tipo; para `TERMINADO`, formset de materiales; para `MERCADERIA`, precio, ISC, contenido y "controla lote" | RF-CAT-15, 16 |
| `/catalogo/productos/<id>` | Ficha; campos bloqueados con candado si hay movimientos; botones desactivar y eliminar según RF | RF-CAT-18 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Contenido de la presentación inmutable con movimientos | Permitir cambiarlo | El contenido define el ISC de unidades ya envasadas (RF-CAT-18) |
| Fracción de caja (0,0417) aceptada | Materiales "por empaque" | Simplicidad en el MVP (art. 7.6); queda como fuera de alcance |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/catalog tests/acceptance -k "E02b"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/catalog/unit/test_presentacion.py` | Validaciones; `materiales_para(240)` = 240 botellas, 10,008 cajas | RF-CAT-15 a 17 |
| Caso de uso | `tests/catalog/usecases/test_presentacion_edicion.py` | Contenido inmutable con movimientos; materiales editables | RF-CAT-18 |
| Aceptación | `features/presentaciones.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-CAT-15, RF-CAT-16, RF-CAT-17, RF-CAT-18 | §1 `presentacion.py` · §3 `validar_presentacion`, `materiales_para` · §4 editar presentación · §7 |

## 9. Dependencias de dudas abiertas

- Ninguna.
