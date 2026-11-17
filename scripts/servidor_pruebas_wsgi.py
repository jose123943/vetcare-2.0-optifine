"""Servidor del navegador limitado a la base aislada creada por las pruebas."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from waitress import serve
from vetcare.application import create_app
from vetcare.config import Config

state = Path(tempfile.gettempdir()) / "vetcare_wsgi_test_database.json"
if not state.exists():
    raise SystemExit("Ejecuta primero scripts/probar_wsgi.py.")
info = json.loads(state.read_text(encoding="utf-8"))
config = Config.load(database=info["database"], testing=True)
config.media = Path(info["media"])
config.session_run_id = info.get("session_run_id", config.session_run_id)
print("Navegador de pruebas: http://127.0.0.1:8001 (base aislada)", flush=True)
serve(create_app(config), host="127.0.0.1", port=8001, threads=config.pool_size)
