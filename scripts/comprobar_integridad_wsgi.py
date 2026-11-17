"""Compara todas las tablas del respaldo original sin exponer sus filas."""

import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vetcare.config import Config
from vetcare.db import Database
from vetcare.maintenance import encode


# Compara filas con un respaldo privado y guarda únicamente el resultado de integridad.
def compare(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        backup = json.load(stream)
    database = Database(Config.load())
    result = {}
    with database.lease() as db:
        for name, table in backup["tables"].items():
            quoted = "`" + name.replace("`", "``") + "`"
            columns = table["columns"]
            rows = db.all(
                "SELECT "
                + ",".join("`" + n.replace("`", "``") + "`" for n in columns)
                + " FROM "
                + quoted
                + " ORDER BY 1"
            )
            current = json.loads(
                json.dumps(
                    [[r[k] for k in columns] for r in rows],
                    default=encode,
                    ensure_ascii=False,
                )
            )

            # Se ordenan por PK para neutralizar el orden de lectura del respaldo.
            # Ordena registros serializados para comparar respaldos sin depender del orden físico.
            def sort(records):
                return sorted(
                    records, key=lambda row: json.dumps(row, ensure_ascii=False)
                )

            result[name] = {
                "registros_antes": len(table["rows"]),
                "registros_despues": len(rows),
                "identica": sort(table["rows"]) == sort(current),
            }
    database.close()
    (Config.load().root / "docs/evidencias/wsgi_integridad_completa.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(
        "Tablas idénticas:",
        sum(t["identica"] for t in result.values()),
        "de",
        len(result),
    )
    if not all(t["identica"] for t in result.values()):
        raise SystemExit("Hay diferencias; revisa el informe sin datos personales.")


if __name__ == "__main__":
    compare(Path(sys.argv[1]))
