# Configura el servidor Linux que publica VetCare y mantiene el monitor de citas.
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
# Recicla procesos de larga duración sin cambiar la identidad de sesión del master.
max_requests = 1000
max_requests_jitter = 100
capture_output = True
accesslog = "-"
errorlog = "-"
# Evita registrar query strings con parámetros o posibles datos privados.
access_log_format = "%(h)s %(m)s %(U)s %(s)s %(L)s"


# Activa el monitor de citas con el pool del proceso de Gunicorn recién iniciado.
def post_worker_init(worker):
    from vetcare.services.scheduler import start_monitor

    worker.vetcare_agenda_monitor = start_monitor(worker.wsgi.database)


# Detiene el monitor de agenda al finalizar ese proceso.
def worker_exit(server, worker):
    from vetcare.services.scheduler import stop_monitor

    monitor = getattr(worker, "vetcare_agenda_monitor", None)
    if monitor:
        stop_monitor(monitor)
