"""T4 (aislamiento por TenantModel) y T5 (correlativo sin huecos ni duplicados)."""

import threading

import pytest
from django.db import connection

from shared.domain.tenant import TenantNoDefinido, tenant_context
from shared.infrastructure.models import Secuencia
from shared.infrastructure.secuencia import SecuenciaPostgres


@pytest.mark.django_db
def test_sin_tenant_falla_y_con_tenant_a_no_ve_filas_de_b(crear_empresa):
    a, b = crear_empresa("20601234565"), crear_empresa("20512345671")
    with tenant_context(a.id):
        Secuencia.objects.create(documento="VENTA", serie="V")
    with tenant_context(b.id):
        Secuencia.objects.create(documento="VENTA", serie="V")
        Secuencia.objects.create(documento="COMPRA", serie="C")

    with pytest.raises(TenantNoDefinido):
        list(Secuencia.objects.all())
    with tenant_context(a.id):
        assert [s.empresa_id for s in Secuencia.objects.all()] == [a.id]


@pytest.mark.django_db
def test_numeracion_correlativa_por_empresa_y_serie(crear_empresa):
    a, b = crear_empresa("20601234565"), crear_empresa("20512345671")
    secuencia = SecuenciaPostgres()
    with tenant_context(a.id):
        assert [secuencia.siguiente("VENTA", "V") for _ in range(3)] == [1, 2, 3]
        assert secuencia.siguiente("COMPRA", "C") == 1
    with tenant_context(b.id):
        assert secuencia.siguiente("VENTA", "V") == 1


@pytest.mark.django_db(transaction=True)
def test_dos_hilos_obtienen_1_y_2_sin_duplicados(crear_empresa):
    empresa = crear_empresa()
    resultados, barrera = [], threading.Barrier(2)

    def numerar():
        try:
            with tenant_context(empresa.id):
                barrera.wait()
                resultados.append(SecuenciaPostgres().siguiente("VENTA", "V"))
        finally:
            connection.close()

    hilos = [threading.Thread(target=numerar) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert sorted(resultados) == [1, 2]
