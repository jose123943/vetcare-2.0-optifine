# Migraciones aditivas con bloqueo y verificaci?n de checksums.
import hashlib


# Aplica SQL versionado con lock de esquema y checksum; no repite archivos ya aplicados.
def migrate(database):
    connection = database.connect(multi=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT GET_LOCK(%s,60) AS locked",
                ("vetcare-schema-" + database.config.database,),
            )
            if cursor.fetchone()["locked"] != 1:
                raise RuntimeError("Otra migración sigue en curso.")
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS vc_schema_migration (name VARCHAR(150) PRIMARY KEY,sha256 CHAR(64) NOT NULL,applied DATETIME(6) NOT NULL) ENGINE=InnoDB"
            )
            for path in sorted((database.config.root / "sql").glob("*.sql")):
                source = path.read_bytes()
                checksum = hashlib.sha256(source).hexdigest()
                cursor.execute(
                    "SELECT sha256 FROM vc_schema_migration WHERE name=%s", (path.name,)
                )
                row = cursor.fetchone()
                if row:
                    if row["sha256"] != checksum:
                        raise RuntimeError(
                            "No modifiques migraciones ya aplicadas: " + path.name
                        )
                    continue
                cursor.execute(source.decode("utf-8"))
                while cursor.nextset():
                    pass
                cursor.execute(
                    "INSERT INTO vc_schema_migration(name,sha256,applied) VALUES (%s,%s,UTC_TIMESTAMP(6))",
                    (path.name, checksum),
                )
            cursor.execute(
                "SELECT RELEASE_LOCK(%s)",
                ("vetcare-schema-" + database.config.database,),
            )
    finally:
        connection.close()


# Consulta columnas, tipos y claves de la base activa.
def schema_inventory(db):
    return db.all(
        "SELECT TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_KEY FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME,ORDINAL_POSITION"
    )
