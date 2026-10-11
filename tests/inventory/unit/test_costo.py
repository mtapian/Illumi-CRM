"""0003a, T1 y T2: costo promedio ponderado por producto (RF-INV-18, RF-INV-24;
RN-INV-01, RN-GEN-09; constitución, art. 4.1 y 4.2). Ejemplo de la malta de la spec."""

from decimal import Decimal as D

from inventory.domain.costo import CostoProducto, entrada, salida_al_promedio

VACIO = CostoProducto()


def test_entrada_recalcula_el_promedio():
    """Filas 1 y 2: 100 × 4.00 y +50 × 5.00 ⇒ 150 KG, 650.00, 4.333333."""
    c = entrada(VACIO, D("100"), D("4"))
    assert (c.cantidad, c.valor, c.promedio) == (D("100.0000"), D("400.00"), D("4.000000"))
    c = entrada(c, D("50"), D("5"))
    assert (c.cantidad, c.valor, c.promedio) == (D("150.0000"), D("650.00"), D("4.333333"))


def test_entrada_redondea_half_up_cantidad_4_importe_2_costo_6():
    c = entrada(VACIO, D("3"), D("0.1234565"))  # costo con más de 6 decimales
    assert c.valor == D("0.37")  # 3 × 0.123457 = 0.370371
    assert c.promedio == D("0.123333")  # 0.37 / 3
    c = entrada(VACIO, D("0.00005"), D("1"))
    assert c.cantidad == D("0.0001")


def test_salida_al_promedio_no_cambia_el_promedio():
    """Filas 3 y 4: −30 sale por 130.00 y −20 por 86.67, con el promedio en 4.333333."""
    c = entrada(entrada(VACIO, D("100"), D("4")), D("50"), D("5"))
    c, importe = salida_al_promedio(c, D("30"))
    assert importe == D("130.00")
    assert (c.cantidad, c.valor, c.promedio) == (D("120.0000"), D("520.00"), D("4.333333"))
    c, importe = salida_al_promedio(c, D("20"))
    assert importe == D("86.67")
    assert (c.cantidad, c.valor, c.promedio) == (D("100.0000"), D("433.33"), D("4.333333"))


def test_salida_que_vacia_sale_por_el_valor_restante():
    """RF-INV-24: sin residuo de redondeo; el promedio se conserva como referencia."""
    c = CostoProducto(D("3"), D("1.00"), D("0.333333"))
    c, importe = salida_al_promedio(c, D("3"))
    assert importe == D("1.00")  # no 3 × 0.333333 = 1.00 redondeado de 0.999999
    assert (c.cantidad, c.valor, c.promedio) == (D("0.0000"), D("0.00"), D("0.333333"))


def test_salida_que_vacia_absorbe_el_residuo():
    c = CostoProducto(D("3"), D("10.00"), D("3.333333"))
    c, primero = salida_al_promedio(c, D("1"))
    c, segundo = salida_al_promedio(c, D("1"))
    c, ultimo = salida_al_promedio(c, D("1"))
    assert (primero, segundo, ultimo) == (D("3.33"), D("3.33"), D("3.34"))
    assert c.valor == D("0.00")


def test_entrada_con_stock_en_cero_toma_el_costo_de_la_entrada():
    c = CostoProducto(D("0"), D("0.00"), D("4.333333"))  # promedio de referencia
    c = entrada(c, D("10"), D("6"))
    assert c.promedio == D("6.000000")
