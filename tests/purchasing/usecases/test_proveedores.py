"""0002d, T4 a T6: proveedores y proveedores del producto (RF-COM-01 a 03, 21, 22)."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from catalog.infrastructure.models import Producto
from purchasing.application import proveedores as uc
from purchasing.domain.errores import ProveedorInvalido
from purchasing.domain.proveedor import DatosProveedor
from purchasing.infrastructure.contenedor import caso_de_uso
from purchasing.infrastructure.models import Proveedor, ProveedorProducto
from shared.domain.errores import DocumentoInvalido, NoEncontrado
from shared.domain.tenant import tenant_context

pytestmark = pytest.mark.django_db
RUC = "20512345671"


def guardar(actor, num=RUC, nombre="Maltería del Sur", id_=None, tipo="RUC"):
    return caso_de_uso(uc.GuardarProveedor).ejecutar(actor, id_, DatosProveedor(tipo, num, nombre))


def asociar(actor, proveedor, sku="INS-MALTA", precio="4.80", plazo=3, codigo=""):
    producto = Producto.objects.get(sku=sku).id
    caso = caso_de_uso(uc.AsociarProveedorProducto)
    return caso.ejecutar(actor, proveedor, producto, Decimal(precio), plazo, codigo)


def test_documento_unico_por_empresa_pero_no_entre_empresas(empresa_compras, crear_empresa):
    """RF-COM-01 y caso límite: el mismo RUC en otra empresa se permite."""
    _, actor = empresa_compras
    malteria = guardar(actor)
    with pytest.raises(ProveedorInvalido, match=f"Ya existe un proveedor con el RUC {RUC}"):
        guardar(actor, nombre="Otro")
    guardar(actor, nombre="Maltería del Sur SAC", id_=malteria)  # editarse a sí mismo
    assert Proveedor.objects.get(pk=malteria).razon_social == "Maltería del Sur SAC"
    with pytest.raises(DocumentoInvalido):
        guardar(actor, num="20512345672")
    otra = crear_empresa(ruc="20100047218")
    with tenant_context(otra.id):
        Proveedor.objects.create(tipo_doc="RUC", num_doc=RUC, razon_social="Mismo RUC")
    with transaction.atomic(), pytest.raises(IntegrityError):  # la base también lo impide
        Proveedor.objects.create(tipo_doc="RUC", num_doc=RUC, razon_social="Duplicado")


def test_con_compras_se_desactiva_en_vez_de_eliminarse(empresa_compras, compras):
    """RF-COM-02."""
    _, actor = empresa_compras
    con, sin = guardar(actor), guardar(actor, "45678912", "Juan Pérez", tipo="DNI")
    compras.con_compras.add(con)
    with pytest.raises(ProveedorInvalido, match="El proveedor tiene compras; puedes desactivarlo"):
        caso_de_uso(uc.EliminarProveedor).ejecutar(actor, con)
    caso_de_uso(uc.CambiarEstadoProveedor).ejecutar(actor, con, False)
    caso_de_uso(uc.EliminarProveedor).ejecutar(actor, sin)
    assert list(Proveedor.objects.values_list("id", "activo")) == [(con, False)]


def test_asociar_crea_o_actualiza(empresa_compras):
    """RF-COM-21: un solo registro por proveedor y producto."""
    _, actor = empresa_compras
    p = guardar(actor)
    asociar(actor, p, codigo="MP-01")
    asociar(actor, p, precio="5.10", plazo=4)
    fila = ProveedorProducto.objects.get()
    assert (fila.precio_referencial, fila.plazo_entrega_dias, fila.codigo_proveedor) == (
        Decimal("5.10"),
        4,
        "",
    )
    caso_de_uso(uc.QuitarProveedorProducto).ejecutar(actor, p, fila.producto_id)
    assert not ProveedorProducto.objects.exists()


def test_desactivado_o_no_comprable_no_se_asocia(empresa_compras):
    """RF-COM-03 y RF-COM-21."""
    _, actor = empresa_compras
    p = guardar(actor)
    caso_de_uso(uc.CambiarEstadoProveedor).ejecutar(actor, p, False)
    with pytest.raises(ProveedorInvalido, match="El proveedor está desactivado"):
        asociar(actor, p)
    caso_de_uso(uc.CambiarEstadoProveedor).ejecutar(actor, p, True)
    Producto.objects.filter(sku="INS-MALTA").update(se_compra=False, se_vende=True, precio_venta=1)
    with pytest.raises(ProveedorInvalido, match="El producto no se compra"):
        asociar(actor, p)


def test_proveedor_o_producto_de_otra_empresa_no_existe(empresa_compras, crear_empresa):
    """RF-TEN-52: no se revela que existe en otra empresa."""
    _, actor = empresa_compras
    otra = crear_empresa(ruc="20100047218")
    with tenant_context(otra.id):
        ajeno = Proveedor.objects.create(tipo_doc="RUC", num_doc=RUC, razon_social="Ajeno").id
    with pytest.raises(NoEncontrado):
        asociar(actor, ajeno)
    with pytest.raises(NoEncontrado):
        caso_de_uso(uc.EliminarProveedor).ejecutar(actor, ajeno)
    with pytest.raises(NoEncontrado):
        caso_de_uso(uc.AsociarProveedorProducto).ejecutar(
            actor, guardar(actor), 999999, Decimal("1"), 0, ""
        )
