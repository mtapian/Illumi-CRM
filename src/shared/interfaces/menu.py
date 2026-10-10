"""Menú lateral: cada contexto registra sus opciones desde sus `urls.py`.

Los grupos (un módulo) se pliegan; el grupo de la página actual se abre solo.
Cada opción puede pedir un permiso: solo se muestra a quien lo tiene (RF-TEN-50). Ocultarla
no es control de acceso (constitución, art. 6.1): la vista lo verifica en el servidor.
"""


class Menu:
    def __init__(self):
        self._items = {}

    def agregar(self, grupo, etiqueta, url, orden=50, ambito="empresa", permiso=None):
        """`grupo=None` deja la opción suelta. `ambito`: "empresa" o "plataforma" (super admin)."""
        self._items[url] = {
            "grupo": grupo,
            "etiqueta": etiqueta,
            "url": url,
            "orden": orden,
            "ambito": ambito,
            "permiso": permiso,
        }

    def armar(self, ruta_actual, ambito="empresa", permisos=None):
        """`permisos=None` no filtra (super admin)."""
        grupos = {}
        items = (
            i
            for i in self._items.values()
            if i["ambito"] == ambito
            and (permisos is None or i["permiso"] is None or i["permiso"] in permisos)
        )
        for item in sorted(items, key=lambda i: i["orden"]):
            grupo = grupos.setdefault(
                item["grupo"], {"nombre": item["grupo"], "abierto": False, "items": []}
            )
            activo = ruta_actual.startswith(item["url"])
            grupo["abierto"] |= activo and item["grupo"] is not None
            grupo["items"].append({**item, "activo": activo})
        return list(grupos.values())


menu = Menu()


def menu_lateral(request):
    actor = getattr(request, "actor", None)
    if actor is None:
        ambito = "plataforma" if getattr(request.user, "is_super", False) else "empresa"
        return {"menu_lateral": menu.armar(request.path, ambito)}
    return {"menu_lateral": menu.armar(request.path, "empresa", actor.permisos)}
