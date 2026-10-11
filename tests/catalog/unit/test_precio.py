"""0002a, T18: desglose informativo del precio de lista (RF-CAT-30)."""

from decimal import Decimal as D

from catalog.domain.precio import Desglose, desglose_precio


def test_desglose_con_isc():
    # Ejemplo de la spec: S/ 12.00 = valor 9.34 + ISC 0.83 + IGV 1.83
    assert desglose_precio(D("12.00"), D("18"), D("0.83")) == Desglose(
        D("9.34"), D("0.83"), D("1.83")
    )


def test_desglose_sin_isc_y_suma_exacta():
    d = desglose_precio(D("12.00"), D("18"), D("0"))
    assert d == Desglose(D("10.17"), D("0.00"), D("1.83"))
    assert d.valor + d.isc + d.igv == D("12.00")
