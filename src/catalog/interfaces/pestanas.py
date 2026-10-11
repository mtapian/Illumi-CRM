"""Pestañas que otros contextos agregan a la ficha de producto (RF-CAT-04).

Mismo patrón que `shared/interfaces/menu.py`: compras (0002d) registra "Compras" (casilla
`se_compra`) desde su `urls.py` sin que el catálogo lo conozca.
`contenido(request, producto_id)` devuelve el HTML de la pestaña; su vista propia verifica
permisos en el servidor (constitución, art. 6.1).
"""


class Pestanas:
    def __init__(self):
        self._items = {}

    def agregar(self, clave, etiqueta, casilla, contenido, orden=30, permiso=None):
        """`casilla`: "se_vende", "se_compra", "se_fabrica", "bien" o None (siempre)."""
        self._items[clave] = {
            "clave": clave,
            "etiqueta": etiqueta,
            "casilla": casilla,
            "contenido": contenido,
            "orden": orden,
            "permiso": permiso,
        }

    def quitar(self, clave):
        self._items.pop(clave, None)

    def para(self, request, producto_id, activas, permisos):
        """Todas las permitidas; `activa` dice si se ve al cargar (la ficha las oculta o
        muestra en vivo según sus casillas)."""
        visibles = (
            p for p in self._items.values() if p["permiso"] is None or p["permiso"] in permisos
        )
        return [
            {
                "clave": p["clave"],
                "etiqueta": p["etiqueta"],
                "orden": p["orden"],
                "casilla": p["casilla"],
                "activa": p["casilla"] is None or p["casilla"] in activas,
                "html": p["contenido"](request, producto_id),
            }
            for p in sorted(visibles, key=lambda p: p["orden"])
        ]


pestanas = Pestanas()
