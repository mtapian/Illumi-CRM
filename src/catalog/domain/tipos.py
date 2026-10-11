"""Tipo de producto (spec 0002a, enmienda 4): todo es un bien o un servicio. Lo que se hace
con él (vender, comprar, fabricar) lo deciden sus casillas, no el tipo."""

from enum import StrEnum


class TipoProducto(StrEnum):
    BIEN = "BIEN"
    SERVICIO = "SERVICIO"
