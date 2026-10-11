"""0002a, T21: registro de pestañas externas de la ficha (RF-CAT-04)."""

from catalog.interfaces.pestanas import Pestanas


def test_activa_segun_su_casilla_y_solo_con_su_permiso():
    p = Pestanas()
    p.agregar("compras", "Compras", "se_compra", lambda r, i: f"<p>{i}</p>", permiso="x")
    compras = {"clave": "compras", "etiqueta": "Compras", "orden": 30, "casilla": "se_compra"}
    assert p.para(None, 7, {"se_compra"}, {"x"}) == [compras | {"activa": True, "html": "<p>7</p>"}]
    assert p.para(None, 7, {"se_vende"}, {"x"})[0]["activa"] is False
    assert p.para(None, 7, {"se_compra"}, set()) == []
