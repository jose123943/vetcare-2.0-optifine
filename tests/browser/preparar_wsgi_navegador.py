"""Prepara sólo la base aislada registrada por las pruebas."""

import argparse
import json
import sys
import tempfile
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.support import adoption_pet, client, write
from vetcare.application import create_app
from vetcare.config import Config

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--reset-demo",
    action="store_true",
    help="Reinicia sólo los datos sintéticos de esta base aislada.",
)
args = parser.parse_args()

info = Path(tempfile.gettempdir()) / "vetcare_wsgi_test_database.json"
data = json.loads(info.read_text())
config = Config.load(database=data["database"], testing=True)
config.media = Path(data["media"])
config.session_run_id = data.get("session_run_id", config.session_run_id)
app = create_app(config)
# Reinicia escenarios de navegador sólo tras la validación test_vetcare_ de Config.
if args.reset_demo:
    from vetcare.demo import prepare_demo

    with app.database.lease() as db, db.atomic():
        prepare_demo(db, date(2026, 11, 17))
c = client(app)
with app.database.lease() as db:
    if not db.one("SELECT id_veterinario FROM veterinario LIMIT 1"):
        r = write(
            c,
            "/api/veterinarios",
            dict(
                nombre="Ana",
                apellido="Pruebas",
                telefono="3000000000",
                especialidad="General",
            ),
        )
        assert r.status_code == 200
r = write(c, "/adopciones/api/admin/mascotas/guardar/", adoption_pet())
assert r.status_code == 200, r.json
(Path(tempfile.gettempdir()) / "vetcare_browser_cookie.json").write_text(
    json.dumps(
        {
            "name": "vetcare_sid",
            "sessionid": c.get_cookie("vetcare_sid").value,
            "csrf": c.get_cookie("csrftoken").value,
        }
    )
)
app.database.close()
print("Navegador preparado en base aislada. Cookie sólo en archivo temporal privado.")
