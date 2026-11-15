"""Copias privadas y comprobación de datos; no publica filas ni contraseñas."""

import base64
import gzip
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path


def encode(value):
    if isinstance(value, bytes):
        return {"__bytes__": base64.b64encode(value).decode()}
    return str(value)


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
        print("Copia SQL privada creada:", target)
    else:
        target = database.config.root / "docs" / ("integridad_wsgi_" + stamp + ".json")
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print("Inventario sin datos personales:", target)
    return output
