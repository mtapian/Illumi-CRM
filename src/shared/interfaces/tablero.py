"""Tarjetas y paneles del inicio que registran los contextos (spec 0008c, RF-FIN-14, 18 a
23): tenancy los pinta sin conocer a ventas ni al catálogo. Cada uno con su permiso."""

from shared.interfaces.iconos import ICONOS


class Registro:
    def __init__(self):
        self._items = {}

    def agregar(self, clave, titulo, funcion, permiso=None, orden=50, **extra):
        """`funcion(request)`: el valor de una tarjeta (texto) o el HTML de un panel."""
        self._items[clave] = {"titulo": titulo, "funcion": funcion, "permiso": permiso}
        if "icono" in extra:
            extra["icono"] = ICONOS.get(extra["icono"], ICONOS["punto"])
        self._items[clave] |= {"orden": orden, **extra}

    def para(self, request):
        permisos = request.actor.permisos if request.actor else frozenset()
        visibles = [a for a in self._items.values() if a["permiso"] in (None, *permisos)]
        return [
            {**a, "valor": a["funcion"](request)}
            for a in sorted(visibles, key=lambda a: a["orden"])
        ]


tarjetas = Registro()  # color e icono en `extra`
paneles = Registro()
