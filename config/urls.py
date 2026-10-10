from django.urls import include, path

urlpatterns = [
    path("", include("tenancy.interfaces.urls")),
]
