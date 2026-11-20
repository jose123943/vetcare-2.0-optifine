# Revisa los archivos de publicación; --con-base también comprueba MySQL.
"""Revisa estructura y despliegue; la comprobación opcional de MySQL es sólo lectura."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# Valida las referencias estáticas, Railway y la copia selectiva del Dockerfile.
def check_source(root=ROOT):
    # Contrasta referencias reales de HTML/bootstrap con los archivos publicados.
    missing = []
    assets = root / "frontend/assets"
    for html in (root / "frontend/pages").glob("*.html"):
        for name in re.findall(
            r'/static/([^\s"<>?]+)', html.read_text(encoding="utf-8")
        ):
            if not (assets / name).is_file():
                missing.append(name)
    bootstrap = (assets / "js/bootstrap.js").read_text(encoding="utf-8")
    for name in re.findall(r"load\(\s*['\"]([^'\"]+)['\"]", bootstrap):
        if not (assets / name).is_file():
            missing.append(name)
    if missing:
        raise RuntimeError(
            "Referencias estáticas inexistentes: " + ", ".join(sorted(set(missing)))
        )
    for filename in ("railway.json", "railway.worker.json"):
        settings = json.loads((root / filename).read_text(encoding="utf-8"))
        if settings["build"]["dockerfilePath"] != "Dockerfile":
            raise RuntimeError(
                "Dockerfile no coincide con la configuración de Railway."
            )
    if "COPY . ." in (root / "Dockerfile").read_text(encoding="utf-8"):
        raise RuntimeError("La imagen debe copiar sólo los directorios de ejecución.")
    return {
        "referencias_estaticas_validas": True,
        "configuracion_railway_valida": True,
        "copia_docker_selectiva": True,
    }


# Comprueba MySQL y los checksums aplicados mediante consultas de sólo lectura.
def check_database():
    # Lee el estado del esquema sin aplicar migraciones, crear sesiones ni enviar correo.
    from vetcare.config import Config
    from vetcare.db import Database

    config = Config.load()
    database = Database(config)
    try:
        with database.lease() as db:
            db.one("SELECT 1 AS ok")
            applied = {
                row["name"]: row["sha256"]
                for row in db.all("SELECT name,sha256 FROM vc_schema_migration")
            }
            expected = {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (ROOT / "sql").glob("*.sql")
            }
            if any(applied.get(name) != digest for name, digest in expected.items()):
                raise RuntimeError(
                    "Hay migraciones pendientes o checksums distintos; revisar antes de desplegar."
                )
        return {
            "mysql_disponible": True,
            "migraciones_verificadas": len(expected),
            "produccion": config.production,
        }
    finally:
        database.close()


# Ejecuta la revisión estática y, opcionalmente, la comprobación de base sin publicar ni modificar datos.
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--con-base",
        action="store_true",
        help="Comprueba MySQL mediante consultas de sólo lectura.",
    )
    args = parser.parse_args(argv)
    report = check_source()
    if args.con_base:
        report.update(check_database())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            "Revisión no completada: "
            + type(exc).__name__
            + ". No se muestran secretos.",
            file=sys.stderr,
        )
        raise SystemExit(1)
