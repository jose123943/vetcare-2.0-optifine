"""Configuración y autenticación de Gmail sin enviar a buzones externos."""

import io
import os
import smtplib
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from dotenv import dotenv_values

from scripts import configurar_gmail
from scripts.configurar_gmail import gmail_values, save_configuration
from vetcare.services.mail import (
    MailConfigurationError,
    check_smtp_connection,
    mail_error,
    smtp_settings,
)


class GmailTests(unittest.TestCase):
    def values(self):
        return gmail_values("sender@example.invalid", "abcd efgh ijkl mnop")

    def test_private_configuration_preserves_database_and_signing_key(self):
        with tempfile.TemporaryDirectory(prefix="vetcare_gmail_") as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "MYSQLPASSWORD='synthetic-database-secret'\nVETCARE_SECRET_KEY='synthetic-signing-secret-unchanged'\n",
                encoding="utf-8",
            )
            save_configuration(path, self.values())
            values = dotenv_values(path, interpolate=False)
            self.assertEqual(values["MYSQLPASSWORD"], "synthetic-database-secret")
            self.assertEqual(
                values["VETCARE_SECRET_KEY"], "synthetic-signing-secret-unchanged"
            )
            self.assertEqual(values["EMAIL_HOST"], "smtp.gmail.com")
            self.assertEqual(values["EMAIL_HOST_PASSWORD"], "abcdefghijklmnop")
            self.assertEqual(
                values["DEFAULT_FROM_EMAIL"], "VetCare <sender@example.invalid>"
            )

    def test_incomplete_password_is_rejected(self):
        for password in ("", "*", "regular-short", "a" * 17):
            with self.assertRaises(MailConfigurationError):
                gmail_values("sender@example.invalid", password)

    def test_missing_account_fails_before_network(self):
        values = self.values()
        values["EMAIL_HOST_USER"] = ""
        with (
            patch.dict(os.environ, values),
            patch("vetcare.services.mail.smtplib.SMTP") as factory,
        ):
            with self.assertRaises(MailConfigurationError):
                check_smtp_connection()
            factory.assert_not_called()

    def test_rejects_insecure_or_inconsistent_gmail_transport(self):
        for changed in [
            {"EMAIL_USE_TLS": "false"},
            {"EMAIL_USE_SSL": "true"},
            {"EMAIL_PORT": "not-a-port"},
            {"DEFAULT_FROM_EMAIL": "other@example.invalid"},
        ]:
            with patch.dict(os.environ, {**self.values(), **changed}):
                with self.assertRaises(MailConfigurationError):
                    smtp_settings()

    def test_authentication_check_uses_tls_and_never_sends(self):
        server = MagicMock()
        server.noop.return_value = (250, b"OK")
        with (
            patch.dict(os.environ, self.values()),
            patch("vetcare.services.mail.smtplib.SMTP") as factory,
        ):
            factory.return_value.__enter__.return_value = server
            check_smtp_connection()
            factory.assert_called_once_with(host="smtp.gmail.com", port=587, timeout=15)
            server.starttls.assert_called_once()
            self.assertTrue(server.starttls.call_args.kwargs["context"].check_hostname)
            server.login.assert_called_once_with(
                "sender@example.invalid", "abcdefghijklmnop"
            )
            server.noop.assert_called_once()
            server.send_message.assert_not_called()
            server.sendmail.assert_not_called()
            self.assertLess(
                [c[0] for c in server.method_calls].index("starttls"),
                [c[0] for c in server.method_calls].index("login"),
            )

    def test_diagnostics_hide_provider_responses(self):
        private = "sensitive-provider-detail@example.invalid"
        for error in [
            smtplib.SMTPAuthenticationError(535, private.encode()),
            smtplib.SMTPDataError(550, private.encode()),
            RuntimeError(private),
        ]:
            message = mail_error(error)
            self.assertNotIn(private, message)
            self.assertLessEqual(len(message), 250)
        self.assertIn(
            "contraseña de aplicación",
            mail_error(smtplib.SMTPAuthenticationError(535, b"bad")),
        )

    def test_assistant_does_not_save_credentials_rejected_by_google(self):
        with tempfile.TemporaryDirectory(prefix="vetcare_gmail_") as directory:
            root = Path(directory)
            path = root / ".env"
            path.write_text(
                "MYSQLPASSWORD=synthetic-original-secret\n", encoding="utf-8"
            )
            before = path.read_bytes()
            output = io.StringIO()
            with (
                patch.dict(os.environ, {}),
                patch.object(configurar_gmail, "ROOT", root),
                patch("builtins.input", return_value="sender@example.invalid"),
                patch.object(
                    configurar_gmail.getpass, "getpass", return_value="abcdefghijklmnop"
                ),
                patch.object(configurar_gmail.sys.stdin, "isatty", return_value=True),
                patch.object(
                    configurar_gmail,
                    "check_smtp_connection",
                    side_effect=smtplib.SMTPAuthenticationError(
                        535, b"private-response"
                    ),
                ),
                redirect_stdout(output),
            ):
                with self.assertRaises(smtplib.SMTPAuthenticationError):
                    configurar_gmail.main([])
            self.assertEqual(path.read_bytes(), before)
            self.assertNotIn("abcdefghijklmnop", output.getvalue())

    def test_assistant_saves_only_after_authentication_succeeds(self):
        with tempfile.TemporaryDirectory(prefix="vetcare_gmail_") as directory:
            root = Path(directory)
            path = root / ".env"
            path.write_text(
                "MYSQLPASSWORD=synthetic-original-secret\n", encoding="utf-8"
            )
            output = io.StringIO()

            def verify_before_save():
                self.assertNotIn(
                    "EMAIL_HOST_PASSWORD", dotenv_values(path, interpolate=False)
                )

            with (
                patch.dict(os.environ, {}),
                patch.object(configurar_gmail, "ROOT", root),
                patch("builtins.input", return_value="sender@example.invalid"),
                patch.object(
                    configurar_gmail.getpass,
                    "getpass",
                    return_value="abcd efgh ijkl mnop",
                ),
                patch.object(configurar_gmail.sys.stdin, "isatty", return_value=True),
                patch.object(
                    configurar_gmail,
                    "check_smtp_connection",
                    side_effect=verify_before_save,
                ),
                redirect_stdout(output),
            ):
                self.assertEqual(configurar_gmail.main([]), 0)
            saved = dotenv_values(path, interpolate=False)
            self.assertEqual(saved["EMAIL_HOST_PASSWORD"], "abcdefghijklmnop")
            self.assertEqual(saved["MYSQLPASSWORD"], "synthetic-original-secret")
            self.assertNotIn("abcdefghijklmnop", output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
