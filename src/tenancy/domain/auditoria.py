"""Cómo se lee un cambio de acceso: valor anterior → nuevo (RF-TEN-43, 44)."""


def _texto(valor) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, bool):
        return "sí" if valor else "no"
    if isinstance(valor, list):
        return ", ".join(map(str, valor)) or "—"
    return str(valor)


def diferencias(antes: dict | None, despues: dict | None) -> list[str]:
    antes, despues = antes or {}, despues or {}
    cambios = []
    for clave in dict.fromkeys([*antes, *despues]):
        a, d = antes.get(clave), despues.get(clave)
        if a == d:
            continue
        if clave == "permisos" and a is not None and d is not None:
            cambios += [f"{p}: incluido → quitado" for p in sorted(set(a) - set(d))]
            cambios += [f"{p}: no incluido → incluido" for p in sorted(set(d) - set(a))]
        else:
            cambios.append(f"{clave}: {_texto(a)} → {_texto(d)}")
    return cambios
