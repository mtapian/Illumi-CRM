from shared.interfaces.menu import Menu


def test_agrupa_por_grupo_en_orden_y_abre_el_grupo_activo():
    menu = Menu()
    menu.agregar("Configuración", "Suscripción", "/suscripcion/", orden=90)
    menu.agregar("Configuración", "Empresa", "/configuracion/empresa/", orden=90)
    menu.agregar(None, "Inicio", "/dashboard/", orden=0)
    menu.agregar("Configuración", "Empresa", "/configuracion/empresa/", orden=90)  # idempotente

    grupos = menu.armar("/configuracion/empresa/")

    assert [g["nombre"] for g in grupos] == [None, "Configuración"]
    inicio, config = grupos
    assert not inicio["abierto"] and config["abierto"]
    assert [(i["etiqueta"], i["activo"]) for i in config["items"]] == [
        ("Suscripción", False),
        ("Empresa", True),
    ]


def test_marca_activa_una_subruta():
    menu = Menu()
    menu.agregar("Ventas", "Pedidos", "/ventas/pedidos/", orden=10)
    assert menu.armar("/ventas/pedidos/15/")[0]["items"][0]["activo"]


def test_separa_las_opciones_de_plataforma():
    menu = Menu()
    menu.agregar(None, "Inicio", "/dashboard/")
    menu.agregar(None, "Empresas", "/plataforma/empresas/", ambito="plataforma")
    assert [i["etiqueta"] for g in menu.armar("/", "plataforma") for i in g["items"]] == [
        "Empresas"
    ]
    assert [i["etiqueta"] for g in menu.armar("/") for i in g["items"]] == ["Inicio"]
