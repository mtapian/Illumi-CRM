# Plan 0002c — Catálogo: categorías y tarifas de ISC

Estado: implementada (2026-10-10)

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/catalog`. Es mayormente CRUD; tiene dominio puro solo para los tipos de producto, las presentaciones y el ISC. Requiere: 0002a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/catalog/domain/isc.py` | Categorías de ISC, tarifa aplicable por fecha, cálculo del ISC por litro | RF-CAT-22 a 27 |
| `src/catalog/domain/errores.py` | `SkuDuplicado`, `CampoInmutable`, `LimiteProductosPlan`, `MaterialNoEsEnvase`, `ContenidoInmutable`, `IscSinTarifaVigente`… | todos los `SI … ENTONCES` |
| `src/catalog/application/isc.py` | `CrearCategoriaIsc`, `AgregarTarifaIsc`, `DesactivarCategoriaIsc` | RF-CAT-22 a 24, 28 |
| `src/catalog/application/fachada.py` | `CatalogoQuery` público: `producto()`, `presentacion()`, `activos(tipo)`, `isc_aplicable(producto, fecha)`, `materiales_para()` | RF-CAT-25, 27 |
| `src/catalog/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios filtrados por tenant | §2 |
| `src/catalog/interfaces/views/*.py` + `templates/catalog/*.html` | Pantallas de §5 | RF-CAT-22 a 28 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `catalog_isc_categoria` | empresa_id, nombre, sistema (`ESPECIFICO`), codigo_tributo (`2000`), codigo_tipo_sistema, activo | UNIQUE(empresa_id, nombre); `CHECK sistema = 'ESPECIFICO'` | RF-CAT-22, 23, 28 |
| `catalog_isc_tarifa` | categoria_id, vigente_desde `DATE`, monto_por_litro `NUMERIC(10,4)`, creado_por | UNIQUE(categoria_id, vigente_desde); `CHECK > 0`; solo inserción (trigger) | RF-CAT-24, 25 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `validar_producto(datos, tipo)` | Unidad litros en `GRANEL`, precio en vendibles, vida útil en `TERMINADO`, contenido si el ISC es por litro | RF-CAT-26 |
| `tarifa_aplicable(tarifas, fecha) -> Tarifa \| None` | La de mayor `vigente_desde ≤ fecha` | RF-CAT-24, 25 |
| `isc_linea(cantidad, contenido_l, tarifa) -> Decimal` | `round(cantidad × contenido × monto_por_litro, 2)`; 0 sin categoría | RF-CAT-25, 27 |

## 4. Algoritmos clave

**ISC aplicable a una línea** (RF-CAT-25 a 27):

```
isc_aplicable(producto, fecha):
  si producto.isc_categoria is None → None                         # RF-CAT-27
  contenido = presentacion(producto).contenido si TERMINADO, si no producto.contenido_litros
  tarifa = tarifa_aplicable(tarifas(categoria), fecha)
  si tarifa is None → IscSinTarifaVigente(categoria, fecha)
  devolver IscDTO(monto_por_litro, contenido, codigo_tributo, codigo_tipo_sistema)
```

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/catalogo/isc/` | Categorías con su historial de tarifas (tabla por fecha; solo "Agregar tarifa") | RF-CAT-22 a 24, 28 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Tarifas de ISC inmutables con vigencia | Editar el monto vigente | Constitución art. 5.1; los comprobantes emitidos no cambian |
| ISC configurado en el catálogo (por empresa) | En la configuración de facturación | Es un atributo del producto; la facturación solo recibe importes (0000 §2) |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/catalog tests/acceptance -k "E02c"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/catalog/unit/test_isc.py` | Tarifa el día antes, el día de inicio y después del cambio; sin categoría ⇒ 0; 24 × 0,33 L × 2,51 = 19,88 | RF-CAT-23 a 27 |
| Caso de uso | `tests/catalog/usecases/test_isc.py` | Crear categoría con primera tarifa, agregar tarifa, no editar, desactivar en uso | RF-CAT-22, 24, 28 |
| Integración | `tests/catalog/integration/test_constraints.py` | SKU único por empresa; trigger de tarifas inmutables | RF-CAT-08, 24 |
| Aceptación | `features/presentaciones.feature`, `features/productos.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-CAT-22, RF-CAT-23, RF-CAT-24, RF-CAT-25, RF-CAT-26, RF-CAT-27, RF-CAT-28 | §1 `isc.py` · §2 tablas ISC · §3 `tarifa_aplicable`, `isc_linea` · §4 ISC aplicable · §5 `/catalogo/isc/` · §7 `test_isc.py` |

## 9. Dependencias de dudas abiertas

- **Código de tipo de sistema ISC:** es un dato de la categoría; no cambia el código.
