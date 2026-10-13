"""Cliente (spec 0006a; RF-VEN-01, 02): CRU con datos mínimos; el documento sigue las reglas de
su tipo en el maestro de la plataforma (RF-VEN-49)."""

import re
from dataclasses import dataclass, fields, replace

from sales.domain.errores import ClienteInvalido
from shared.domain.documentos import ReglasDocumento, validar_numero
from shared.domain.errores import DocumentoInvalido

EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
CANALES = ("", "B2B", "B2C")


@dataclass(frozen=True)
class DatosCliente:
    nombre: str
    tipo_doc: str
    num_doc: str = ""
    telefono: str = ""
    email: str = ""
    comentarios: str = ""
    direccion: str = ""
    contacto: str = ""
    canal: str = ""
    activo: bool = True


def validar_cliente(d: DatosCliente, reglas: ReglasDocumento | None) -> DatosCliente:
    """Devuelve los datos limpios o rechaza con el campo del error (docs/ux.md §4)."""
    textos = {f.name: getattr(d, f.name).strip() for f in fields(d) if f.name != "activo"}
    d = replace(d, **textos)
    if not d.nombre:
        raise ClienteInvalido("El nombre o razón social es obligatorio", "nombre")
    if reglas is None:
        raise ClienteInvalido("Elige un tipo de documento", "tipo_doc")
    try:
        num_doc = validar_numero(reglas, d.num_doc)
    except DocumentoInvalido as e:
        e.campo = "num_doc"  # el error va junto al número
        raise
    if d.email and not EMAIL.fullmatch(d.email):
        raise ClienteInvalido("El email no es válido", "email")
    if d.canal not in CANALES:
        raise ClienteInvalido("El canal debe ser B2B o B2C", "canal")
    return replace(d, num_doc=num_doc, email=d.email.lower())
