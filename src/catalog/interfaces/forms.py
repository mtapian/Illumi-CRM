from django import forms

from catalog.domain.isc import ESPECIFICO
from catalog.domain.producto import CASILLAS, DatosProducto
from catalog.domain.receta import Receta
from catalog.domain.tipos import TipoProducto

# Pestañas de la ficha (RF-CAT-04, 39): clave, etiqueta, orden y la casilla que la muestra.
# "bien" = solo bienes. Las externas usan otro orden (p. ej. Compras = 30).
PESTANAS = [
    ("general", "General", 10, None),
    ("ventas", "Ventas", 20, "se_vende"),
    ("inventario", "Inventario", 40, "bien"),
    ("produccion", "Producción", 50, "se_fabrica"),
]
ENCABEZADO = ("tipo", *CASILLAS)  # van arriba de las pestañas (RF-CAT-38)
_PESTANA_DE = {
    "precio_venta": "ventas",
    "afecto_isc": "ventas",
    "isc_codigo_tipo_sistema": "ventas",
    "contenido_litros": "ventas",
    "tasa_monto": "ventas",
    "tasa_desde": "ventas",
    "stock_minimo": "inventario",
    "vida_util_dias": "inventario",
    "peso_kg": "inventario",
    "volumen_m3": "inventario",
}


class ProductoForm(forms.Form):
    """Todos los campos van en el formulario; las pestañas se muestran según el tipo y las
    casillas (CSS `:has`, sin JS) y el dominio descarta lo que no corresponde."""

    tipo = forms.ChoiceField(
        choices=[(TipoProducto.BIEN, "Bien"), (TipoProducto.SERVICIO, "Servicio")],
        widget=forms.RadioSelect,
        initial=TipoProducto.BIEN,
    )
    se_vende = forms.BooleanField(label="Se vende", required=False)
    se_compra = forms.BooleanField(label="Se compra", required=False, initial=True)
    se_fabrica = forms.BooleanField(label="Se fabrica", required=False)
    sku = forms.CharField(label="SKU", max_length=40)
    nombre = forms.CharField(max_length=200)
    unidad = forms.ChoiceField()
    categoria = forms.ChoiceField(label="Categoría", required=False)
    marca = forms.ChoiceField(required=False)
    referencia = forms.CharField(label="Referencia interna", max_length=60, required=False)
    codigo_barras = forms.CharField(label="Código de barras", max_length=40, required=False)
    precio_venta = forms.DecimalField(
        label="Precio de lista (con IGV e ISC)", decimal_places=2, required=False
    )
    # ISC en la ficha (RF-CAT-45, 46): Sistema Específico, S/ por litro.
    afecto_isc = forms.BooleanField(label="Afecto a ISC (Sistema Específico)", required=False)
    isc_codigo_tipo_sistema = forms.CharField(
        label="Código de tipo de sistema", max_length=2, required=False
    )
    contenido_litros = forms.DecimalField(
        label="Litros por unidad (unidad de control)",
        decimal_places=4,
        required=False,
        help_text="Botella 330 ml = 0.33; caja de 12 × 330 ml = 3.96",
    )
    tasa_monto = forms.DecimalField(
        label="Nueva tasa (S/ por litro)", decimal_places=4, required=False
    )
    tasa_desde = forms.DateField(
        label="Vigente desde", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    stock_minimo = forms.DecimalField(
        label="Stock mínimo", decimal_places=4, initial=0, min_value=0, required=False
    )
    vida_util_dias = forms.IntegerField(
        label="Vida útil (días)",
        required=False,
        min_value=1,
        help_text="Solo sugiere el vencimiento del lote al ingresar o producir",
    )
    peso_kg = forms.DecimalField(label="Peso (kg)", decimal_places=4, required=False, min_value=0)
    volumen_m3 = forms.DecimalField(
        label="Volumen (m³)", decimal_places=6, required=False, min_value=0
    )

    FILAS_RECETA = 8

    def __init__(
        self,
        *args,
        unidades,
        categorias=(),
        marcas=(),
        componentes=(),
        bloqueados=(),
        **kw,
    ):
        super().__init__(*args, **kw)
        # `unidades`: (abreviatura, nombre) → "Unidad (UND)", como en la referencia del PO.
        self.fields["unidad"].choices = [(a, f"{n} ({a})") for a, n in unidades]
        self.fields["categoria"].choices = [("", "— Sin categoría —")] + [
            (str(i), n) for i, n in categorias
        ]
        self.fields["marca"].choices = [("", "— Sin marca —")] + [(str(i), n) for i, n in marcas]
        opciones = [("", "—")] + [(str(i), n) for i, n in componentes]
        for i in range(self.FILAS_RECETA):  # receta opcional (RF-CAT-41)
            self.fields[f"componente_{i}"] = forms.ChoiceField(
                label=f"Componente {i + 1}", choices=opciones, required=False
            )
            self.fields[f"cantidad_{i}"] = forms.DecimalField(
                label="Cantidad por unidad", decimal_places=4, required=False
            )
        for campo in ENCABEZADO:  # van fuera del <form>, arriba de las pestañas
            self.fields[campo].widget.attrs["form"] = "ficha"
        for campo in bloqueados:  # RF-CAT-43: con movimientos se muestran con candado
            if campo in self.fields:
                self.fields[campo].disabled = True
                self.fields[campo].label = f"🔒 {self.fields[campo].label or campo.capitalize()}"

    def _valor(self, campo):
        if self.is_bound:
            return self[campo].value()
        return self.initial.get(campo, self.fields[campo].initial)

    def casillas_activas(self) -> set[str]:
        """Estado actual (lo enviado o lo guardado): qué pestañas se ven al cargar."""
        activas = {c for c in CASILLAS if self._valor(c)}
        return activas | ({"bien"} if self._valor("tipo") != TipoProducto.SERVICIO else set())

    def encabezado(self):
        return [self[c] for c in ENCABEZADO]

    def pestanas(self) -> list[dict]:
        campos = {}
        for f in self:
            if f.name in ENCABEZADO:
                continue
            receta = f.name.startswith(("componente_", "cantidad_"))
            clave = "produccion" if receta else _PESTANA_DE.get(f.name, "general")
            campos.setdefault(clave, []).append(f)
        activas = self.casillas_activas()
        return [
            {
                "clave": c,
                "etiqueta": e,
                "orden": o,
                "casilla": casilla,
                "activa": casilla is None or casilla in activas,
                "campos": campos[c],
                "errores": any(f.errors for f in campos[c]),
            }
            for c, e, o, casilla in PESTANAS
        ]

    def datos(self) -> DatosProducto:
        c = self.cleaned_data
        categoria, marca = c.get("categoria"), c.get("marca")
        return DatosProducto(
            sku=c["sku"],
            nombre=c["nombre"],
            tipo=TipoProducto(c["tipo"]),
            unidad=c["unidad"],
            se_vende=c["se_vende"],
            se_compra=c["se_compra"],
            se_fabrica=c["se_fabrica"],
            categoria_id=int(categoria) if categoria else None,
            marca_id=int(marca) if marca else None,
            stock_minimo=c.get("stock_minimo") or 0,
            precio_venta=c.get("precio_venta"),
            isc_sistema=ESPECIFICO if c.get("afecto_isc") else None,
            isc_codigo_tipo_sistema=c.get("isc_codigo_tipo_sistema", ""),
            contenido_litros=c.get("contenido_litros"),
            vida_util_dias=c.get("vida_util_dias"),
            peso_kg=c.get("peso_kg"),
            volumen_m3=c.get("volumen_m3"),
            referencia=c.get("referencia", ""),
            codigo_barras=c.get("codigo_barras", ""),
        )

    def tasa(self):
        """(monto, desde) de una tasa nueva, o None si no se ingresó (RF-CAT-46)."""
        c = self.cleaned_data
        if c.get("tasa_monto") is None and c.get("tasa_desde") is None:
            return None
        return c.get("tasa_monto"), c.get("tasa_desde")

    def receta(self) -> Receta | None:
        """None si no se fabrica: la receta guardada no se toca (enmienda 4)."""
        c = self.cleaned_data
        if not c.get("se_fabrica"):
            return None
        return tuple(
            (int(c[f"componente_{i}"]), c[f"cantidad_{i}"])
            for i in range(self.FILAS_RECETA)
            if c.get(f"componente_{i}")
        )

    @staticmethod
    def inicial_receta(receta: Receta) -> dict:
        inicial = {}
        for i, (m, q) in enumerate(receta):
            inicial |= {f"componente_{i}": str(m), f"cantidad_{i}": q}
        return inicial
