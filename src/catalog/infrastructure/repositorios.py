"""Repositorios del catálogo. Usan el manager por empresa: solo ven la empresa actual."""

from django.db import IntegrityError, transaction

from catalog.application.fachada import ProductoDTO
from catalog.domain.errores import SkuDuplicado
from catalog.domain.isc import Tarifa
from catalog.domain.presentacion import DatosPresentacion
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto
from catalog.infrastructure.models import (
    Familia,
    IscCategoria,
    IscTarifa,
    Presentacion,
    PresentacionMaterial,
    Producto,
    Unidad,
)
from shared.domain.errores import NoEncontrado
from shared.domain.tenant import empresa_actual

_CAMPOS = (
    "sku",
    "nombre",
    "tipo",
    "familia_id",
    "stock_minimo",
    "controla_lote",
    "precio_venta",
    "contenido_litros",
    "isc_categoria_id",
    "vida_util_dias",
)


def _a_modelo(d: DatosProducto, unidad_id: int) -> dict:
    campos = {c: getattr(d, c) for c in _CAMPOS}
    return campos | {
        "unidad_id": unidad_id,
        "prefijo_lote": d.prefijo_lote or "",
        "activo": d.activo,
    }


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

    def crear_familia(self, nombre) -> int:
        return Familia.objects.get_or_create(nombre=nombre)[0].id

    def existe_sku(self, sku, excluir_id=None) -> bool:
        return Producto.objects.filter(sku=sku).exclude(pk=excluir_id).exists()

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
            prefijo_lote=p.prefijo_lote or None,
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

    def granel_con_presentaciones_activas(self, producto_id) -> bool:
        return Presentacion.objects.filter(granel_id=producto_id, producto__activo=True).exists()

    def referencias_internas(self, producto_id) -> int:
        como_granel = Presentacion.objects.filter(granel_id=producto_id).count()
        como_material = PresentacionMaterial.objects.filter(
            material_id=producto_id, presentacion__empresa_id=empresa_actual()
        ).count()
        return como_granel + como_material

    def categoria_isc_activa(self, categoria_id) -> bool:
        return IscCategoria.objects.filter(pk=categoria_id, activo=True).exists()

    def tarifas_isc(self, categoria_id) -> list[Tarifa]:
        filas = IscTarifa.objects.filter(categoria_id=categoria_id)
        return [Tarifa(d, m) for d, m in filas.values_list("vigente_desde", "monto_por_litro")]

    def isc_de_producto(self, producto_id):
        """(categoría, contenido en litros) o None si no tiene categoría."""
        p = Producto.objects.select_related("isc_categoria").filter(pk=producto_id).first()
        if p is None or p.isc_categoria is None:
            return None
        contenido = p.contenido_litros
        if p.tipo == TipoProducto.TERMINADO:
            contenido = Presentacion.objects.get(producto=p).contenido_litros
        return p.isc_categoria, contenido

    def tipos_y_estado(self, ids):
        filas = Producto.objects.filter(pk__in=ids).values_list("id", "tipo", "activo")
        return {i: (TipoProducto(t), a) for i, t, a in filas}

    def presentacion(self, producto_id) -> DatosPresentacion | None:
        p = Presentacion.objects.filter(producto_id=producto_id).first()
        if p is None:
            return None
        materiales = p.materiales.order_by("id").values_list("material_id", "cantidad_por_unidad")
        return DatosPresentacion(p.granel_id, p.contenido_litros, tuple(materiales))

    def guardar_presentacion(self, producto_id, datos: DatosPresentacion) -> None:
        p, _ = Presentacion.objects.update_or_create(
            producto_id=producto_id,
            defaults={"granel_id": datos.granel_id, "contenido_litros": datos.contenido_litros},
        )
        p.materiales.all().delete()
        PresentacionMaterial.objects.bulk_create(
            PresentacionMaterial(presentacion=p, material_id=m, cantidad_por_unidad=c)
            for m, c in datos.materiales
        )

    def productos(self, ids=None, tipos=None, solo_activos=False) -> list[ProductoDTO]:
        filas = Producto.objects.select_related("unidad").order_by("nombre")
        if ids is not None:
            filas = filas.filter(pk__in=ids)
        if tipos is not None:
            filas = filas.filter(tipo__in=list(tipos))
        if solo_activos:
            filas = filas.filter(activo=True)
        return [
            ProductoDTO(
                p.id,
                p.sku,
                p.nombre,
                TipoProducto(p.tipo),
                p.unidad.abreviatura,
                p.controla_lote,
                p.precio_venta,
                p.activo,
            )
            for p in filas
        ]


class IscOrm:
    def existe_categoria(self, nombre) -> bool:
        return IscCategoria.objects.filter(nombre__iexact=nombre).exists()

    def crear_categoria(self, nombre, codigo_tipo_sistema) -> int:
        return IscCategoria.objects.create(
            nombre=nombre, codigo_tipo_sistema=codigo_tipo_sistema
        ).id

    def categoria_existe(self, categoria_id) -> bool:
        return IscCategoria.objects.filter(pk=categoria_id).exists()

    def existe_tarifa(self, categoria_id, desde) -> bool:
        return IscTarifa.objects.filter(categoria_id=categoria_id, vigente_desde=desde).exists()

    def agregar_tarifa(self, categoria_id, monto, desde, actor_id) -> None:
        IscTarifa.objects.create(
            categoria_id=categoria_id,
            monto_por_litro=monto,
            vigente_desde=desde,
            creado_por_id=actor_id,
        )

    def productos_activos_con_categoria(self, categoria_id) -> int:
        return Producto.objects.filter(isc_categoria_id=categoria_id, activo=True).count()

    def cambiar_estado_categoria(self, categoria_id, activo) -> None:
        IscCategoria.objects.filter(pk=categoria_id).update(activo=activo)
