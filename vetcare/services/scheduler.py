# Monitor peri?dico de citas finalizadas, independiente del correo.
"""Finalización periódica de citas, independiente del transporte de correo."""

import logging
from threading import Event, Thread

from .clinic import complete_finished_appointments

logger = logging.getLogger("vetcare")


# Inicia el monitor de agenda cada 15 segundos, independiente del correo.
def start_monitor(database, interval=15):
    stopped = Event()

    # Actualiza citas finalizadas y registra fallos sin secretos; continúa tras errores temporales.
    def run():
        while not stopped.is_set():
            try:
                with database.lease() as db:
                    complete_finished_appointments(db)
            except Exception as exc:
                logger.warning("Actualización de agenda: %s", type(exc).__name__)
            stopped.wait(interval)

    thread = Thread(target=run, name="vetcare-agenda", daemon=True)
    thread.start()
    return stopped, thread


# Señala la detención del monitor al cerrar el servidor y espera su finalización.
def stop_monitor(monitor):
    stopped, thread = monitor
    stopped.set()
    thread.join(timeout=5)
