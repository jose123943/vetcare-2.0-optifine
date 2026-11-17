# Respaldos privados consistentes y evidencia de integridad sin datos personales.
"""Copias privadas y comprobación de datos; no publica filas ni contraseñas."""

import base64
import gzip
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path


# Convierte valores especiales para un respaldo lógico JSON.
def encode(value):
    if isinstance(value, bytes):
        return {"__bytes__": base64.b64encode(value).decode()}
    return str(value)


# Captura esquema/filas de forma consistente y verifica el respaldo privado, o genera conteos y hashes sin filas.
def snapshot(database, backup=False):
    output = {}
    tables = {}
    connection = database.connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT")
            cursor.execute("SHOW FULL TABLES WHERE Table_type=%s", ("BASE TABLE",))
            names = [next(iter(row.values())) for row in cursor.fetchall()]
            for name in names:
                quoted = "`" + name.replace("`", "``") + "`"
                cursor.execute("SHOW CREATE TABLE " + quoted)
                schema = list(cursor.fetchone().values())[1]
                cursor.execute("SELECT * FROM " + quoted + " ORDER BY 1")
                raw = list(cursor.fetchall())
                columns = [d[0] for d in cursor.description]
                rows = [[r[k] for k in columns] for r in raw]
                output[name] = {
                    "registros": len(rows),
                    "sha256": hashlib.sha256(
                        json.dumps(rows, default=encode, ensure_ascii=False).encode()
                    ).hexdigest(),
                }
                if backup:
                    tables[name] = {"schema": schema, "columns": columns, "rows": rows}
        connection.rollback()
    finally:
        connection.close()
    stamp = datetime.now(UTC).replace(tzinfo=None).strftime("%Y%m%d_%H%M%S")
    if backup:
        directory = Path(
            os.getenv("VETCARE_BACKUP_DIR") or Path.home() / ".codex/backups/vetcare"
        )
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / ("vetcare_sql_" + stamp + ".json.gz")
        with gzip.open(target, "wt", encoding="utf-8") as stream:
            json.dump(
                {
                    "created_utc": datetime.now(UTC).replace(tzinfo=None).isoformat(),
                    "tables": tables,
                },
                stream,
                ensure_ascii=False,
                default=encode,
            )
        with gzip.open(target, "rt", encoding="utf-8") as stream:
            recovered = json.load(stream)
        if set(recovered["tables"]) != set(tables):
            raise RuntimeError(
                "El respaldo no contiene todas las tablas; no continuar con la limpieza."
            )
        for name, table in recovered["tables"].items():
            digest = hashlib.sha256(
                json.dumps(table["rows"], ensure_ascii=False).encode()
            ).hexdigest()
            if digest != output[name]["sha256"]:
                raise RuntimeError(
                    "El respaldo no coincide con la tabla " + name + "; no continuar."
                )
        print("Copia SQL privada creada y verificada:", target)
    else:
        target = (
            database.config.root
            / "docs/evidencias"
            / ("integridad_wsgi_" + stamp + ".json")
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print("Inventario sin datos personales:", target)
    return output
