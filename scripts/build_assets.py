# Genera copias comprimidas de CSS y JavaScript para cargar la web más rápido.
"""Precomprime CSS/JavaScript de forma reproducible; el código fuente sigue legible."""

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# Genera recursos CSS/JS gzip reproducibles y un manifiesto de tamaños y hashes, sin leer secretos.
def build_assets(root=ROOT):
    # Sólo procesa recursos públicos; nunca examina .env, fotos o la base de datos.
    source = root / "frontend/assets"
    destination = root / "build/static"
    records = []
    for path in sorted(source.rglob("*")):
        if path.suffix not in (".css", ".js") or not path.is_file():
            continue
        raw = path.read_bytes()
        relative = path.relative_to(source)
        target = destination / (relative.as_posix() + ".gz")
        target.parent.mkdir(parents=True, exist_ok=True)
        data = gzip.compress(raw, compresslevel=9, mtime=0)
        target.write_bytes(data)
        records.append(
            {
                "archivo": relative.as_posix(),
                "bytes": len(raw),
                "gzip_bytes": len(data),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    report = {
        "archivos": records,
        "bytes": sum(r["bytes"] for r in records),
        "gzip_bytes": sum(r["gzip_bytes"] for r in records),
    }
    (root / "build").mkdir(exist_ok=True)
    (root / "build/assets.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    result = build_assets()
    print(
        json.dumps(
            {
                "archivos": len(result["archivos"]),
                "bytes": result["bytes"],
                "gzip_bytes": result["gzip_bytes"],
            }
        )
    )
