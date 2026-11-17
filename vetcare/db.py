# Pool SQL por proceso, consultas parametrizadas y control de transacciones.
import os
import queue
import time
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor


class Database:
    """Pool por proceso. Nunca reenvía SQL tras una conexión perdida."""

    # Prepara los slots del pool de conexiones por proceso.
    def __init__(self, config):
        self.config = config
        self.pool = queue.LifoQueue(maxsize=config.pool_size)
        for _ in range(config.pool_size):
            self.pool.put(None)

    # Abre una conexión PyMySQL con tiempos límite, charset y aislamiento READ COMMITTED.
    def connect(self, database=True, multi=False):
        options = dict(
            host=os.environ["MYSQLHOST"],
            port=int(os.environ["MYSQLPORT"]),
            user=os.environ["MYSQLUSER"],
            password=os.environ["MYSQLPASSWORD"],
            charset="utf8mb4",
            autocommit=True,
            cursorclass=DictCursor,
            connect_timeout=10,
            read_timeout=30,
            write_timeout=30,
            init_command="SET time_zone='+00:00'",
        )
        if database:
            options["database"] = self.config.database
        if multi:
            options["client_flag"] = pymysql.constants.CLIENT.MULTI_STATEMENTS
        if os.getenv("MYSQL_SSL_CA"):
            options["ssl"] = {"ca": os.environ["MYSQL_SSL_CA"], "check_hostname": True}
        for attempt in range(2):
            try:
                connection = pymysql.connect(**options)
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED"
                        )
                        cursor.execute(
                            "SET SESSION sql_mode='STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'"
                        )
                except BaseException:
                    if connection.open:
                        connection.close()
                    raise
                return connection
            except pymysql.OperationalError as exc:
                if attempt or exc.args[0] not in (2006, 2013):
                    raise
                time.sleep(0.1)

    # Presta una conexión, comprueba conexiones antiguas y descarta sockets cerrados al devolverla.
    @contextmanager
    def lease(self):
        try:
            item = self.pool.get(timeout=35)
        except queue.Empty:
            raise TimeoutError("Pool de conexiones ocupado") from None
        connection = None
        try:
            if item:
                connection, last = item
                if time.monotonic() - last > 30:
                    try:
                        connection.ping(reconnect=False)
                    except pymysql.Error:
                        if connection.open:
                            connection.close()
                        connection = None
            if connection is None:
                connection = self.connect()
            yield SQL(connection)
        except pymysql.Error:
            if connection:
                if connection.open:
                    connection.close()
                connection = None
            raise
        finally:
            # La capa HTTP puede haber manejado la excepción antes de cerrar
            # el contexto; nunca devolver un socket ya cerrado al pool.
            if connection and not connection.open:
                connection = None
            if connection:
                try:
                    if (
                        connection.server_status
                        & pymysql.constants.SERVER_STATUS.SERVER_STATUS_IN_TRANS
                    ):
                        connection.rollback()
                    if not connection.get_autocommit():
                        connection.autocommit(True)
                except pymysql.Error:
                    if connection.open:
                        connection.close()
                    connection = None
            self.pool.put((connection, time.monotonic()) if connection else None)

    # Cierra las conexiones disponibles del pool.
    def close(self):
        while not self.pool.empty():
            item = self.pool.get_nowait()
            if item:
                if item[0].open:
                    item[0].close()


class SQL:
    # Envuelve una conexión y comienza su contador de consultas.
    def __init__(self, connection):
        self.connection = connection
        self.queries = 0

    # Ejecuta una consulta parametrizada y devuelve sus filas como diccionarios.
    def all(self, statement, params=()):
        self.queries += 1
        with self.connection.cursor() as c:
            c.execute(statement, params)
            return list(c.fetchall())

    # Devuelve la primera fila o None.
    def one(self, statement, params=()):
        rows = self.all(statement, params)
        return rows[0] if rows else None

    # Ejecuta una sentencia parametrizada y devuelve el identificador insertado.
    def execute(self, statement, params=()):
        self.queries += 1
        with self.connection.cursor() as c:
            c.execute(statement, params)
            return c.lastrowid

    # Ejecuta un lote parametrizado para evitar inserciones individuales innecesarias.
    def many(self, statement, rows):
        self.queries += 1
        with self.connection.cursor() as c:
            c.executemany(statement, rows)

    # Inicia una transacción y decide COMMIT o ROLLBACK según el resultado.
    @contextmanager
    def atomic(self):
        self.connection.begin()
        try:
            yield self
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise


# Construye INSERT con identificadores internos y parámetros para todos los valores.
def insert(db, table, values):
    # Los identificadores vienen solo de constantes internas, jamás de JSON o URLs.
    fields = ",".join("`" + key + "`" for key in values)
    return db.execute(
        f"INSERT INTO `{table}` ({fields}) VALUES ({','.join(['%s'] * len(values))})",
        tuple(values.values()),
    )


# Actualiza campos internos de una fila identificada por su clave primaria.
def update(db, table, values, pk, pk_name="id"):
    fields = ",".join("`" + key + "`=%s" for key in values)
    db.execute(
        f"UPDATE `{table}` SET {fields} WHERE `{pk_name}`=%s", (*values.values(), pk)
    )
