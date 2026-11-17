"""Arranque real de Gunicorn en Linux, exclusivamente con una base test_vetcare_."""

import argparse
import gzip
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent


# Simula la entrada por el proxy HTTPS sin exponer tokens ni contenido privado.
def request(port, path, headers=None):
    req = Request(
        f"http://127.0.0.1:{port}" + path,
        headers={"X-Forwarded-Proto": "https", **(headers or {})},
    )
    try:
        with urlopen(req, timeout=15) as response:
            return response.status, dict(response.headers), response.read()
    except HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


# Lanza y detiene sólo el proceso de prueba; las credenciales quedan en memoria.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--state-file", type=Path, required=True)
    args = parser.parse_args()
    values = {
        k: v
        for k, v in dotenv_values(args.env_file, interpolate=False).items()
        if v is not None
    }
    state = json.loads(args.state_file.read_text(encoding="utf-8"))
    database = state["database"]
    if not database.startswith("test_vetcare_") or database == values.get(
        "MYSQLDATABASE"
    ):
        raise RuntimeError(
            "La prueba requiere una base aislada y distinta de la operativa."
        )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="vetcare_linux_web_") as folder:
        env = {
            **os.environ,
            **values,
            "MYSQLDATABASE": database,
            "VETCARE_PRODUCTION": "true",
            "VETCARE_SERVICE": "web",
            "VETCARE_ALLOWED_HOSTS": "127.0.0.1,localhost",
            "MEDIA_ROOT": str(Path(folder) / "media"),
            "PORT": str(port),
            "WEB_CONCURRENCY": "2",
            "WEB_THREADS": "2",
            "DB_POOL_SIZE": "3",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        logfile = Path(folder) / "gunicorn.log"
        with logfile.open("w", encoding="utf-8") as output:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "gunicorn",
                    "--config",
                    "gunicorn.conf.py",
                    "vetcare.wsgi:application",
                ],
                cwd=ROOT,
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 45
                while True:
                    try:
                        if request(port, "/health/live/")[0] == 200:
                            break
                    except (URLError, OSError):
                        pass
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError(
                            "Gunicorn no completó el arranque de prueba."
                        )
                    time.sleep(0.3)
                statuses = {}
                for path, expected in [
                    ("/health/ready/", 200),
                    ("/", 200),
                    ("/adopciones/", 200),
                    ("/api/clientes", 401),
                ]:
                    status, _, _ = request(port, path)
                    if status != expected:
                        raise RuntimeError("Respuesta HTTP inesperada en " + path)
                    statuses[path] = status
                status, headers, content = request(
                    port, "/static/js/clinic.js", {"Accept-Encoding": "gzip"}
                )
                if status != 200 or headers.get("Content-Encoding") != "gzip":
                    raise RuntimeError("No se sirve la variante gzip.")
                if (
                    gzip.decompress(content)
                    != (ROOT / "frontend/assets/js/clinic.js").read_bytes()
                ):
                    raise RuntimeError(
                        "El recurso comprimido no coincide con su fuente."
                    )
                status, _, _ = request(
                    port,
                    "/static/js/clinic.js",
                    {"Accept-Encoding": "gzip", "If-None-Match": headers["ETag"]},
                )
                if status != 304:
                    raise RuntimeError("La revalidación ETag no funciona.")
                report = {
                    "plataforma": sys.platform,
                    "python": sys.version.split()[0],
                    "gunicorn_workers": 2,
                    "base_aislada": True,
                    "rutas": statuses,
                    "gzip_validado": True,
                    "etag_304": True,
                    "correos_enviados": 0,
                }
                destination = ROOT / "docs/evidencias/linux-gunicorn.json"
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
                print(json.dumps(report))
            finally:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            "Prueba Linux no completada: "
            + type(exc).__name__
            + ". No se muestran secretos.",
            file=sys.stderr,
        )
        raise SystemExit(1)
