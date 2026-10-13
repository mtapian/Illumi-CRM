"""0002d, T3: datos del proveedor y del proveedor del producto (RF-COM-01, RF-COM-21)."""

from decimal import Decimal

import pytest

from purchasing.domain.errores import ProveedorInvalido
from purchasing.domain.proveedor import (
    DatosProveedor,
    validar_proveedor,
    validar_proveedor_producto,
)
from shared.domain.documentos import TIPOS_INICIALES
from shared.domain.errores import DocumentoInvalido

REGLAS = {t.abreviatura: t for t in TIPOS_INICIALES}


def validar(d):
    return validar_proveedor(d, REGLAS.get(d.tipo_doc))


def test_proveedor_valido_se_normaliza():
    d = validar(DatosProveedor("RUC", " 20512345671 ", "  Maltería del Sur "))
    assert (d.num_doc, d.razon_social) == ("20512345671", "Maltería del Sur")


def test_documento_y_razon_social_obligatorios():
    with pytest.raises(DocumentoInvalido, match="El RUC no es válido"):
        validar(DatosProveedor("RUC", "20512345672", "X"))
    with pytest.raises(DocumentoInvalido, match="El DNI debe tener 8 dígitos"):
        validar(DatosProveedor("DNI", "1234567", "X"))
    with pytest.raises(ProveedorInvalido, match="La razón social es obligatoria"):
        validar(DatosProveedor("DNI", "45678912", " "))


def test_proveedor_del_producto_solo_comprable_con_precio_y_plazo_no_negativos():
    assert validar_proveedor_producto(True, Decimal("4.805"), 3) == Decimal("4.81")  # half-up
    with pytest.raises(ProveedorInvalido, match="El producto no se compra"):
        validar_proveedor_producto(False, Decimal("1"), 0)
    with pytest.raises(ProveedorInvalido, match="El precio referencial no puede ser negativo"):
        validar_proveedor_producto(True, Decimal("-0.01"), 0)
    with pytest.raises(ProveedorInvalido, match="El plazo de entrega no puede ser negativo"):
        validar_proveedor_producto(True, Decimal("0"), -1)


def test_tipo_de_documento_del_maestro():
    """0006a, RF-VEN-49: el proveedor usa los tipos del maestro, p. ej. carné de extranjería."""
    assert validar(DatosProveedor("CE", "ab123", "Importadora")).num_doc == "AB123"
    with pytest.raises(ProveedorInvalido, match="Elige un tipo de documento"):
        validar(DatosProveedor("XX", "1", "X"))
