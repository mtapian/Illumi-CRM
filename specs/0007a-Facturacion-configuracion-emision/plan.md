# Plan 0007a — Facturación: configuración y emisión

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` (ADR-08) · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/billing`. No conoce ventas ni inventario: recibe un `ComprobanteDTO` con importes, cuotas y códigos ya calculados (épica 0006), y la `venta_id` como referencia opaca. Bloqueado por Q1 (PSE) solo en el adaptador `PseEmisor`. Requiere: 0006b, 0002c.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/billing/domain/comprobante.py` | Agregado `Comprobante`: estados, intentos, inmutabilidad al aceptar | RF-FAC-07 a 10 |
| `src/billing/domain/series.py` | Formato de series y letra de la NC | RF-FAC-01, 06 |
| `src/billing/domain/politica_envio.py` | Funciones puras de reintento, plazo legal y modo de envío (con `hoy`/`ahora`) | RF-FAC-04, 05 |
| `src/billing/domain/errores.py` | `SerieInvalida`, `CredencialesInvalidas`, `ComprobanteNoAceptado`, `VentaAnuladaNoReemitible`… | todos los `SI … ENTONCES` |
| `src/billing/application/dto.py` | `ComprobanteDTO` (líneas con valor, ISC, IGV, gratuitas, cuotas, códigos) | RF-FAC-11 a 13 |
| `src/billing/application/puertos.py` | `EmisorComprobantes` (`emitir`, `consultar`, `enviar_resumen`, `consultar_ticket`, `probar_conexion`) | RF-FAC-03, 08 |
| `src/billing/application/fachada.py` | `FacturacionService`: `registrar_emision`, `registrar_anulacion`, `registrar_correccion`, `intentar_envio`, `reintentar_pendientes`, `reemitir` | RF-FAC-07 a 14 |
| `src/billing/application/configuracion.py` | `ConfigurarFacturacion`, `ProbarConexion` | RF-FAC-01 a 03, 06 |
| `src/billing/infrastructure/emisores/null.py`, `fake.py`, `pse.py` | Adaptadores: nulo (comprobante interno), simulado (tests), PSE real (Q1) | RF-FAC-04, 08 |
| `src/billing/infrastructure/cifrado.py` | Cifrado autenticado de credenciales con clave del entorno | RF-FAC-02 |
| `src/billing/infrastructure/models.py`, `repositorios.py` | Modelos y repositorios | §2 |
| `src/billing/interfaces/views/*.py` + `templates/billing/*.html` | Pantallas de §5 y representación impresa | RF-FAC-01, 03, 14 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `billing_config` | empresa_id, habilitado, entorno, proveedor, credenciales `BYTEA` (cifradas), emisor_*, series (factura, boleta, NC factura, NC boleta), email_automatico, probado_en, estado_conexion, mensaje_conexion | UNIQUE(empresa_id); `CHECK` de formato de series | RF-FAC-01 a 03, 06 |
| `billing_comprobante` | empresa_id, venta_id, tipo (`01`,`03`,`07`,`INTERNO`), serie, correlativo, referencia_id null, motivo_nc, fecha_emision `DATE`, total, estado (`PENDIENTE`, `ESPERANDO_ORIGINAL`, `ACEPTADO`, `OBSERVADO`, `RECHAZADO`, `ERROR`, `NO_REQUERIDA`), intentos, ultimo_intento_en, aceptado_en, requiere_atencion, hash, xml_ref, cdr_ref, pdf_ref, codigo_respuesta, mensaje, email_enviado_en, payload_enviado `JSONB` | UNIQUE(empresa_id, serie, correlativo); `CHECK correlativo < 1e8`; aceptado ⇒ con XML y CDR; trigger de inmutabilidad al aceptar | RF-FAC-07 a 10 |

## 3. Funciones puras

| Función | Qué hace | RF |
|---|---|---|
| `validar_series(series)` | 4 caracteres; factura y su NC con `F`, boleta y su NC con `B` | RF-FAC-01 |
| `modo_emision(facturacion_habilitada, empresa_en_prueba) -> {INTERNO, PENDIENTE_SIN_ENVIO, ELECTRONICO}` | Regla de RF-FAC-04 y 05 | RF-FAC-04, 05 |
| `estado_tras_respuesta(resultado) -> estado` | Mapea la respuesta del PSE; `ERROR` en fallas de red | RF-FAC-08, 09 |
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

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/facturacion/configuracion` | Formulario (credenciales enmascaradas), series con validación, botón "Probar conexión" con fecha y resultado | RF-FAC-01 a 03, 06 |
| Representación impresa (A4 y ticket de 80 mm) | Emisor, cliente, líneas, totales con ISC e IGV, importe en letras, QR o hash, leyenda | RF-FAC-14 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Emisión por PSE con un puerto `EmisorComprobantes` | Firmar el XML en Python | Menos riesgo en el MVP; se cambia de PSE sin tocar ventas (ADR-08) |
| Outbox + reintento por cron | Llamar al PSE dentro del request | La venta nunca depende de SUNAT y nunca queda sin comprobante (art. 5.2) |
| `skip_locked` + advisory lock en los reintentos | Confiar en que el cron no se solapa | Evita el doble envío del mismo comprobante (RF-FAC-17) |
| Copia propia de XML y CDR | Guardar solo las URL del PSE | Conservación legal aunque se cambie de PSE (art. 5.4) |
| Cifrado autenticado de credenciales con clave del entorno | Guardarlas en claro o con hash | Hay que poder usarlas, pero nunca mostrarlas (art. 6.2) |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/billing tests/acceptance -k "E07a"`. El contrato real con el PSE se prueba aparte (`pytest -m externo`, fuera del CI por defecto).

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/billing/unit/test_series.py` | Formato y letra de la NC | RF-FAC-01, 06 |
| Unitario | `tests/billing/unit/test_politica_envio.py` | Modo de emisión; reintento a los 15 min y cada hora; plazo con `hoy` fijo; resumen vs. individual | RF-FAC-04, 05, 15, 18, 19, 22 |
| Unitario | `tests/billing/unit/test_xml.py` | Líneas con ISC (tributo `2000`), gratuitas, importe en letras | RF-FAC-12 a 14 |
| Caso de uso | `tests/billing/usecases/test_emision.py` | Ciclo de estados con `FakeEmisor` (acepta, rechaza, timeout, ya existe) | RF-FAC-07 a 11, 16, 20, 21 |
| Caso de uso | `tests/billing/usecases/test_configuracion.py` | Guardar, probar conexión, credenciales nunca expuestas | RF-FAC-01 a 03 |
| Integración | `tests/billing/integration/test_outbox.py` | El proceso muere tras el commit: el comprobante `PENDIENTE` existe y se envía | RF-FAC-07 |
| Integración | `tests/billing/integration/test_conservacion.py` | Ningún aceptado sin XML y CDR propios; trigger de inmutabilidad | RF-FAC-08, 10 |
| Aceptación | `features/facturacion.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-FAC-01, RF-FAC-02, RF-FAC-03, RF-FAC-04, RF-FAC-05, RF-FAC-06 | §1 `configuracion.py`, `series.py`, `cifrado.py`, `politica_envio.py` · §3 `validar_series`, `modo_emision` · §4 emisión · §5 configuración · §7 |
| RF-FAC-07, RF-FAC-08, RF-FAC-09, RF-FAC-10, RF-FAC-11, RF-FAC-12, RF-FAC-13, RF-FAC-14 | §1 `comprobante.py`, `fachada.py`, `dto.py` · §3 `estado_tras_respuesta`, `lineas_xml`, `importe_en_letras` · §4 emisión con outbox · §5 representación impresa · §7 |

## 9. Dependencias de dudas abiertas

- **Q1 (PSE):** solo afecta a `infrastructure/emisores/pse.py`, a si UC-FAC-04 entra y a quién genera el PDF.

- **Código de tipo de sistema ISC:** dato de la categoría (épica 0002); se valida con un comprobante de prueba en el sandbox.

- **T1 (almacenamiento):** decide el backend de archivos, sin cambiar los casos de uso.
