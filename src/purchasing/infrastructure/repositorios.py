"""Adaptador de PostgreSQL de los proveedores (plan 0002d §2)."""

from dataclasses import asdict

from purchasing.domain.proveedor import DatosProveedor
from purchasing.infrastructure.models import Proveedor, ProveedorProducto


class ProveedoresOrm:
    def activo(self, proveedor_id):
        return Proveedor.objects.filter(pk=proveedor_id).values_list("activo", flat=True).first()

    def existe_documento(self, tipo, numero, excluir):
        filas = Proveedor.objects.filter(tipo_doc=tipo, num_doc=numero)
        return filas.exclude(pk=excluir).exists()

    def guardar(self, proveedor_id, datos: DatosProveedor):
        if proveedor_id is None:
            return Proveedor.objects.create(**asdict(datos)).id
        Proveedor.objects.filter(pk=proveedor_id).update(**asdict(datos))
        return proveedor_id

    def cambiar_estado(self, proveedor_id, activo):
        Proveedor.objects.filter(pk=proveedor_id).update(activo=activo)

    def eliminar(self, proveedor_id):
        Proveedor.objects.filter(pk=proveedor_id).delete()

    def asociar(self, proveedor_id, producto_id, precio, plazo, codigo):
        ProveedorProducto.objects.update_or_create(
            proveedor_id=proveedor_id,
            producto_id=producto_id,
            defaults={
                "precio_referencial": precio,
                "plazo_entrega_dias": plazo,
                "codigo_proveedor": codigo,
            },
        )

    def quitar(self, proveedor_id, producto_id):
        ProveedorProducto.objects.filter(
            proveedor_id=proveedor_id, producto_id=producto_id
        ).delete()
