# Illumi-CRM — Especificaciones (SDD)

Repositorio de especificaciones del MVP de **Illumi-CRM**, un CRM/ERP SaaS multiempresa para PYMEs productoras en Perú. Primer cliente: cervecera artesanal con producción a pedido.

> **Metodología:** Spec-Driven Development. Los principios del proyecto están en **[docs/constitution.md](docs/constitution.md)**; la guía de trabajo (flujo, estructura, identificadores), en **[AGENTS.md](AGENTS.md)**; el estado actual de cada spec, en **[MEMORY.md](MEMORY.md)**.

## Estructura

```
docs/constitution.md              ← constitución (principios)
AGENTS.md                         ← guía de trabajo
MEMORY.md                         ← estado y decisiones
PRD.md                            ← visión, alcance MVP, métricas, preguntas abiertas
specs/
├── 000-arquitectura/plan.md      ← decisiones técnicas transversales
├── 001-tenancy-accesos/
├── 002-catalogo/
├── 003-inventario/
├── 004-compras/
├── 005-produccion/
├── 006-ventas-pedidos/
├── 007-facturacion-electronica/
└── 008-finanzas/
    ├── spec.md                   ← QUÉ y POR QUÉ (EARS, sin stack)
    ├── plan.md                   ← CÓMO (modelo de datos, casos de uso, tests)
    ├── tasks.md                  ← tareas (cuando el plan esté aprobado)
    └── features/*.feature        ← escenarios Gherkin (criterio de aceptación)
```

> Las carpetas `NNN-*` equivalen a las épicas `E0N` del PRD. Cuando existan tickets en el issue tracker se puede añadir la clave (p. ej. `006-ventas-pedidos` ↔ `ILL-123`) en el encabezado de la spec.

## Glosario

| Término | Definición |
|---|---|
| Tenant / Empresa | Cliente del SaaS; sus datos están aislados del resto |
| Insumo | Materia prima de la receta (malta, lúpulo, levadura, agua tratada, aditivos) |
| Envase / material | Material de envasado (botella, lata, tapa, etiqueta, caja, barril) |
| Granel | Cerveza terminada en tanque, medida en litros, por estilo (p. ej. "IPA a granel") |
| Presentación | Producto terminado vendible: granel + contenido (L) + materiales (p. ej. "IPA botella 330 ml") |
| Mercadería | Producto de reventa: se compra y se vende sin producirlo (agua, snacks, merchandising); puede controlar lote si es perecible |
| Receta | Lista de insumos para un volumen base de un estilo |
| OP | Orden de producción: cocción y fermentación de una receta para obtener granel |
| Envasado | Transformación de granel de un lote en unidades de una o más presentaciones |
| Lote | Código de trazabilidad de un granel producido; se hereda en sus presentaciones |
| FEFO | First Expired, First Out: se vende primero el lote que vence antes |
| Costo promedio | Costo promedio ponderado por producto = valor total / cantidad total; cambia con las entradas y con las reversiones de entradas |
| PSE / OSE | Proveedor de servicios electrónicos / operador que emite y valida comprobantes ante SUNAT |
| ISC | Impuesto Selectivo al Consumo (aplica a la cerveza) |
| Utilidad operativa | Ventas netas − costo de ventas − mermas y ajustes netos − pérdidas de producción − gastos operativos |
| Módulo | Área del sistema visible en el menú (Inventario, Producción…) |
| Funcionalidad | Capacidad comercializable dentro de un módulo; la habilita el super admin por plan o por empresa |
| Permiso | Acción concreta (`ventas.venta.anular`); el admin de la empresa lo asigna a roles |
| Rol | Conjunto de permisos definido por cada empresa; un usuario puede tener varios |
| Plantilla de rol | Rol inicial editable creado al registrar la empresa (Gerente, Producción, Almacén, Ventas) |
| Habilitación / ajuste | Funcionalidades efectivas de una empresa = plan ± ajustes del super admin (con vigencia opcional) |
