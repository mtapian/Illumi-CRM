# Plan 0008b — Finanzas: estado de resultados, dashboard y exportación

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/finance`. Registra gastos y **lee** ventas, inventario, producción y facturación para el estado de resultados, el dashboard y las exportaciones. No modifica datos de otros contextos. Requiere: 0008a, 0006b, 0006c, 0003a, 0005b.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/finance/domain/periodo.py` | Períodos en hora de Lima, período anterior, márgenes sin división por cero | RF-FIN-06, 13 |
| `src/finance/domain/errores.py` | `FechaFutura`, `ImporteInvalido`, `RangoInvalido`, `EstadoInvalido` | todos los `SI … ENTONCES` |
| `src/finance/application/resultados.py` | `EstadoResultadosQuery(desde, hasta, comparar)`, `DetalleLineaQuery`, `IndicadoresQuery`, `PendientesTributariosQuery` | RF-FIN-06 a 13 |
| `src/finance/application/dashboard.py` | `DashboardQuery(actor)`: compone avisos según permisos | RF-FIN-14 |
| `src/shared/application/csv.py` | Exportación CSV común (UTF-8 con BOM, coma, punto decimal, filtros, columnas de costo según permiso); la usan todas las specs | RF-FIN-15, 16 |
| `src/finance/infrastructure/sql/fn_estado_resultados.sql`, `vw_er_*.sql` | Función única del estado de resultados y vistas de detalle | RF-FIN-06 a 12 |
| `src/finance/infrastructure/models.py`, `repositorios.py` | Modelos, repositorios y modelos `managed=False` de las vistas (con filtro de empresa) | §2 |
| `src/finance/interfaces/views/*.py` + `templates/finance/*.html` | Pantallas de §5 | RF-FIN-06 a 16 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `mes_actual(hoy) -> (desde, hasta)` | Período por defecto | RF-FIN-06 |
| `periodo_anterior(desde, hasta) -> (desde, hasta)` | Mismo largo, inmediatamente antes | RF-FIN-06 |
| `margen(utilidad, ventas_netas) -> Decimal \| None` | `None` (se pinta "—") si no hay ventas | RF-FIN-13 |
| `avisos_visibles(permisos) -> list` | Tabla aviso → permiso de la spec | RF-FIN-14 |
| `columnas_exportables(reporte, permisos) -> list` | Quita costos unitarios y valorización sin `inventario.costo.ver` | RF-FIN-16 |

## 4. Algoritmo clave: estado de resultados

Una sola función SQL es la fuente para la pantalla, el CSV y la API (RNF-FIN-01). La lógica de negocio que la alimenta (costo congelado, gasto del período, gratuitas) ya está calculada por cada contexto; la función solo suma por período. Implementa RF-FIN-06 a 10:

- **Ventas netas y costo de ventas:** ventas por fecha de emisión menos anuladas por fecha de anulación; el costo de las anuladas solo se resta si hubo reingreso (RF-FIN-07, 08).

- **Mermas y ajustes:** sin `SALDO_INICIAL` ni `TRANSFERENCIA` (RF-FIN-09).

- **Entregas gratuitas:** fuera de ventas y costo, dentro de gastos operativos (RF-FIN-10).

- **Gastos:** suman por su fecha y su anulación resta en el período en que se anula (spec RF-FIN-05).

```sql
CREATE OR REPLACE FUNCTION fn_estado_resultados(
    p_empresa BIGINT, p_desde DATE, p_hasta DATE
) RETURNS TABLE (
    ventas_netas        NUMERIC(14,2),
    costo_ventas        NUMERIC(14,2),
    mermas_ajustes      NUMERIC(14,2),
    perdidas_produccion NUMERIC(14,2),
    utilidad_bruta      NUMERIC(14,2),
    gastos_operativos   NUMERIC(14,2),   -- incluye gastos_gratuitas
    gastos_gratuitas    NUMERIC(14,2),
    utilidad_operativa  NUMERIC(14,2),
    margen_bruto_pct    NUMERIC(7,2),
    margen_operativo_pct NUMERIC(7,2)
)
LANGUAGE sql STABLE AS $$
WITH
emitidas AS (            -- ventas emitidas en el período (incluye las luego anuladas)
    SELECT COALESCE(SUM(l.valor_venta), 0) AS valor,
           COALESCE(SUM(l.costo_total) FILTER (WHERE NOT l.es_gratuita), 0) AS costo,
           COALESCE(SUM(l.costo_total + l.tributos_asumidos) FILTER (WHERE l.es_gratuita), 0) AS gratuitas
    FROM sales_venta v
    JOIN sales_venta_linea l ON l.venta_id = v.id
    WHERE v.empresa_id = p_empresa
      AND v.fecha_emision BETWEEN p_desde AND p_hasta
),
anuladas AS (            -- RN-FIN-03: restan en el período de anulación
    SELECT COALESCE(SUM(l.valor_venta), 0) AS valor,
           COALESCE(SUM(l.costo_total) FILTER (WHERE v.reingresa_mercaderia AND NOT l.es_gratuita), 0) AS costo,
           COALESCE(SUM(l.tributos_asumidos + CASE WHEN v.reingresa_mercaderia THEN l.costo_total ELSE 0 END)
                    FILTER (WHERE l.es_gratuita), 0) AS gratuitas
    FROM sales_venta v
    JOIN sales_venta_linea l ON l.venta_id = v.id
    WHERE v.empresa_id = p_empresa
      AND v.estado = 'ANULADA'
      AND (v.anulado_en AT TIME ZONE 'America/Lima')::date BETWEEN p_desde AND p_hasta
),
ajustes AS (             -- ajustes (excepto saldo inicial y transferencias) + mermas de OP y de envasado
    SELECT COALESCE(SUM(CASE WHEN m.tipo = 'SALIDA' THEN m.costo_total ELSE -m.costo_total END), 0) AS neto
    FROM inventory_movimiento m
    LEFT JOIN inventory_ajuste a ON m.ref_tipo = 'AJUSTE' AND a.id = m.ref_id
    WHERE m.empresa_id = p_empresa
      AND (m.fecha AT TIME ZONE 'America/Lima')::date BETWEEN p_desde AND p_hasta
      AND (
            (m.ref_tipo = 'AJUSTE' AND a.tipo NOT IN ('SALDO_INICIAL', 'TRANSFERENCIA'))  -- RN-FIN-04 (incluye sus anulaciones)
         OR (m.ref_tipo IN ('OP', 'ENVASADO') AND m.motivo = 'MERMA')     -- cierre con saldo y descarte de envasado
      )
),
perdidas AS (
    SELECT COALESCE(SUM(op.costo_total), 0) AS total
    FROM production_op op
    WHERE op.empresa_id = p_empresa
      AND op.perdida_produccion
      AND op.fecha_fin BETWEEN p_desde AND p_hasta
),
gastos AS (               -- RF-FIN-05: el gasto suma por su fecha y su anulación resta en el período en que se anula
    SELECT COALESCE(SUM(g.gasto_periodo) FILTER (WHERE g.fecha BETWEEN p_desde AND p_hasta), 0)
         - COALESCE(SUM(g.gasto_periodo) FILTER (WHERE g.estado = 'ANULADO'
                    AND (g.anulado_en AT TIME ZONE 'America/Lima')::date BETWEEN p_desde AND p_hasta), 0) AS total
    FROM finance_gasto g
    WHERE g.empresa_id = p_empresa
),
r AS (
    SELECT e.valor - an.valor                                   AS ventas_netas,
           e.costo - an.costo                                   AS costo_ventas,
           aj.neto                                              AS mermas_ajustes,
           p.total                                              AS perdidas_produccion,
           (e.valor - an.valor) - (e.costo - an.costo) - aj.neto - p.total AS utilidad_bruta,
           g.total + (e.gratuitas - an.gratuitas)               AS gastos_operativos,  -- RN-FIN-07
           e.gratuitas - an.gratuitas                           AS gastos_gratuitas
    FROM emitidas e, anuladas an, ajustes aj, perdidas p, gastos g
)
SELECT ventas_netas,
       costo_ventas,
       mermas_ajustes,
       perdidas_produccion,
       utilidad_bruta,
       gastos_operativos,
       gastos_gratuitas,
       utilidad_bruta - gastos_operativos,
       CASE WHEN ventas_netas = 0 THEN NULL
            ELSE ROUND(utilidad_bruta * 100 / ventas_netas, 2) END,
       CASE WHEN ventas_netas = 0 THEN NULL
            ELSE ROUND((utilidad_bruta - gastos_operativos) * 100 / ventas_netas, 2) END
FROM r;
$$;
```

**Detalle por línea** (RF-FIN-11): vistas `vw_er_ventas`, `vw_er_ajustes`, `vw_er_perdidas`, `vw_er_gastos` y `vw_er_gratuitas` con los mismos filtros, de modo que el detalle suma exactamente lo mismo que la línea.

**Pendientes tributarios** (RF-FIN-12): ventas anuladas con NC sin aceptar y ventas con comprobante `RECHAZADO` sin reemitir, leídas de `FacturacionService`.

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/finanzas/estado-resultados` | Selector de período (por defecto el mes actual), comparación opcional en una segunda columna, márgenes ("—" sin ventas), indicadores; cada línea se despliega con su detalle; sección aparte de pendientes tributarios; exportar CSV | RF-FIN-06 a 13, 15 |
| `/dashboard` | Avisos según permiso, cargados por separado con HTMX; cifras de ventas sin impuestos | RF-FIN-14 |
| Exportaciones (estado de resultados, ventas, kardex, stock, gastos, comprobantes) | Botón "Exportar CSV" en cada listado; respeta los filtros | RF-FIN-15, 16 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Función SQL única para el estado de resultados | Calcularlo en Python desde el ORM | Una sola fuente para pantalla, CSV y API; rendimiento con agregados (ADR-10) |
| `gasto_periodo` calculado en el dominio y guardado | Repetir la regla del IGV en SQL | La regla vive una sola vez, en Python (art. 7.3) |
| La empresa de la función sale siempre del contexto de la empresa | Recibirla del request | Aislamiento (art. 3) |
| Anulación de gastos y ventas en el período de la anulación | Recalcular el período original | Un período revisado no cambia por un hecho posterior |
| Avisos del dashboard cargados por separado | Una sola consulta grande | Cada aviso depende de un permiso distinto y no frena a los demás |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/finance tests/acceptance -k "E08b"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/finance/unit/test_periodo.py` | Mes actual y anterior con `hoy` fijo; margen sin ventas | RF-FIN-06, 13 |
| Unitario | `tests/finance/unit/test_permisos_dashboard.py` | Avisos y columnas según permisos | RF-FIN-14, 16 |
| Integración | `tests/finance/integration/test_estado_resultados.py` | Escenario de la spec (1400,00 → 253,33; 53,81 % / 18,10 %); costo congelado; anulación en otro mes; saldo inicial y transferencia fuera; gratuitas 686,18 en gastos; gasto anulado en otro mes | RF-FIN-05 a 10 |
| Integración | `tests/finance/integration/test_cortes.py` | Venta del 30-nov a las 23:30 de Lima en noviembre | RF-FIN-06 |
| Property-based | `tests/finance/integration/test_detalle.py` | Σ detalle = línea con datos aleatorios | RF-FIN-11 |
| Integración | `tests/finance/integration/test_pendientes.py` | NC sin aceptar y rechazados listados aparte | RF-FIN-12 |
| Integración | `tests/finance/integration/test_csv.py` | UTF-8 con BOM, filtros, sin columnas de costo sin permiso | RF-FIN-15, 16 |
| Aceptación | `features/gastos_resultados.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-FIN-06, RF-FIN-07, RF-FIN-08, RF-FIN-09, RF-FIN-10 | §1 `resultados.py`, `fn_estado_resultados.sql` · §3 `mes_actual`, `periodo_anterior` · §4 · §5 estado de resultados · §7 `test_estado_resultados.py` |
| RF-FIN-11, RF-FIN-12, RF-FIN-13 | §4 detalle y pendientes · §3 `margen` · §5 · §7 `test_detalle.py`, `test_pendientes.py` |
| RF-FIN-14 | §1 `dashboard.py` · §3 `avisos_visibles` · §5 `/dashboard` · §7 |
| RF-FIN-15, RF-FIN-16 | §1 `csv.py` · §3 `columnas_exportables` · §5 exportaciones · §7 `test_csv.py` |

## 9. Dependencias de dudas abiertas

- **Q10 (lote perdido):** la línea "Pérdidas de producción" se muestra en 0 hasta que se apruebe.
