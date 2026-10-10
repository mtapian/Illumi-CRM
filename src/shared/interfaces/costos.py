"""Una sola regla para ocultar costos sin `inventario.costo.ver` en pantallas, CSV y API
(RF-TEN-51). Recibe filas (dicts) o nombres de columna."""

VER_COSTOS = "inventario.costo.ver"
CAMPOS_COSTO = frozenset({"costo_unitario", "costo_promedio", "valorizacion", "valor_total"})


def sin_costos(datos: list, permisos) -> list:
    if VER_COSTOS in permisos:
        return datos
    if datos and isinstance(datos[0], dict):
        return [{k: v for k, v in fila.items() if k not in CAMPOS_COSTO} for fila in datos]
    return [c for c in datos if c not in CAMPOS_COSTO]
