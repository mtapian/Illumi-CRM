# PRD — Illumi-CRM MVP

| Campo | Valor |
|---|---|
| Producto | Illumi-CRM (CRM/ERP SaaS) |
| Versión | MVP · release 1 · v0.2 (control de acceso por módulos, funcionalidades y roles configurables) |
| Estado | En revisión (validación 2026-10-10: 10 bloqueantes; ver §12 Q10–Q12 y dependencias de Q1/Q2) |
| Owner | Product Owner (tapiafiis@gmail.com) |
| Fecha | 2026-10-10 |
| Mercado | Perú (SUNAT, PEN, IGV 18 %) |
| Cliente piloto | Cervecera artesanal, producción a pedido |
| Referencia funcional | `saas-ventas-inventario` (Laravel 11): se reescribe en Python/Django con arquitectura hexagonal |

---

## 1. Problema

Las PYMEs productoras (cerveceras artesanales como caso piloto) operan con planillas y sistemas desconectados:

- **No saben cuánto les cuesta producir.** El costo de un lote de cerveza depende del precio real de insumos y envases, y se calcula a mano o no se calcula.
- **No saben cuánto ganan.** Sin un costo histórico confiable por venta, la utilidad del mes se estima, no se mide.
- **El inventario no cuadra.** Un lote produce varias presentaciones (botella, lata, barril) y las mermas de envasado no se registran.
- **Producen a pedido sin trazabilidad.** No hay vínculo entre el pedido del cliente, el lote producido y lo que se entregó.
- **Facturan aparte.** El comprobante electrónico no sale del mismo sistema donde se registra la venta.

El sistema de referencia resuelve ventas, inventario simple y facturación SUNAT, pero no producción ni costo histórico, y tiene limitaciones de modelo (stock entero, costo sobrescrito, numeración global).

## 2. Objetivo del MVP

> Que una cervecera pueda **comprar insumos y mercadería, producir, envasar, vender (su cerveza y productos de reventa), facturar y conocer su utilidad operativa mensual** en un solo sistema, sin planillas paralelas.

### No-objetivos (release 1)
- Contabilidad (plan de cuentas, asientos, libros electrónicos PLE).
- Cuentas por cobrar y por pagar, caja y bancos, conciliación.
- CRM comercial avanzado: leads, oportunidades, actividades, campañas.
- Control de proceso cervecero (densidad, temperatura, programación de tanques).
- Guías de remisión electrónicas, detracciones y percepciones.
- Cobro online de suscripciones SaaS.
- App móvil o funcionamiento offline.

## 3. Usuarios

| Rol | Quién es | Necesita |
|---|---|---|
| **Administrador** (dueño) | Dueño o gerente general de la cervecera | Configurar la empresa, ver la utilidad, controlar usuarios |
| **Gerente** | Jefe de operaciones o comercial | Ver todo lo operativo y ejecutar anulaciones (no hay flujo de aprobación en el MVP) |
| **Producción** | Maestro cervecero | Recetas, órdenes de producción y envasado |
| **Almacén** | Encargado de almacén | Compras, stock, ajustes y conteos |
| **Ventas** | Vendedor B2B/B2C o atención de taproom | Clientes, pedidos, ventas y comprobantes |
| **Super admin** | Operador de la plataforma SaaS | Alta de empresas, planes, suspensión, soporte, y **habilitar módulos y funcionalidades por plan y por empresa** |

> Los roles de empresa Gerente, Producción, Almacén y Ventas son **plantillas iniciales editables**; "Administrador" es un rol de sistema que no se edita (siempre tiene todos los permisos habilitados). Cada empresa crea sus propios roles combinando permisos, pero solo dentro de las funcionalidades que la plataforma le habilitó. Modelo completo en `specs/0001b-Tenancy-plataforma-habilitaciones/spec.md` y `specs/0001c-Tenancy-usuarios-roles/spec.md` ("Definiciones").

```
Super admin ──► Plan (paquete de funcionalidades) ± ajustes por empresa (con vigencia)
                        │
                        ▼  funcionalidades habilitadas de la empresa
Admin del tenant ──► Roles propios (permisos ⊆ habilitados) ──► Usuarios (1..n roles)
                        │
                        ▼
              Permisos efectivos = roles ∩ habilitados
```

## 4. Flujo principal (happy path)

```
Compra de insumos, envases y mercadería ─► Stock + costo promedio   (la mercadería queda lista para vender)
          │
Pedido del cliente (CONFIRMADO) ─► ¿hay stock de la presentación?
          │                              │ no
          │                              ▼
          │                   OP planificada (receta × litros)
          │                              │ iniciar: consume insumos
          │                              │ terminar: ingresa granel con lote y costo/L
          │                              ▼
          │                   Envasado: granel ─► botellas / latas / barriles (mismo lote)
          ▼                              │
Venta (FEFO por lote, costo snapshot) ◄──┘
          │
Comprobante electrónico (boleta/factura) ─► SUNAT vía PSE
          │
Gastos del mes ─► Estado de resultados: utilidad bruta ─► utilidad operativa
```

## 5. Alcance funcional: épicas y casos de uso

| Épica | Caso de uso | Prioridad |
|---|---|---|
| **E01 Tenancy y accesos** | UC-TEN-01 Registrar empresa con prueba gratis · UC-TEN-02 Iniciar sesión · UC-TEN-03 Gestionar usuarios · UC-TEN-04 Configurar datos de empresa · UC-TEN-05 Restringir acceso por suscripción vencida · UC-TEN-06 Activar plan (super admin) · UC-TEN-07 Configurar funcionalidades de un plan (super admin) · UC-TEN-08 Habilitar módulos y funcionalidades por empresa (super admin) · UC-TEN-09 Gestionar roles y permisos (tenant) · UC-TEN-10 Consultar la auditoría de accesos · UC-TEN-11 Gestionar tokens de API | Must |
| **E02 Catálogo** | UC-CAT-01 Gestionar unidades de medida · UC-CAT-02 Gestionar productos por tipo · UC-CAT-03 Definir presentación y sus materiales · UC-CAT-04 Desactivar producto · UC-CAT-05 Gestionar categorías de ISC | Must |
| **E03 Inventario** | UC-INV-01 Gestionar almacenes · UC-INV-02 Consultar stock por almacén y lote · UC-INV-03 Consultar kardex · UC-INV-04 Registrar ajuste de inventario · UC-INV-05 Alertar stock bajo mínimo · UC-INV-06 Alertar lotes próximos a vencer | Must (05–06 Should) |
| **E04 Compras** | UC-COM-01 Gestionar proveedores · UC-COM-02 Registrar compra · UC-COM-03 Anular compra | Must |
| **E05 Producción** | UC-PRD-01 Gestionar recetas versionadas · UC-PRD-02 Planificar OP · UC-PRD-03 Iniciar OP · UC-PRD-04 Terminar OP · UC-PRD-05 Anular OP · UC-PRD-06 Registrar envasado · UC-PRD-07 Cerrar OP · UC-PRD-08 Consultar costo y rendimiento del lote | Must |
| **E06 Ventas y pedidos** | UC-VEN-01 Gestionar clientes · UC-VEN-02 Crear pedido · UC-VEN-03 Confirmar pedido · UC-VEN-04 Avanzar estado del pedido · UC-VEN-05 Registrar venta · UC-VEN-06 Anular venta · UC-VEN-07 Cancelar pedido | Must |
| **E07 Facturación electrónica** | UC-FAC-01 Configurar facturación · UC-FAC-02 Emitir comprobante · UC-FAC-03 Reintentar comprobantes pendientes · UC-FAC-04 Enviar resumen diario de boletas · UC-FAC-05 Emitir nota de crédito · UC-FAC-06 Descargar y enviar comprobante | Must (04 condicional a Q1: sale del MVP si el PSE envía los resúmenes) |
| **E08 Finanzas** | UC-FIN-01 Registrar gasto operativo · UC-FIN-02 Anular gasto · UC-FIN-03 Ver estado de resultados · UC-FIN-04 Ver dashboard de indicadores · UC-FIN-05 Exportar reportes a CSV | Must (04 Should) |

Detalle de comportamiento en `specs/000Nx-*/spec.md` y criterios de aceptación en `specs/000Nx-*/features/*.feature`.

## 6. Reglas de negocio transversales

| ID | Regla |
|---|---|
| RN-GEN-01 | Los datos de una empresa nunca son visibles ni modificables por otra empresa. |
| RN-GEN-02 | El stock de un producto en un almacén (y lote) nunca puede ser negativo. |
| RN-GEN-03 | Todo cambio de stock genera exactamente un movimiento en el kardex, con su costo. |
| RN-GEN-04 | El costo de inventario es **promedio ponderado por producto** (valor total / cantidad total), sin IGV. |
| RN-GEN-05 | El costo de una salida (venta, consumo, merma) se congela al momento del movimiento y nunca se recalcula. |
| RN-GEN-06 | Los documentos (compra, OP, envasado, pedido, venta, comprobante) tienen numeración correlativa por empresa y serie, sin duplicados. |
| RN-GEN-07 | Los documentos confirmados no se editan ni se borran: se anulan, y la anulación revierte sus efectos de stock. |
| RN-GEN-08 | Toda operación registra el usuario y la fecha/hora (zona horaria America/Lima). |
| RN-GEN-09 | Cantidades: hasta 4 decimales. Importes: 2 decimales con redondeo half-up. Costos unitarios: 6 decimales. |
| RN-GEN-10 | Todo caso de uso exige un **permiso** del catálogo; el usuario solo lo ejecuta si el permiso está en sus roles **y** su funcionalidad está habilitada para la empresa. Se valida en el servidor, no solo en el menú. |
| RN-GEN-11 | Deshabilitar un módulo o una funcionalidad nunca borra datos; solo impide operar. |

## 7. Requisitos no funcionales

| Categoría | Requisito |
|---|---|
| Seguridad | Contraseñas con hash (algoritmo por defecto de Django); credenciales SUNAT/PSE cifradas en reposo; HTTPS obligatorio; sesión expira por inactividad (valor por definir) |
| Aislamiento | Test automatizado de aislamiento entre empresas en cada repositorio; bloquea el release si falla |
| Concurrencia | Dos usuarios que venden el último stock a la vez: uno tiene éxito y el otro recibe un error claro |
| Rendimiento | Listados paginados; objetivo p95 < 800 ms con 10 000 productos y 100 000 movimientos por empresa (a validar) |
| Auditoría | Kardex inmutable; registro de anulaciones con motivo y usuario |
| Disponibilidad | Si el PSE o SUNAT no responde, la venta se registra igual y el comprobante queda pendiente para reintento |
| Conservación | XML y CDR de comprobantes almacenados y descargables (plazo legal a validar con el contador) |
| Usabilidad | Interfaz web responsive en español, usable en tablet en planta |
| Integración | API REST autenticada por token para lectura de stock, pedidos y ventas (consumo desde n8n) |

## 8. Métricas de éxito (propuestas, a validar con el piloto)

| Métrica | Meta a 60 días del go-live |
|---|---|
| Operaciones del piloto registradas en el sistema (compras, OP, envasados, ventas) | 100 % |
| Diferencia entre el conteo físico mensual y el stock del sistema (valorizado; reporte de ajustes `CONTEO`, E03) | < 2 % |
| Comprobantes electrónicos aceptados por SUNAT dentro de las 24 h (`aceptado_en − fecha_emision`, widget del dashboard) | ≥ 99 % |
| Estado de resultados mensual generado sin planillas externas | Sí |
| Tiempo de registro de un envasado de 3 presentaciones | < 5 min |

## 9. Supuestos

1. El piloto compra insumos en la misma unidad en que los usa en la receta (kg, g, L, unidad); no hay conversión de unidades de compra en el MVP.
2. El costeo de producción incluye solo materiales (insumos + envases) más un costo indirecto manual opcional por OP. La mano de obra y los gastos de planta van a gastos operativos.
3. Los barriles retornables **no** se controlan en inventario en el MVP (son activos que circulan entre clientes). La presentación en barril consume solo materiales descartables (precinto, etiqueta). Control de barriles en comodato: R2.
4. Una sola moneda (PEN) y un solo % de IGV por empresa.
5. La emisión electrónica se hace mediante un PSE/OSE con API, no con firma directa.

## 10. Dependencias y riesgos

| Riesgo / dependencia | Impacto | Mitigación |
|---|---|---|
| Tratamiento del **ISC** de la cerveza: **definido** por el contador (Q2). Riesgo residual: el código del tipo de sistema en el XML y el monto, que cambia por decreto | Medio: rechazo de comprobantes si el código no coincide con lo que valida el PSE | Validar el XML con ISC en el sandbox del PSE antes de S4; monto parametrizado con vigencia |
| Elección del **PSE/OSE** | Alto: bloquea E07 | Decisión antes del sprint de E07; puerto desacoplado (`EmisorComprobantes`) |
| Calidad de los datos iniciales (stock y costos de apertura) | Medio | Carga de saldo inicial como ajuste con costo (UC-INV-04) |
| Reescritura desde Laravel | Medio: se pierden funcionalidades probadas | Los specs heredan los flujos SUNAT de la referencia |
| Alcance de la producción "a pedido" con tiempos largos de fermentación (semanas) | Medio | Pedido con fecha de entrega; el estado `EN_PRODUCCION` se vincula a la OP |

## 11. Plan de release (propuesto)

| Sprint | Épicas | Hito |
|---|---|---|
| S0 | E01 | Login multiempresa con aislamiento verificado; habilitaciones por plan/empresa y roles configurables |
| S1 | E02, E03, E04 | Compras con stock y costo promedio |
| S2 | E05 | OP → granel → envasado multipresentación |
| S3 | E06 | Pedido → venta con FEFO y costo congelado |
| S4 | E07 | Boleta y factura aceptadas en beta SUNAT. **Requisito de entrada:** Q1 (PSE) y T1 (almacenamiento de XML/CDR) resueltos; código del tipo de sistema ISC validado en el sandbox del PSE |
| S5 | E08 | Utilidad operativa del mes · go-live piloto. **Requisito:** ISC configurado y probado en el sandbox del PSE |

## 12. Preguntas abiertas

| # | Pregunta | Dueño |
|---|---|---|
| Q1 | ¿Qué PSE/OSE se usará? | PO |
| Q2 | ~~ISC de la cerveza~~ **Respondido por el contador (2026-10-10):** Sistema Específico, **S/ 2.51 por litro vigente desde el 2024-07-01**, sin importar el precio ni la graduación; configurable por empresa en categorías de ISC con vigencia (E02 UC-CAT-05); tributo `2000` (ISC); tipo de sistema `01` (monto fijo) según el contador; base del IGV = valor + ISC; NC: el ISC y el IGV se ajustan en proporción; gratuitas: retiro de bienes gravado con ISC + IGV, reportado como transferencia gratuita y asumido por el emisor; su costo y los tributos asumidos van a gastos de venta (E08 RN-FIN-07). **Queda:** confirmar con el PSE el código del tipo de sistema (ver E07 RN-FAC-07) | PSE |
| Q3 | ¿El piloto vende en taproom (B2C con boleta) además de B2B? | PO / piloto |
| Q4 | ¿Hay mockups de UI? Si no, se usa la referencia Laravel como guía visual | PO |
| Q5 | ¿Se necesita migrar datos desde el sistema de referencia? | PO |
| Q6 | ¿Tiempo de expiración de sesión y política de contraseñas? | PO |
| Q7 | ¿Vida útil por presentación (botella vs barril) o por estilo? | Piloto |
| Q8 | ¿Qué funcionalidades incluye cada plan comercial (Gratis, Emprendedor, Negocio)? | PO |
| Q9 | ¿Se necesitan permisos por registro (p. ej. "solo mi almacén", "solo mis ventas") en el MVP? Propuesto: R2 | PO |
| Q10 | ¿Se aprueba el "lote perdido" (terminar una OP con 0 L, pasa a `CERRADA` y su costo va a pérdidas de producción)? Escenarios marcados `@pendiente-q10` | PO |
| Q11 | ~~¿E01 completo en S0 o versión mínima?~~ **Respondido por el PO (2026-10-10):** E01 completo en S0 (planes, ajustes con vigencia, vista previa de impacto); excepción aprobada al art. 7.6 de la constitución | PO |
| Q12 | Preguntas al contador: plazo máximo de envío a SUNAT y del resumen; plazo de conservación de XML/CDR; formato de cuotas a crédito; reemisión de rechazados (¿nuevo correlativo?); anulación de compra ya consumida (**PO 2026-10-10: opción A**, se corrige por ajuste; falta el visto bueno del contador); costeo del granel por lote vs. promedio; costo indirecto vs. gastos de planta; sustento de mermas y desmedros; percepción del IGV en cerveza; fecha del kardex en compras con fecha pasada; umbral de S/ 700 de la boleta | Contador |
| Q13 | ~~¿Vende productos que no produce?~~ **Respondido por el PO (2026-10-10):** sí (agua, snacks, merchandising). Se agrega el tipo `MERCADERIA`: se compra, ingresa al stock y se vende sin receta ni envasado; lote opcional para perecibles (E02, E04, E06) | PO |
