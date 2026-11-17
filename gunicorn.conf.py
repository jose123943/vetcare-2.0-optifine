import os
import secrets

# Se ejecuta en el master antes de cargar/forkear la aplicación.
os.environ["_VETCARE_SESSION_RUN_ID"] = secrets.token_hex(32)

bind = "0.0.0.0:" + os.environ.get("PORT", "8000")
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
worker_class = "gthread"
threads = int(os.environ.get("WEB_THREADS", "4"))
timeout = 60
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
# Evita registrar query strings con parámetros o posibles datos privados.
access_log_format = "%(h)s %(m)s %(U)s %(s)s %(L)s"
