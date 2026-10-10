from django.core.mail.backends.base import BaseEmailBackend


class Backend(BaseEmailBackend):
    def send_messages(self, email_messages):
        raise OSError("servidor SMTP caído")
