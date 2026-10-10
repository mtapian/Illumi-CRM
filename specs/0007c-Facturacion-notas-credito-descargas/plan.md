# Plan 0007c — Facturación: notas de crédito y descargas

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` (ADR-08) · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/billing`. No conoce ventas ni inventario: recibe un `ComprobanteDTO` con importes, cuotas y códigos ya calculados (épica 0006), y la `venta_id` como referencia opaca. Bloqueado por Q1 (PSE) solo en el adaptador `PseEmisor`. Requiere: 0007a, 0007b, 0006c.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/billing/domain/nota_credito.py` | Construcción de la NC por el total (réplica de líneas, ISC, IGV) y su espera al original | RF-FAC-24 a 28 |
| `src/billing/domain/errores.py` | `SerieInvalida`, `CredencialesInvalidas`, `ComprobanteNoAceptado`, `VentaAnuladaNoReemitible`… | todos los `SI … ENTONCES` |
| `src/billing/application/fachada.py` | `FacturacionService`: `registrar_emision`, `registrar_anulacion`, `registrar_correccion`, `intentar_envio`, `reintentar_pendientes`, `reemitir` | RF-FAC-24 a 28 |
| `src/billing/application/bandeja.py` | `ConsultarBandeja`, `DescargarArchivo`, `EnviarComprobantePorEmail`, `ReintentarManual` | RF-FAC-29 a 32 |
| `src/billing/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/billing/interfaces/management/commands/billing_reintentar.py`, `billing_resumen_diario.py`, `billing_alertar_plazos.py`, `billing_enviar_emails.py` | Procesos programados | RF-FAC-30 |
| `src/billing/interfaces/views/*.py` + `templates/billing/*.html` | Pantallas de §5 y representación impresa | RF-FAC-29 a 32 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `billing_comprobante` | empresa_id, venta_id, tipo (`01`,`03`,`07`,`INTERNO`), serie, correlativo, referencia_id null, motivo_nc, fecha_emision `DATE`, total, estado (`PENDIENTE`, `ESPERANDO_ORIGINAL`, `ACEPTADO`, `OBSERVADO`, `RECHAZADO`, `ERROR`, `NO_REQUERIDA`), intentos, ultimo_intento_en, aceptado_en, requiere_atencion, hash, xml_ref, cdr_ref, pdf_ref, codigo_respuesta, mensaje, email_enviado_en, payload_enviado `JSONB` | UNIQUE(empresa_id, serie, correlativo); `CHECK correlativo < 1e8`; aceptado ⇒ con XML y CDR; trigger de inmutabilidad al aceptar | RF-FAC-24 a 28 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `construir_nc(original, motivo) -> ComprobanteDTO` | Réplica de valor, ISC e IGV por línea; serie de NC según la letra | RF-FAC-24, 27 |
| `estado_inicial_nc(estado_original) -> estado` | `PENDIENTE` si el original está aceptado; si no, `ESPERANDO_ORIGINAL` | RF-FAC-25 |
| `resolver_nc_en_espera(estado_original, hoy) -> (estado, fecha_emision)` | Aceptado ⇒ `PENDIENTE` con fecha de hoy; rechazado ⇒ `NO_REQUERIDA` | RF-FAC-25, 26 |

## 4. Algoritmos clave

Sin algoritmos no triviales: la lógica está en las funciones puras de §3.

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/comprobantes/` | Bandeja con filtros (fecha, tipo, serie, estado, cliente), insignias de estado, "Requiere atención", días restantes del plazo, rechazados sin reemitir; reintento individual o masivo; CSV | RF-FAC-31, 32 |
| `/comprobantes/<id>` | Detalle, mensaje del PSE, par venta anulada ↔ NC en espera; descargas de PDF, XML y CDR; enviar por email; reemitir | RF-FAC-25, 29, 30 |
| Dashboard | Comprobantes que requieren atención, % aceptados en 24 h | RF-FAC-32 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Copia propia de XML y CDR | Guardar solo las URL del PSE | Conservación legal aunque se cambie de PSE (art. 5.4) |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/billing tests/acceptance -k "E07c"`. El contrato real con el PSE se prueba aparte (`pytest -m externo`, fuera del CI por defecto).

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/billing/unit/test_nota_credito.py` | Réplica de ISC e IGV; espera y resolución con `hoy` | RF-FAC-24 a 28 |
| Caso de uso | `tests/billing/usecases/test_bandeja.py` | Descargas por empresa, email automático y manual, CSV, rechazados visibles | RF-FAC-29 a 32 |
| Aceptación | `features/facturacion.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-FAC-24, RF-FAC-25, RF-FAC-26, RF-FAC-27, RF-FAC-28 | §1 `nota_credito.py` · §3 `construir_nc`, `estado_inicial_nc`, `resolver_nc_en_espera` · §4 reintentos · §7 `test_nota_credito.py` |
| RF-FAC-29, RF-FAC-30, RF-FAC-31, RF-FAC-32 | §1 `bandeja.py`, `billing_enviar_emails` · §5 bandeja y detalle · §7 `test_bandeja.py` |

## 9. Dependencias de dudas abiertas

- **Q12 (plazos, conservación, reemisión) y validación de RF-FAC-25:** parámetros con vigencia; no cambian el código.
