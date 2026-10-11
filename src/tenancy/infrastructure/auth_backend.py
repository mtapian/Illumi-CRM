from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Autentica por email. Los usuarios técnicos no inician sesión (spec 0001d)."""

    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and not user.es_tecnico
