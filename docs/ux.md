# Guía de UX/UI de Illumi-CRM

Reglas del PO (2026-10-11) para todo el sistema. Completan la guía visual del ADR-12 (`specs/0000-Arquitectura/plan.md`). Prototipos de referencia: `Referencia:html/Andina_Ejemplos_HTML/` (`productos.html`, `compra-creada.html`, `compra-en-proceso.html`; son maquetas, no guardan datos).

## 1. Reglas generales

| Área | Regla |
|---|---|
| Acción principal | Cada pantalla destaca una acción principal según su contexto y estado. |
| Guardar | Guarda datos; no cambia el estado ni genera movimientos de stock. Se habilita cuando hay cambios. |
| Siguiente paso | El botón principal muestra la siguiente acción válida del flujo. |
| Acciones adicionales | Las menos frecuentes se agrupan en "Más acciones" o ⋯; las más usadas quedan visibles. |
| Acciones destructivas | Al final del menú, separadas y en rojo. Se confirman antes de ejecutarse. |
| Nombres | Verbos que explican el resultado: "Pasar a en proceso", "Finalizar y recibir stock". |
| Estados | El estado actual siempre se muestra con texto. La secuencia de estados es informativa; no funciona como pestañas. |
| Permisos | Solo se muestran las acciones permitidas para el usuario y el estado del registro. |
| Cambios pendientes | Se indica "Cambios sin guardar" y se evita perderlos al salir o al cambiar de estado. |
| Confirmaciones | Explican qué ocurrirá y qué registro se afecta. Nada de "¿Estás seguro?". |
| Procesamiento | Se muestra el avance y se bloquean los clics repetidos mientras se ejecuta una acción. |
| Resultado | El éxito se muestra solo después de que el sistema lo confirma. Si falla, se conservan los datos y se explica el error. |

## 2. Compras

| Estado | Acción principal | Comportamiento |
|---|---|---|
| Creada | Pasar a en proceso | Cambia el estado a En proceso |
| En proceso | Finalizar y recibir stock | Finaliza y genera la recepción de stock |
| Finalizada | Ver recepción (si existe esa consulta) | Consulta la recepción generada |

Antes de generar la recepción se muestran la compra, el proveedor, el almacén y las cantidades. Las recepciones duplicadas se evitan en la interfaz y en el servidor.

## 3. Grillas

| Elemento | Regla |
|---|---|
| Acciones generales | Arriba: Nuevo, Importar o Exportar, cuando existan. |
| Acciones por registro | En la última columna: una acción frecuente visible y las demás en ⋯. |
| Alcance por fila | Editar, consultar o desactivar afectan solo a esa fila. |
| Acciones masivas | Aparecen al seleccionar registros y dicen cuántos se afectan. |
| Abrir detalle | El código o el nombre abre el registro. |
| Buscador | Dice qué permite buscar y acepta Enter. |
| Filtros | Los frecuentes visibles; el resto en "Más filtros". Se muestran los aplicados y se pueden limpiar. |
| Columnas | Las necesarias para identificar, comparar y actuar; el resto, accesible. |
| Importes | Alineados a la derecha, con moneda y decimales consistentes. |
| Resultados | Cantidad de registros, paginación y estados de carga, error y sin resultados. |
| Orden (PO, 2026-10-13) | Las grillas de **documentos** (pedidos, cobranzas, compras, ajustes, OP) se ordenan por fecha de creación **descendente** (lo más nuevo primero) y muestran la **fecha y hora**. Los **maestros** (productos, clientes, proveedores, unidades, métodos de pago…) se ordenan por nombre. Excepción: el **kardex** va en orden de registro ascendente, porque cada fila acumula el saldo de la anterior. |

## 4. Formularios y diseño

| Elemento | Regla |
|---|---|
| Agrupación | Datos generales, documento, productos y totales, separados. |
| Campos | Etiquetas visibles, obligatorios marcados y errores junto al campo. |
| Costos | Etiqueta y ayuda según el documento: "Costo sin IGV" (factura) o "Total por unidad" (otro documento). |
| Totales | El total destacado; el cálculo provisional se actualiza al editar. |
| Colores | Azul para acciones principales, verde para éxito, rojo para errores o acciones destructivas. |
| Consistencia | Los mismos botones, filtros, tablas, menús y confirmaciones en todas las pantallas. |
| Accesibilidad | Uso con teclado, foco visible y estados comprensibles sin depender del color. |
| Adaptación | En el celular el contenido se reorganiza sin perder datos ni acciones. |

## 5. Cómo se implementa (sin dependencias nuevas)

- **Barra de acciones:** abajo, como en el prototipo (PO, 2026-10-11), fija al hacer scroll (`.acciones-documento`): a la izquierda el estado de los cambios; a la derecha Guardar (solo con cambios), la acción principal en azul y "Más acciones".
- **Menús "Más acciones" y ⋯:** `<details>` nativo; lo destructivo al final, separado y en rojo.
- **Confirmaciones:** `<dialog>` centrado con el texto de lo que ocurrirá y el registro afectado.
- **Cambios sin guardar, envío único y "Procesando…":** un script corto y común en `base.html`.
- **Éxito y error:** mensajes de Django después de la respuesta del servidor; si falla, el formulario vuelve con lo enviado.
- La unicidad (p. ej. no recibir dos veces) la garantiza el servidor; la interfaz solo la refuerza.
- **Grillas (piezas comunes):**
  - Encabezado `.encabezado-listado`: título, descripción y la acción general a la derecha ("+ Nuevo …" en azul; "Exportar CSV" en secundario).
  - Filtros `<form class="tarjeta barra-filtros">`: buscador `label.buscar` con etiqueta y Enter, 2 o 3 filtros frecuentes con etiqueta, el resto en `<details class="mas-filtros">` (resaltado con `data-activos` si tiene alguno aplicado) y "Filtrar".
  - Chips de filtros aplicados: `shared/interfaces/listados.py::aplicados` + `listados/_aplicados.html` (cada chip quita su filtro; "Limpiar filtros" quita todos). En un maestro con solo buscador: `listados/_buscar.html`.
  - Tabla `.tarjeta.tabla`: el nombre o código abre el registro; importes con `S/` y `class="num"`; última columna `td.acciones` con una acción visible (`a.boton.secundario.chico`) y el resto en `<details class="mas-acciones abajo">` ⋯, lo destructivo al final y en rojo.
  - Pie `listados/_pie.html` con `listados.paginar` (25 por página): cantidad de registros y "1–25 de N" con Anterior/Siguiente; el kardex usa cursor ("Siguientes ›").
- **Formularios:**
  - Obligatorios con `*` en la etiqueta y la nota "Los campos con * son obligatorios."; en formularios de Django, `required_css_class = "requerido"`.
  - Error junto al campo: el error de negocio lleva su campo (`DomainError(mensaje, campo)`); `_intentar` lo deja en `request.errores_campo` y la plantilla lo muestra con `{% include "listados/_error.html" with error=request.errores_campo.<campo> %}`; arriba solo "No se guardó: revisa el campo marcado.". Los errores del inventario en una línea van al campo `lineas`. En un formulario de Django (ficha de producto), la vista pasa el error al campo con `form.add_error` y se abre la pestaña que lo contiene.
  - Si falla un "guardar", el formulario vuelve con lo enviado; si falla una acción con diálogo (recepción, anulación), su diálogo se reabre con el error y lo escrito.
  - Secciones separadas (p. ej. proveedor: "Datos generales" y "Contacto"; compra: "Datos de la compra" y "Productos").
