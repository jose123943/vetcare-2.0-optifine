# Comprueba el envío de un correo a un receptor local que simula un servidor SMTP.
"""Envía MIME por un socket SMTP local real, sin destinatarios externos."""

import os
import socketserver
import threading
import unittest
from email import policy
from email.parser import BytesParser
from unittest.mock import patch

from vetcare.services.mail import make_message, smtp_send


# Simula un servidor de correo y conserva los mensajes solamente en memoria.
class Receiver(socketserver.StreamRequestHandler):
    # Responde al protocolo de correo para que la prueba no necesite contactar con Internet.
    def handle(self):
        self.wfile.write(b"220 localhost SMTP test\r\n")
        while raw := self.rfile.readline():
            verb = raw.split(b" ", 1)[0].strip().upper()
            if verb in (b"EHLO", b"HELO"):
                self.wfile.write(b"250 localhost\r\n")
            elif verb in (b"MAIL", b"RCPT", b"RSET", b"NOOP"):
                self.wfile.write(b"250 OK\r\n")
            elif verb == b"DATA":
                self.wfile.write(b"354 Send message\r\n")
                body = []
                while line := self.rfile.readline():
                    if line == b".\r\n":
                        break
                    body.append(line[1:] if line.startswith(b"..") else line)
                self.server.messages.append(b"".join(body))
                self.wfile.write(b"250 Accepted\r\n")
            elif verb == b"QUIT":
                self.wfile.write(b"221 Bye\r\n")
                return
            else:
                self.wfile.write(b"502 Command not supported\r\n")


# Agrupa las pruebas de envío mediante un receptor local.
class SMTPTests(unittest.TestCase):
    # Comprueba el correo completo contra un receptor local, sin destinatarios externos.
    def test_real_smtp_transport_on_loopback(self):
        with socketserver.ThreadingTCPServer(("127.0.0.1", 0), Receiver) as receiver:
            receiver.messages = []
            worker = threading.Thread(target=receiver.serve_forever, daemon=True)
            worker.start()
            try:
                with patch.dict(
                    os.environ,
                    {
                        "EMAIL_HOST": "127.0.0.1",
                        "EMAIL_PORT": str(receiver.server_address[1]),
                        "EMAIL_USE_TLS": "false",
                        "EMAIL_USE_SSL": "false",
                        "EMAIL_HOST_USER": "",
                        "EMAIL_HOST_PASSWORD": "",
                        "DEFAULT_FROM_EMAIL": "sender@example.invalid",
                    },
                ):
                    message = make_message(
                        {
                            "id": 1,
                            "asunto": "Cita de prueba",
                            "destinatario": "recipient@example.invalid",
                            "contexto": {
                                "cliente": "Familia sintética",
                                "mascota": "Paciente",
                                "fecha": "2027-01-01",
                                "hora": "10:00",
                                "veterinario": "Profesional",
                                "motivo": "Consulta <script>",
                                "estado": "Pendiente",
                            },
                        }
                    )
                    smtp_send(message)
                self.assertEqual(len(receiver.messages), 1)
                received = BytesParser(policy=policy.default).parsebytes(
                    receiver.messages[0]
                )
                self.assertEqual(received["To"], "recipient@example.invalid")
                self.assertIn(
                    "Paciente",
                    received.get_body(preferencelist=("plain",)).get_content(),
                )
                self.assertIn(
                    "&lt;script&gt;",
                    received.get_body(preferencelist=("html",)).get_content(),
                )
            finally:
                receiver.shutdown()
                worker.join(timeout=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
