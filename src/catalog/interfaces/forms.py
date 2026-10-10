from django import forms

from catalog.domain.presentacion import DatosPresentacion
from catalog.domain.producto import DatosProducto, campos_requeridos
from catalog.domain.tipos import TipoProducto

_PROPIOS = [
    "precio_venta",
    "isc_categoria_id",
    "contenido_litros",
    "controla_lote",
    "vida_util_dias",
    "prefijo_lote",
]


class ProductoForm(forms.Form):
    """Muestra solo los campos del tipo elegido (RF-CAT-04 a 07)."""

    sku = forms.CharField(label="SKU", max_length=40)
    nombre = forms.CharField(max_length=200)
    unidad = forms.ChoiceField()
    familia = forms.ChoiceField(required=False)
    stock_minimo = forms.DecimalField(
        label="Stock mínimo", decimal_places=4, initial=0, min_value=0
    )
    precio_venta = forms.DecimalField(
        label="Precio de lista (con IGV e ISC)", decimal_places=2, required=False
    )
    isc_categoria_id = forms.ChoiceField(label="Categoría de ISC", required=False)
    contenido_litros = forms.DecimalField(
        label="Contenido en litros por unidad", decimal_places=4, required=False
    )
    controla_lote = forms.BooleanField(label="Controla lote (perecible)", required=False)
    vida_util_dias = forms.IntegerField(label="Vida útil (días)", required=False, min_value=0)
    prefijo_lote = forms.CharField(
        label="Prefijo de lote",
        max_length=10,
        required=False,
        help_text="Por defecto, las 3 primeras letras del nombre",
    )

    FILAS_MATERIALES = 8

    def __init__(
        self,
        *args,
        tipo: TipoProducto,
        unidades,
        familias,
        bloqueados=(),
        graneles=(),
        envases=(),
        categorias_isc=(),
        **kw,
    ):
        super().__init__(*args, **kw)
        self.tipo = TipoProducto(tipo)
        self.fields["unidad"].choices = [(u, u) for u in unidades]
        self.fields["familia"].choices = [("", "—")] + [(str(i), n) for i, n in familias]
        self.fields["isc_categoria_id"].choices = [("", "Sin ISC")] + [
            (str(i), n) for i, n in categorias_isc
        ]
        for campo in _PROPIOS:
            if campo not in campos_requeridos(self.tipo):
                del self.fields[campo]
        if self.tipo == TipoProducto.GRANEL:
            self.fields["unidad"].choices = [("L", "L")]
        if self.tipo == TipoProducto.TERMINADO:  # presentación (spec 0002b)
            self.fields["granel"] = forms.ChoiceField(
                label="Granel de origen", choices=[("", "—")] + [(str(i), n) for i, n in graneles]
            )
            self.fields["contenido"] = forms.DecimalField(
                label="Contenido por unidad (L)", decimal_places=4
            )
            opciones = [("", "—")] + [(str(i), n) for i, n in envases]
            for i in range(self.FILAS_MATERIALES):
                self.fields[f"material_{i}"] = forms.ChoiceField(
                    label=f"Material {i + 1}", choices=opciones, required=False
                )
                self.fields[f"cantidad_{i}"] = forms.DecimalField(
                    label="Cantidad por unidad", decimal_places=4, required=False
                )
        for campo in bloqueados:  # RF-CAT-09: con movimientos se muestran con candado
            if campo in self.fields:
                self.fields[campo].disabled = True
                self.fields[campo].label = f"🔒 {self.fields[campo].label or campo.capitalize()}"

    def datos(self) -> DatosProducto:
        c = self.cleaned_data
        familia = c.get("familia")
        return DatosProducto(
            sku=c["sku"],
            nombre=c["nombre"],
            tipo=self.tipo,
            unidad=c["unidad"],
            familia_id=int(familia) if familia else None,
            stock_minimo=c["stock_minimo"],
            controla_lote=c.get("controla_lote", False),
            precio_venta=c.get("precio_venta"),
            isc_categoria_id=int(c["isc_categoria_id"]) if c.get("isc_categoria_id") else None,
            contenido_litros=c.get("contenido_litros"),
            vida_util_dias=c.get("vida_util_dias"),
            prefijo_lote=c.get("prefijo_lote") or None,
        )

    def presentacion(self) -> DatosPresentacion | None:
        if self.tipo != TipoProducto.TERMINADO:
            return None
        c = self.cleaned_data
        materiales = tuple(
            (int(c[f"material_{i}"]), c[f"cantidad_{i}"])
            for i in range(self.FILAS_MATERIALES)
            if c.get(f"material_{i}")
        )
        return DatosPresentacion(int(c["granel"]), c["contenido"], materiales)

    @staticmethod
    def inicial_presentacion(p: DatosPresentacion | None) -> dict:
        if p is None:
            return {}
        inicial = {"granel": str(p.granel_id), "contenido": p.contenido_litros}
        for i, (m, c) in enumerate(p.materiales):
            inicial |= {f"material_{i}": str(m), f"cantidad_{i}": c}
        return inicial
