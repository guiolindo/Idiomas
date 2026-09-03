"""Backend de e-mail que fala com a API HTTP do Resend (https://api.resend.com/emails)
em vez de SMTP.

Por quê: em produção (Railway), a conexão SMTP com smtp.resend.com:465 fica pendurada
(nunca conecta nem dá erro) até o worker do gunicorn matar a requisição à força —
o usuário via só um "Internal Server Error" cru, sem nenhum traceback do Django, porque
o processo morria antes de conseguir responder. A API HTTP evita esse socket problemático
por completo e ainda responde bem mais rápido.
"""
import httpx
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendAPIBackend(BaseEmailBackend):
    api_url = "https://api.resend.com/emails"
    timeout = 10

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = settings.RESEND_API_KEY
        sent = 0
        with httpx.Client(timeout=self.timeout) as client:
            for message in email_messages:
                payload = {
                    "from": message.from_email,
                    "to": list(message.to),
                    "subject": message.subject,
                    "text": message.body,
                }
                if message.cc:
                    payload["cc"] = list(message.cc)
                if message.bcc:
                    payload["bcc"] = list(message.bcc)

                html_body = None
                for content, mimetype in getattr(message, "alternatives", []):
                    if mimetype == "text/html":
                        html_body = content
                        break
                if html_body:
                    payload["html"] = html_body

                try:
                    response = client.post(
                        self.api_url,
                        headers={"Authorization": f"Bearer {api_key}"},
                        json=payload,
                    )
                    response.raise_for_status()
                    sent += 1
                except httpx.HTTPError:
                    if not self.fail_silently:
                        raise
        return sent
