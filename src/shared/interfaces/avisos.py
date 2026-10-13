"""Avisos del inicio que registran los contextos (mismo patrón que `menu.py`; spec 0008c,
RF-FIN-17): tenancy los pinta sin conocerlos.

Cada aviso declara cuántos casos hay (`contar(request)`) y su texto en singular y plural; su
"Ver detalle" lleva a un listado filtrado (`enlace`) o despliega su lista (`detalle(request)`
devuelve HTML). Solo se muestran los que tienen algo (n > 0).
"""


class Avisos:
    def __init__(self):
        self._items = {}

    def agregar(
        self, clave, contar, textos, permiso=None, orden=50, enlace=None, detalle=None
    ):  # textos: (singular, plural)
        self._items[clave] = {
            "contar": contar,
            "textos": textos,
            "permiso": permiso,
            "orden": orden,
            "enlace": enlace,
            "detalle": detalle,
        }

    def para(self, request):
        """Los avisos con algo pendiente que el usuario puede ver, en orden (RF-INV-30)."""
        permisos = request.actor.permisos if request.actor else frozenset()
        resultado = []
        for clave, a in sorted(self._items.items(), key=lambda x: x[1]["orden"]):
            if a["permiso"] not in (None, *permisos):
                continue
            n = a["contar"](request)
            if n:
                singular, plural = a["textos"]
                resultado.append(
                    {
                        "clave": clave,
                        "texto": f"{n} {singular if n == 1 else plural}",
                        "enlace": a["enlace"],
                        "detalle": a["detalle"](request) if a["detalle"] else "",
                    }
                )
        return resultado


avisos = Avisos()
