# Plan 0007b — Facturación: reintentos y resumen diario

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` (ADR-08) · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/billing`. No conoce ventas ni inventario: recibe un `ComprobanteDTO` con importes, cuotas y códigos ya calculados (épica 0006), y la `venta_id` como referencia opaca. Bloqueado por Q1 (PSE) solo en el adaptador `PseEmisor`. Requiere: 0007a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/billing/domain/comprobante.py` | Agregado `Comprobante`: estados, intentos, inmutabilidad al aceptar | RF-FAC-15 a 21 |
| `src/billing/domain/politica_envio.py` | Funciones puras de reintento, plazo legal y modo de envío (con `hoy`/`ahora`) | RF-FAC-15, 18, 19, 22 |
| `src/billing/domain/errores.py` | `SerieInvalida`, `CredencialesInvalidas`, `ComprobanteNoAceptado`, `VentaAnuladaNoReemitible`… | todos los `SI … ENTONCES` |
| `src/billing/application/puertos.py` | `EmisorComprobantes` (`emitir`, `consultar`, `enviar_resumen`, `consultar_ticket`, `probar_conexion`) | RF-FAC-16, 22 |
| `src/billing/application/fachada.py` | `FacturacionService`: `registrar_emision`, `registrar_anulacion`, `registrar_correccion`, `intentar_envio`, `reintentar_pendientes`, `reemitir` | RF-FAC-15 a 23 |
| `src/billing/application/bandeja.py` | `ConsultarBandeja`, `DescargarArchivo`, `EnviarComprobantePorEmail`, `ReintentarManual` | RF-FAC-20 |
| `src/billing/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/billing/interfaces/management/commands/billing_reintentar.py`, `billing_resumen_diario.py`, `billing_alertar_plazos.py`, `billing_enviar_emails.py` | Procesos programados | RF-FAC-15, 18, 19, 22, 23 |
| `src/billing/interfaces/views/*.py` + `templates/billing/*.html` | Pantallas de §5 y representación impresa | RF-FAC-20 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `billing_comprobante` | empresa_id, venta_id, tipo (`01`,`03`,`07`,`INTERNO`), serie, correlativo, referencia_id null, motivo_nc, fecha_emision `DATE`, total, estado (`PENDIENTE`, `ESPERANDO_ORIGINAL`, `ACEPTADO`, `OBSERVADO`, `RECHAZADO`, `ERROR`, `NO_REQUERIDA`), intentos, ultimo_intento_en, aceptado_en, requiere_atencion, hash, xml_ref, cdr_ref, pdf_ref, codigo_respuesta, mensaje, email_enviado_en, payload_enviado `JSONB` | UNIQUE(empresa_id, serie, correlativo); `CHECK correlativo < 1e8`; aceptado ⇒ con XML y CDR; trigger de inmutabilidad al aceptar | RF-FAC-15 a 23 |
| `billing_resumen` | empresa_id, fecha_referencia, identificador, ticket, estado, intentos | Solo si Q1 lo requiere | RF-FAC-22, 23 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `toca_reintentar(comprobante, ahora, plazo_dias) -> bool` | Habilitada; cada 15 min hasta 10 intentos, luego cada hora; dentro del plazo legal | RF-FAC-15, 18 |
| `dias_para_plazo(fecha_emision, plazo_dias, hoy) -> int` | Días restantes del plazo legal | RF-FAC-19 |
| `alerta_de_plazo(dias_restantes) -> bool` | `≤ 2` | RF-FAC-19 |
| `se_envia_individual(tipo, con_resumen) -> bool` | Con resumen, boletas y sus NC solo van en el resumen | RF-FAC-22 |
| `puede_reemitir(comprobante, venta_anulada) -> bool` | Solo `RECHAZADO` y venta no anulada | RF-FAC-21 |

## 4. Algoritmos clave

**Reintentos** (RF-FAC-15, 18, 19, 25, 26):

```
billing_reintentar (cada 15 min, con pg_try_advisory_lock):
  por empresa con facturación habilitada (también suspendida o vencida):
    por c en ERROR/PENDIENTE: si toca_reintentar(c, ahora, plazo) → intentar_envio(c)
                              si c.intentos ≥ 10 → requiere_atencion
    por nc en ESPERANDO_ORIGINAL: (estado, fecha) = resolver_nc_en_espera(original, hoy)
```

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/comprobantes/` | Bandeja con filtros (fecha, tipo, serie, estado, cliente), insignias de estado, "Requiere atención", días restantes del plazo, rechazados sin reemitir; reintento individual o masivo; CSV | RF-FAC-18 a 21 |
| `/comprobantes/<id>` | Detalle, mensaje del PSE, par venta anulada ↔ NC en espera; descargas de PDF, XML y CDR; enviar por email; reemitir | RF-FAC-21 |
| Dashboard | Comprobantes que requieren atención, % aceptados en 24 h | RF-FAC-18, 19 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Reintentos cada hora tras el intento 10 | Detenerse a los 10 | El plazo legal dura días (RF-FAC-15) |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/billing tests/acceptance -k "E07b"`. El contrato real con el PSE se prueba aparte (`pytest -m externo`, fuera del CI por defecto).

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/billing/unit/test_politica_envio.py` | Modo de emisión; reintento a los 15 min y cada hora; plazo con `hoy` fijo; resumen vs. individual | RF-FAC-04, 05, 15, 18, 19, 22 |
| Caso de uso | `tests/billing/usecases/test_emision.py` | Ciclo de estados con `FakeEmisor` (acepta, rechaza, timeout, ya existe) | RF-FAC-07 a 11, 16, 20, 21 |
| Integración | `tests/billing/integration/test_concurrencia.py` | Dos reintentos a la vez ⇒ un solo envío | RF-FAC-17 |
| Integración | `tests/billing/integration/test_resumen.py` | Resumen con boletas y NC, ticket y reintento | RF-FAC-22, 23 |
| Aceptación | `features/facturacion.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-FAC-15, RF-FAC-16, RF-FAC-17, RF-FAC-18, RF-FAC-19, RF-FAC-20, RF-FAC-21 | §1 comandos, `politica_envio.py` · §3 `toca_reintentar`, `dias_para_plazo`, `alerta_de_plazo`, `puede_reemitir` · §4 reintentos · §5 bandeja · §7 |
| RF-FAC-22, RF-FAC-23 | §1 `billing_resumen_diario` · §2 `billing_resumen` · §3 `se_envia_individual` · §7 `test_resumen.py` |

## 9. Dependencias de dudas abiertas

- **Q1 (PSE):** solo afecta a `infrastructure/emisores/pse.py`, a si UC-FAC-04 entra y a quién genera el PDF.

- **Q12 (plazos, conservación, reemisión) y validación de RF-FAC-25:** parámetros con vigencia; no cambian el código.
