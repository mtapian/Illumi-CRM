# Plan 0008a — Finanzas: gastos operativos

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/finance`. Registra gastos y **lee** ventas, inventario, producción y facturación para el estado de resultados, el dashboard y las exportaciones. No modifica datos de otros contextos. Requiere: 0001a, 0004a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/finance/domain/gasto.py` | Agregado `Gasto`: gasto del período según el documento, validaciones | RF-FIN-01 a 04 |
| `src/finance/domain/errores.py` | `FechaFutura`, `ImporteInvalido`, `RangoInvalido`, `EstadoInvalido` | todos los `SI … ENTONCES` |
| `src/finance/application/gastos.py` | `RegistrarGasto`, `AnularGasto`, categorías | RF-FIN-01 a 05 |
| `src/finance/infrastructure/models.py`, `repositorios.py` | Modelos, repositorios y modelos `managed=False` de las vistas (con filtro de empresa) | §2 |
| `src/finance/interfaces/views/*.py` + `templates/finance/*.html` | Pantallas de §5 | RF-FIN-01 a 05 |
| `src/finance/interfaces/api.py` | `GET /api/v1/estado-resultados` | RNF-FIN-01 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `finance_categoria_gasto` | empresa_id, nombre, es_de_planta, activo | UNIQUE(empresa_id, nombre) | RF-FIN-03, 04 |
| `finance_gasto` | empresa_id, numero, fecha `DATE`, categoria_id, descripcion, proveedor_id null, doc_tipo, doc_numero, base, igv, total, gasto_periodo, estado (`REGISTRADO`/`ANULADO`), anulado_por, anulado_en, motivo_anulacion | UNIQUE(empresa_id, numero); `CHECK total = base + igv`; `CHECK total > 0` | RF-FIN-01, 02, 05 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `gasto_del_periodo(doc_tipo, base, igv) -> Money` | Factura ⇒ base; boleta o sin documento ⇒ total; recibo por honorarios ⇒ bruto | RF-FIN-01 |
| `validar_gasto(fecha, total, hoy)` | Fecha no futura e importe > 0 | RF-FIN-02 |
| `advertir_planta(categoria) -> bool` | Categoría marcada "de planta" | RF-FIN-04 |

## 4. Algoritmo clave: estado de resultados

Sin algoritmos no triviales: la lógica está en las funciones puras de §3.

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/finanzas/gastos/` | Listado y formulario: base e IGV solo con factura; advertencia en categorías de planta; anular con motivo | RF-FIN-01 a 05 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Anulación de gastos y ventas en el período de la anulación | Recalcular el período original | Un período revisado no cambia por un hecho posterior |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/finance tests/acceptance -k "E08a"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/finance/unit/test_gasto.py` | Gasto del período por tipo de documento; fecha futura; importe; categoría de planta | RF-FIN-01 a 04 |
| Integración | `tests/finance/integration/test_estado_resultados.py` | Escenario de la spec (1400,00 → 253,33; 53,81 % / 18,10 %); costo congelado; anulación en otro mes; saldo inicial y transferencia fuera; gratuitas 686,18 en gastos; gasto anulado en otro mes | RF-FIN-05 a 10 |
| Aceptación | `features/gastos_resultados.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-FIN-01, RF-FIN-02, RF-FIN-03, RF-FIN-04, RF-FIN-05 | §1 `gasto.py`, `gastos.py` · §2 `finance_gasto` · §3 `gasto_del_periodo`, `validar_gasto`, `advertir_planta` · §4 (gastos) · §5 `/finanzas/gastos/` · §7 |

## 9. Dependencias de dudas abiertas

- **Q12 (costo indirecto vs. gastos de planta):** hoy solo hay una advertencia (RF-FIN-04).
