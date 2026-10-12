"""Repositorios del catálogo. Usan el manager por empresa: solo ven la empresa actual."""

from django.db import IntegrityError, transaction

from catalog.application.fachada import EntradaHistorial, ProductoDTO
from catalog.domain.errores import SkuDuplicado
from catalog.domain.isc import Tarifa
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto
from catalog.infrastructure.models import (
    Categoria,
    Impuesto,
    ImpuestoTasa,
    Marca,
    Producto,
    ProductoHistorial,
    ProductoImpuesto,
    ProductoIscTasa,
    RecetaComponente,
    Unidad,
)
from shared.domain.auditoria import diferencias
from shared.domain.errores import NoEncontrado
from shared.domain.tenant import empresa_actual

_CAMPOS = (
    "sku",
    "nombre",
    "tipo",
    "categoria_id",
    "marca_id",
    "stock_minimo",
    "se_vende",
    "se_compra",
    "se_fabrica",
    "precio_venta",
    "contenido_litros",
    "isc_sistema",
    "isc_codigo_tipo_sistema",
    "vida_util_dias",
    "peso_kg",
    "volumen_m3",
    "referencia",
    "codigo_barras",
)


def _a_modelo(d: DatosProducto, unidad_id: int) -> dict:
    campos = {c: getattr(d, c) for c in _CAMPOS}
    return campos | {
        "unidad_id": unidad_id,
        "activo": d.activo,
    }


_AGRUPACIONES = {"categoria": Categoria, "marca": Marca}


class CatalogoOrm:
    def unidad_activa(self, abreviatura):
        fila = Unidad.objects.filter(abreviatura=abreviatura.upper(), activo=True)
        return fila.values_list("id", flat=True).first()

    def crear_unidad(self, nombre, abreviatura, codigo_sunat) -> int:
        return Unidad.objects.create(
            nombre=nombre, abreviatura=abreviatura, codigo_sunat=codigo_sunat
        ).id

    def existe_unidad(self, abreviatura) -> bool:
        return Unidad.objects.filter(abreviatura=abreviatura).exists()

    def _unidad(self, unidad_id) -> Unidad:
        unidad = Unidad.objects.filter(pk=unidad_id).first()
        if unidad is None:
            raise NoEncontrado("No encontrado")
        return unidad

    def unidad_en_uso(self, unidad_id, solo_activos) -> bool:
        productos = self._unidad(unidad_id).productos.all()
        return (productos.filter(activo=True) if solo_activos else productos).exists()

    def cambiar_estado_unidad(self, unidad_id, activo) -> None:
        Unidad.objects.filter(pk=self._unidad(unidad_id).pk).update(activo=activo)

    def eliminar_unidad(self, unidad_id) -> None:
        self._unidad(unidad_id).delete()

    def editar_unidad(self, unidad_id, nombre, abreviatura, codigo_sunat) -> None:
        Unidad.objects.filter(pk=self._unidad(unidad_id).pk).update(
            nombre=nombre, abreviatura=abreviatura, codigo_sunat=codigo_sunat
        )

    def abreviatura_de(self, unidad_id) -> str:
        return self._unidad(unidad_id).abreviatura

    # --- Categorías y marcas (RF-CAT-33, 34, 49) ---

    def _agrupacion(self, tipo, id_):
        fila = _AGRUPACIONES[tipo].objects.filter(pk=id_).first()
        if fila is None:
            raise NoEncontrado("No encontrado")
        return fila

    def existe_agrupacion(self, tipo, nombre, excluir_id=None) -> bool:
        filas = _AGRUPACIONES[tipo].objects.filter(nombre__iexact=nombre)
        return filas.exclude(pk=excluir_id).exists()

    def guardar_agrupacion(self, tipo, id_, nombre, descripcion, activo) -> int:
        campos = {"nombre": nombre} | ({"descripcion": descripcion} if tipo == "categoria" else {})
        if activo is not None:
            campos["activo"] = activo
        if id_ is None:
            return _AGRUPACIONES[tipo].objects.create(**campos).id
        fila = self._agrupacion(tipo, id_)
        for campo, valor in campos.items():
            setattr(fila, campo, valor)
        fila.save(update_fields=list(campos))
        return fila.id

    def agrupacion_activa(self, tipo, id_) -> bool:
        return _AGRUPACIONES[tipo].objects.filter(pk=id_, activo=True).exists()

    def agrupacion_en_uso(self, tipo, id_) -> bool:
        return self._agrupacion(tipo, id_).productos.exists()

    def cambiar_estado_agrupacion(self, tipo, id_, activo) -> None:
        fila = self._agrupacion(tipo, id_)
        fila.activo = activo
        fila.save(update_fields=["activo"])

    def eliminar_agrupacion(self, tipo, id_) -> None:
        self._agrupacion(tipo, id_).delete()

    def existe_sku(self, sku, excluir_id=None) -> bool:
        return Producto.objects.filter(sku=sku).exclude(pk=excluir_id).exists()

    def sku_con_codigo_barras(self, codigo, excluir_id=None) -> str | None:
        filas = Producto.objects.filter(codigo_barras=codigo).exclude(pk=excluir_id)
        return filas.values_list("sku", flat=True).first()

    def registrar_historial(self, producto_id, actor_id, accion, antes, despues) -> None:
        ProductoHistorial.objects.create(
            producto_id=producto_id, actor_id=actor_id, accion=accion, antes=antes, despues=despues
        )

    def historial(self, producto_id) -> list[EntradaHistorial]:
        filas = ProductoHistorial.objects.filter(producto_id=producto_id).select_related("actor")
        return [
            EntradaHistorial(
                h.created_at,
                h.actor.email if h.actor else "—",
                h.accion,
                diferencias(h.antes, h.despues),
            )
            for h in filas.order_by("-created_at", "-id")
        ]

    def contar_activos(self) -> int:
        return Producto.objects.filter(activo=True).count()

    def _producto(self, producto_id) -> Producto:
        producto = Producto.objects.select_related("unidad").filter(pk=producto_id).first()
        if producto is None:
            raise NoEncontrado("No encontrado")
        return producto

    def producto(self, producto_id) -> DatosProducto:
        p = self._producto(producto_id)
        datos = {c: getattr(p, c) for c in _CAMPOS}
        return DatosProducto(
            **datos | {"tipo": TipoProducto(p.tipo)},
            unidad=p.unidad.abreviatura,
            activo=p.activo,
        )

    def crear_producto(self, datos, unidad_id) -> int:
        try:
            with transaction.atomic():
                return Producto.objects.create(**_a_modelo(datos, unidad_id)).id
        except IntegrityError as e:
            if "sku_unico_por_empresa" in str(e):
                raise SkuDuplicado(f"Ya existe un producto con el SKU {datos.sku}") from e
            raise

    def actualizar_producto(self, producto_id, datos, unidad_id) -> None:
        Producto.objects.filter(pk=producto_id).update(**_a_modelo(datos, unidad_id))

    def cambiar_estado_producto(self, producto_id, activo) -> None:
        Producto.objects.filter(pk=producto_id).update(activo=activo)

    def eliminar_producto(self, producto_id) -> None:
        self._producto(producto_id).delete()

    def referencias_internas(self, producto_id) -> int:
        return RecetaComponente.objects.filter(
            componente_id=producto_id, producto__empresa_id=empresa_actual()
        ).count()

    def tasas_isc(self, producto_id) -> list[Tarifa]:
        filas = ProductoIscTasa.objects.filter(producto_id=producto_id).order_by("-vigente_desde")
        return [Tarifa(d, m) for d, m in filas.values_list("vigente_desde", "monto_por_litro")]

    def existe_tasa(self, producto_id, desde) -> bool:
        return ProductoIscTasa.objects.filter(producto_id=producto_id, vigente_desde=desde).exists()

    def agregar_tasa(self, producto_id, monto, desde, actor_id) -> None:
        ProductoIscTasa.objects.create(
            producto_id=producto_id,
            monto_por_litro=monto,
            vigente_desde=desde,
            creado_por_id=actor_id,
        )

    def isc_de_producto(self, producto_id):
        """(código de tipo de sistema, litros por unidad) o None si no está afecto."""
        p = Producto.objects.filter(pk=producto_id, isc_sistema__isnull=False).first()
        return (p.isc_codigo_tipo_sistema, p.contenido_litros) if p else None

    def unidades_de(self, ids) -> dict[int, str]:
        filas = Producto.objects.filter(pk__in=ids).values_list("id", "unidad__abreviatura")
        return dict(filas)

    def estados(self, ids):
        filas = Producto.objects.filter(pk__in=ids).values_list("id", "tipo", "activo")
        return {i: (TipoProducto(t), a) for i, t, a in filas}

    def grafo_recetas(self) -> dict[int, set[int]]:
        grafo = {}
        filas = RecetaComponente.objects.filter(producto__empresa_id=empresa_actual())
        for producto, componente in filas.values_list("producto_id", "componente_id"):
            grafo.setdefault(producto, set()).add(componente)
        return grafo

    def receta(self, producto_id):
        filas = RecetaComponente.objects.filter(
            producto_id=producto_id, producto__empresa_id=empresa_actual()
        )
        return tuple(filas.order_by("id").values_list("componente_id", "cantidad_por_unidad"))

    def guardar_receta(self, producto_id, receta) -> None:
        self._producto(producto_id)  # de la empresa actual
        RecetaComponente.objects.filter(producto_id=producto_id).delete()
        RecetaComponente.objects.bulk_create(
            RecetaComponente(producto_id=producto_id, componente_id=c, cantidad_por_unidad=q)
            for c, q in receta
        )

    def productos(self, ids=None, casillas=None, solo_activos=False) -> list[ProductoDTO]:
        filas = Producto.objects.select_related("unidad").order_by("nombre")
        if ids is not None:
            filas = filas.filter(pk__in=ids)
        if casillas:
            filas = filas.filter(**casillas)
        if solo_activos:
            filas = filas.filter(activo=True)
        return [
            ProductoDTO(
                p.id,
                p.sku,
                p.nombre,
                TipoProducto(p.tipo),
                p.unidad.abreviatura,
                p.se_vende,
                p.se_compra,
                p.se_fabrica,
                p.precio_venta,
                p.activo,
                p.vida_util_dias,
            )
            for p in filas
        ]


class ImpuestosOrm:
    """Repositorio del maestro de impuestos (spec 0002e)."""

    def _fila(self, id_) -> Impuesto:
        fila = Impuesto.objects.filter(pk=id_).first()
        if fila is None:
            raise NoEncontrado("No encontrado")
        return fila

    def impuesto(self, id_):
        fila = self._fila(id_)
        return fila.tipo, fila.codigo, fila.criterio

    def existe_nombre(self, tipo, nombre, excluir_id) -> bool:
        filas = Impuesto.objects.filter(tipo=tipo, nombre__iexact=nombre)
        return filas.exclude(pk=excluir_id).exists()

    def en_uso(self, id_) -> bool:
        # ponytail: solo productos; los documentos (0004a, 0006b) se suman al usar impuestos.
        return ProductoImpuesto.objects.filter(impuesto_id=id_).exists()

    def asignado_a_activos(self, id_) -> bool:
        return ProductoImpuesto.objects.filter(impuesto_id=id_, producto__activo=True).exists()

    def guardar(self, id_, nombre, tipo, codigo, criterio) -> int:
        campos = {"nombre": nombre, "tipo": tipo, "codigo": codigo, "criterio": criterio}
        if id_ is None:
            return Impuesto.objects.create(**campos).id
        Impuesto.objects.filter(pk=id_).update(**campos)
        return id_

    def fechas_tasas(self, id_):
        return list(
            ImpuestoTasa.objects.filter(impuesto_id=id_).values_list("vigente_desde", flat=True)
        )

    def agregar_tasa(self, id_, importe, desde, actor_id):
        ImpuestoTasa.objects.create(
            impuesto_id=id_, importe=importe, vigente_desde=desde, creado_por_id=actor_id
        )

    def cambiar_estado(self, id_, activo):
        Impuesto.objects.filter(pk=id_).update(activo=activo)
