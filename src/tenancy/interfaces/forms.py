from django import forms
from django.contrib.auth.password_validation import validate_password


class RegistroForm(forms.Form):
    required_css_class = "requerido"  # obligatorios con * (docs/ux.md §4)
    ruc = forms.CharField(label="RUC", max_length=20)
    razon_social = forms.CharField(label="Razón social", max_length=200)
    nombre_comercial = forms.CharField(label="Nombre comercial", max_length=200, required=False)
    nombre = forms.CharField(label="Tu nombre", max_length=150)
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)


class EmpresaForm(forms.Form):
    required_css_class = "requerido"  # obligatorios con * (docs/ux.md §4)
    """Datos editables de la empresa; el RUC no está (RF-TEN-17)."""

    razon_social = forms.CharField(label="Razón social", max_length=200)
    nombre_comercial = forms.CharField(label="Nombre comercial", max_length=200, required=False)
    direccion_fiscal = forms.CharField(label="Dirección fiscal", max_length=300, required=False)
    ubigeo = forms.CharField(label="Ubigeo", max_length=6, required=False)
    telefono = forms.CharField(label="Teléfono", max_length=30, required=False)
    email = forms.EmailField(label="Email", required=False)
    logo = forms.FileField(label="Logo", required=False)
