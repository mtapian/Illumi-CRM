"""Avisos del dashboard que registran los contextos (mismo patrón que `menu.py`).

El inventario registra "Stock bajo" y "Por vencer" (0003c) desde su `urls.py`; tenancy los
pinta sin conocerlo. `contenido(request)` devuelve el HTML del aviso.
"""


class Avisos:
    def __init__(self):
        self._items = {}

    def agregar(self, clave, titulo, contenido, permiso=None, orden=50):
        self._items[clave] = {"titulo": titulo, "contenido": contenido, "permiso": permiso}
        self._items[clave]["orden"] = orden

    def para(self, request):
        """Los avisos que el usuario puede ver, en orden (RF-INV-30)."""
        permisos = request.actor.permisos if request.actor else frozenset()
        visibles = (a for a in self._items.values() if a["permiso"] in (None, *permisos))
        return [
            {"titulo": a["titulo"], "html": a["contenido"](request)}
            for a in sorted(visibles, key=lambda a: a["orden"])
        ]


avisos = Avisos()
