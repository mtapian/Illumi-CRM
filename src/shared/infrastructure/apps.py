from django.apps import AppConfig


class SharedConfig(AppConfig):
    name = "shared.infrastructure"
    label = "shared"
    verbose_name = "Shared kernel"
