# Plan 007 — Facturación electrónica

Estado: borrador

Spec: `./spec.md` · Base técnica: `../000-arquitectura/plan.md` (ADR-08) · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/billing`. No conoce ventas ni inventario: recibe un `ComprobanteDTO` con importes, cuotas y códigos ya calculados (spec 006), y la `venta_id` como referencia opaca. Bloqueado por Q1 (PSE) solo en el adaptador `PseEmisor`.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/billing/domain/comprobante.py` | Agregado `Comprobante`: estados, intentos, inmutabilidad al aceptar | RF-FAC-07 a 10, 15 a 21 |
| `src/billing/domain/series.py` | Formato de series y letra de la NC | RF-FAC-01, 06 |
| `src/billing/domain/politica_envio.py` | Funciones puras de reintento, plazo legal y modo de envío (con `hoy`/`ahora`) | RF-FAC-04, 05, 15, 18, 19, 22 |
| `src/billing/domain/nota_credito.py` | Construcción de la NC por el total (réplica de líneas, ISC, IGV) y su espera al original | RF-FAC-24 a 28 |
| `src/billing/domain/errores.py` | `SerieInvalida`, `CredencialesInvalidas`, `ComprobanteNoAceptado`, `VentaAnuladaNoReemitible`… | todos los `SI … ENTONCES` |
| `src/billing/application/dto.py` | `ComprobanteDTO` (líneas con valor, ISC, IGV, gratuitas, cuotas, códigos) | RF-FAC-11 a 13 |
| `src/billing/application/puertos.py` | `EmisorComprobantes` (`emitir`, `consultar`, `enviar_resumen`, `consultar_ticket`, `probar_conexion`) | RF-FAC-03, 08, 16, 22 |
| `src/billing/application/fachada.py` | `FacturacionService`: `registrar_emision`, `registrar_anulacion`, `registrar_correccion`, `intentar_envio`, `reintentar_pendientes`, `reemitir` | RF-FAC-07 a 28 |
| `src/billing/application/configuracion.py` | `ConfigurarFacturacion`, `ProbarConexion` | RF-FAC-01 a 03, 06 |
| `src/billing/application/bandeja.py` | `ConsultarBandeja`, `DescargarArchivo`, `EnviarComprobantePorEmail`, `ReintentarManual` | RF-FAC-20, 29 a 32 |
| `src/billing/infrastructure/emisores/null.py`, `fake.py`, `pse.py` | Adaptadores: nulo (comprobante interno), simulado (tests), PSE real (Q1) | RF-FAC-04, 08 |
| `src/billing/infrastructure/cifrado.py` | Cifrado autenticado de credenciales con clave del entorno | RF-FAC-02 |
| `src/billing/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/billing/interfaces/management/commands/billing_reintentar.py`, `billing_resumen_diario.py`, `billing_alertar_plazos.py`, `billing_enviar_emails.py` | Procesos programados | RF-FAC-15, 18, 19, 22, 23, 30 |
| `src/billing/interfaces/views/*.py` + `templates/billing/*.html` | Pantallas de §5 y representación impresa | RF-FAC-01, 03, 14, 20, 29 a 32 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `billing_config` | empresa_id, habilitado, entorno, proveedor, credenciales `BYTEA` (cifradas), emisor_*, series (factura, boleta, NC factura, NC boleta), email_automatico, probado_en, estado_conexion, mensaje_conexion | UNIQUE(empresa_id); `CHECK` de formato de series | RF-FAC-01 a 03, 06 |
| `billing_comprobante` | empresa_id, venta_id, tipo (`01`,`03`,`07`,`INTERNO`), serie, correlativo, referencia_id null, motivo_nc, fecha_emision `DATE`, total, estado (`PENDIENTE`, `ESPERANDO_ORIGINAL`, `ACEPTADO`, `OBSERVADO`, `RECHAZADO`, `ERROR`, `NO_REQUERIDA`), intentos, ultimo_intento_en, aceptado_en, requiere_atencion, hash, xml_ref, cdr_ref, pdf_ref, codigo_respuesta, mensaje, email_enviado_en, payload_enviado `JSONB` | UNIQUE(empresa_id, serie, correlativo); `CHECK correlativo < 1e8`; aceptado ⇒ con XML y CDR; trigger de inmutabilidad al aceptar | RF-FAC-07 a 10, 15 a 28 |
| `billing_resumen` | empresa_id, fecha_referencia, identificador, ticket, estado, intentos | Solo si Q1 lo requiere | RF-FAC-22, 23 |

Los plazos de envío y de conservación son parámetros con vigencia (`tenancy_parametro_vigencia`, spec 001).

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `validar_series(series)` | 4 caracteres; factura y su NC con `F`, boleta y su NC con `B` | RF-FAC-01 |
| `modo_emision(facturacion_habilitada, empresa_en_prueba) -> {INTERNO, PENDIENTE_SIN_ENVIO, ELECTRONICO}` | Regla de RF-FAC-04 y 05 | RF-FAC-04, 05 |
| `toca_reintentar(comprobante, ahora, plazo_dias) -> bool` | Habilitada; cada 15 min hasta 10 intentos, luego cada hora; dentro del plazo legal | RF-FAC-15, 18 |
| `dias_para_plazo(fecha_emision, plazo_dias, hoy) -> int` | Días restantes del plazo legal | RF-FAC-19 |
| `alerta_de_plazo(dias_restantes) -> bool` | `≤ 2` | RF-FAC-19 |
| `se_envia_individual(tipo, con_resumen) -> bool` | Con resumen, boletas y sus NC solo van en el resumen | RF-FAC-22 |
| `estado_tras_respuesta(resultado) -> estado` | Mapea la respuesta del PSE; `ERROR` en fallas de red | RF-FAC-08, 09 |
| `construir_nc(original, motivo) -> ComprobanteDTO` | Réplica de valor, ISC e IGV por línea; serie de NC según la letra | RF-FAC-24, 27 |
| `estado_inicial_nc(estado_original) -> estado` | `PENDIENTE` si el original está aceptado; si no, `ESPERANDO_ORIGINAL` | RF-FAC-25 |
| `resolver_nc_en_espera(estado_original, hoy) -> (estado, fecha_emision)` | Aceptado ⇒ `PENDIENTE` con fecha de hoy; rechazado ⇒ `NO_REQUERIDA` | RF-FAC-25, 26 |
| `puede_reemitir(comprobante, venta_anulada) -> bool` | Solo `RECHAZADO` y venta no anulada | RF-FAC-21 |
| `lineas_xml(dto) -> list` | Tributo `2000` y tipo de sistema en líneas con ISC; marca de transferencia gratuita | RF-FAC-12, 13 |
| `importe_en_letras(total) -> str` | Para la representación impresa | RF-FAC-14 |

## 4. Algoritmos clave

**Emisión con outbox** (RF-FAC-07 a 10):
```
registrar_emision(dto):                        # dentro de la transacción de la venta
  modo = modo_emision(config.habilitado, empresa_en_prueba)
  si modo = INTERNO: crear comprobante INTERNO (serie I001) y terminar          # RF-FAC-04
  correlativo = SequencePort.siguiente(tipo, serie)
  crear comprobante PENDIENTE con payload_enviado = dto                          # RF-FAC-07
intentar_envio(id):                            # fuera de la transacción (on_commit, cron, manual)
  c = select_for_update(skip_locked) ; si nadie más lo tiene:                     # RF-FAC-17
    si not se_envia_individual(c.tipo, con_resumen) → salir
    r = emisor.consultar(c) ; si ya aceptado → ACEPTADO sin reenviar             # RF-FAC-16
    si no r = emisor.emitir(c)
    c.estado = estado_tras_respuesta(r); guardar XML y CDR propios; aceptado_en  # RF-FAC-08 a 10
```

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
| `/facturacion/configuracion` | Formulario (credenciales enmascaradas), series con validación, botón "Probar conexión" con fecha y resultado | RF-FAC-01 a 03, 06 |
| `/comprobantes/` | Bandeja con filtros (fecha, tipo, serie, estado, cliente), insignias de estado, "Requiere atención", días restantes del plazo, rechazados sin reemitir; reintento individual o masivo; CSV | RF-FAC-18 a 21, 31, 32 |
| `/comprobantes/<id>` | Detalle, mensaje del PSE, par venta anulada ↔ NC en espera; descargas de PDF, XML y CDR; enviar por email; reemitir | RF-FAC-21, 25, 29, 30 |
| Representación impresa (A4 y ticket de 80 mm) | Emisor, cliente, líneas, totales con ISC e IGV, importe en letras, QR o hash, leyenda | RF-FAC-14 |
| Dashboard | Comprobantes que requieren atención, % aceptados en 24 h | RF-FAC-18, 19, 32 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Emisión por PSE con un puerto `EmisorComprobantes` | Firmar el XML en Python | Menos riesgo en el MVP; se cambia de PSE sin tocar ventas (ADR-08) |
| Outbox + reintento por cron | Llamar al PSE dentro del request | La venta nunca depende de SUNAT y nunca queda sin comprobante (art. 5.2) |
| `skip_locked` + advisory lock en los reintentos | Confiar en que el cron no se solapa | Evita el doble envío del mismo comprobante (RF-FAC-17) |
| Copia propia de XML y CDR | Guardar solo las URL del PSE | Conservación legal aunque se cambie de PSE (art. 5.4) |
| Cifrado autenticado de credenciales con clave del entorno | Guardarlas en claro o con hash | Hay que poder usarlas, pero nunca mostrarlas (art. 6.2) |
| Reintentos cada hora tras el intento 10 | Detenerse a los 10 | El plazo legal dura días (RF-FAC-15) |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/billing tests/acceptance -k "E07"`. El contrato real con el PSE se prueba aparte (`pytest -m externo`, fuera del CI por defecto).

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/billing/unit/test_series.py` | Formato y letra de la NC | RF-FAC-01, 06 |
| Unitario | `tests/billing/unit/test_politica_envio.py` | Modo de emisión; reintento a los 15 min y cada hora; plazo con `hoy` fijo; resumen vs. individual | RF-FAC-04, 05, 15, 18, 19, 22 |
| Unitario | `tests/billing/unit/test_nota_credito.py` | Réplica de ISC e IGV; espera y resolución con `hoy` | RF-FAC-24 a 28 |
| Unitario | `tests/billing/unit/test_xml.py` | Líneas con ISC (tributo `2000`), gratuitas, importe en letras | RF-FAC-12 a 14 |
| Caso de uso | `tests/billing/usecases/test_emision.py` | Ciclo de estados con `FakeEmisor` (acepta, rechaza, timeout, ya existe) | RF-FAC-07 a 11, 16, 20, 21 |
| Caso de uso | `tests/billing/usecases/test_bandeja.py` | Descargas por empresa, email automático y manual, CSV, rechazados visibles | RF-FAC-29 a 32 |
| Caso de uso | `tests/billing/usecases/test_configuracion.py` | Guardar, probar conexión, credenciales nunca expuestas | RF-FAC-01 a 03 |
| Integración | `tests/billing/integration/test_outbox.py` | El proceso muere tras el commit: el comprobante `PENDIENTE` existe y se envía | RF-FAC-07 |
| Integración | `tests/billing/integration/test_concurrencia.py` | Dos reintentos a la vez ⇒ un solo envío | RF-FAC-17 |
| Integración | `tests/billing/integration/test_resumen.py` | Resumen con boletas y NC, ticket y reintento | RF-FAC-22, 23 |
| Integración | `tests/billing/integration/test_conservacion.py` | Ningún aceptado sin XML y CDR propios; trigger de inmutabilidad | RF-FAC-08, 10 |
| Aceptación | `features/facturacion.feature` | Escenarios de la spec (los `@pendiente-q1` se omiten) | todos |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-FAC-01, RF-FAC-02, RF-FAC-03, RF-FAC-04, RF-FAC-05, RF-FAC-06 | §1 `configuracion.py`, `series.py`, `cifrado.py`, `politica_envio.py` · §3 `validar_series`, `modo_emision` · §4 emisión · §5 configuración · §7 |
| RF-FAC-07, RF-FAC-08, RF-FAC-09, RF-FAC-10, RF-FAC-11, RF-FAC-12, RF-FAC-13, RF-FAC-14 | §1 `comprobante.py`, `fachada.py`, `dto.py` · §3 `estado_tras_respuesta`, `lineas_xml`, `importe_en_letras` · §4 emisión con outbox · §5 representación impresa · §7 |
| RF-FAC-15, RF-FAC-16, RF-FAC-17, RF-FAC-18, RF-FAC-19, RF-FAC-20, RF-FAC-21 | §1 comandos, `politica_envio.py` · §3 `toca_reintentar`, `dias_para_plazo`, `alerta_de_plazo`, `puede_reemitir` · §4 reintentos · §5 bandeja · §7 |
| RF-FAC-22, RF-FAC-23 | §1 `billing_resumen_diario` · §2 `billing_resumen` · §3 `se_envia_individual` · §7 `test_resumen.py` |
| RF-FAC-24, RF-FAC-25, RF-FAC-26, RF-FAC-27, RF-FAC-28 | §1 `nota_credito.py` · §3 `construir_nc`, `estado_inicial_nc`, `resolver_nc_en_espera` · §4 reintentos · §7 `test_nota_credito.py` |
| RF-FAC-29, RF-FAC-30, RF-FAC-31, RF-FAC-32 | §1 `bandeja.py`, `billing_enviar_emails` · §5 bandeja y detalle · §7 `test_bandeja.py` |

## 9. Dependencias de dudas abiertas

- **Q1 (PSE):** solo afecta a `infrastructure/emisores/pse.py`, a si UC-FAC-04 entra y a quién genera el PDF.
- **Código de tipo de sistema ISC:** dato de la categoría (spec 002); se valida con un comprobante de prueba en el sandbox.
- **Q12 (plazos, conservación, reemisión) y validación de RF-FAC-25:** parámetros con vigencia; no cambian el código.
- **T1 (almacenamiento):** decide el backend de archivos, sin cambiar los casos de uso.
