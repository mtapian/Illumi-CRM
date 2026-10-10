"""T13 (RF-TEN-01): cada contexto registra un sembrador de datos iniciales para empresas nuevas."""

from datetime import date

from tenancy.application.sembradores import RegistroSembradores


def test_los_sembradores_se_ejecutan_en_orden_con_empresa_admin_y_hoy():
    llamadas = []
    registro = RegistroSembradores()
    registro.registrar(
        lambda empresa, admin, hoy: llamadas.append(("almacen", empresa, admin, hoy))
    )
    registro.registrar(
        lambda empresa, admin, hoy: llamadas.append(("unidades", empresa, admin, hoy))
    )

    registro.sembrar(empresa_id=1, admin_id=2, hoy=date(2026, 10, 10))

    assert llamadas == [
        ("almacen", 1, 2, date(2026, 10, 10)),
        ("unidades", 1, 2, date(2026, 10, 10)),
    ]


def test_un_sembrador_registrado_dos_veces_corre_una_sola_vez():
    llamadas = []

    def sembrador(empresa, admin, hoy):
        llamadas.append(empresa)

    registro = RegistroSembradores()
    registro.registrar(sembrador)
    registro.registrar(sembrador)
    registro.sembrar(1, 2, date(2026, 10, 10))
    assert llamadas == [1]
