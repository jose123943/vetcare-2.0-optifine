# Comprueba la configuración de publicación y los archivos públicos sin conectar a MySQL.
"""Configuración y recursos de producción; no necesita credenciales ni conexiones SQL."""

import gzip
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from werkzeug.test import Client
from werkzeug.wrappers import Response

from scripts.build_assets import build_assets
from scripts.verificar_despliegue import check_source
from vetcare.application import create_app
from vetcare.config import Config


# Agrupa las comprobaciones de archivos y configuración de publicación.
class DeploymentTests(unittest.TestCase):
    # Prepara el entorno y los datos aislados requeridos por este grupo de pruebas.
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp(prefix="vetcare_assets_test_"))
        source = cls.root / "frontend/assets/js"
        source.mkdir(parents=True)
        (source / "example.js").write_text(
            "// Recurso público de prueba\n" + "const value = 1;\n" * 300,
            encoding="utf-8",
        )
        cls.report = build_assets(cls.root)
        cls.config = Config(
            root=cls.root,
            database="test_vetcare_offline",
            production=True,
            testing=True,
            secret="Synthetic-deployment-test-secret-32",
        )
        cls.app = create_app(cls.config)

    # Cierra los recursos reservados por este grupo de pruebas.
    @classmethod
    def tearDownClass(cls):
        cls.app.database.close()

    # Comprueba las rutas del proyecto y los archivos que se incluyen en Docker.
    def test_01_source_paths_and_selective_docker_copy(self):
        self.assertTrue(check_source()["referencias_estaticas_validas"])

    # Comprueba que un recurso comprimido tenga el mismo contenido que su original.
    def test_02_static_plain_and_gzip_are_equivalent(self):
        c = Client(self.app, Response)
        headers = {"X-Forwarded-Proto": "https"}
        plain = c.get("/static/js/example.js", headers=headers)
        compressed = c.get(
            "/static/js/example.js", headers={**headers, "Accept-Encoding": "gzip"}
        )
        self.assertEqual(plain.status_code, 200)
        self.assertEqual(compressed.status_code, 200)
        self.assertEqual(compressed.headers["Content-Encoding"], "gzip")
        self.assertEqual(gzip.decompress(compressed.data), plain.data)
        self.assertLess(len(compressed.data), len(plain.data))
        self.assertIn("Accept-Encoding", compressed.headers["Vary"])
        self.assertEqual(compressed.mimetype, "text/javascript")
        plain.close()
        compressed.close()

    # Comprueba que se respete el navegador y el modo de desarrollo al comprimir.
    def test_03_gzip_zero_quality_and_development_use_source(self):
        response = Client(self.app, Response).get(
            "/static/js/example.js",
            headers={"X-Forwarded-Proto": "https", "Accept-Encoding": "gzip;q=0"},
        )
        self.assertNotIn("Content-Encoding", response.headers)
        response.close()
        dev = create_app(replace(self.config, production=False))
        try:
            response = Client(dev, Response).get(
                "/static/js/example.js", headers={"Accept-Encoding": "gzip"}
            )
            self.assertNotIn("Content-Encoding", response.headers)
            response.close()
        finally:
            dev.database.close()

    # Comprueba la caché y las consultas de recursos sin descargar de nuevo su contenido.
    def test_04_gzip_etag_revalidation_and_head(self):
        c = Client(self.app, Response)
        headers = {"X-Forwarded-Proto": "https", "Accept-Encoding": "gzip"}
        first = c.get("/static/js/example.js", headers=headers)
        cached = c.get(
            "/static/js/example.js",
            headers={**headers, "If-None-Match": first.headers["ETag"]},
        )
        self.assertEqual(cached.status_code, 304)
        self.assertEqual(cached.data, b"")
        head = c.head("/static/js/example.js", headers=headers)
        self.assertEqual(head.status_code, 200)
        self.assertEqual(head.data, b"")
        self.assertEqual(head.headers["Content-Length"], str(len(first.data)))
        first.close()
        cached.close()
        head.close()

    # Comprueba que las rutas inválidas no permitan salir de la carpeta pública.
    def test_05_static_traversal_and_missing_file_are_rejected(self):
        c = Client(self.app, Response)
        for path in ["/static/../.env", "/static/js/missing.js"]:
            self.assertEqual(
                c.get(path, headers={"X-Forwarded-Proto": "https"}).status_code, 404
            )

    # Comprueba que generar recursos dos veces produzca el mismo resultado seguro.
    def test_06_build_is_repeatable_and_only_contains_public_text(self):
        before = (self.root / "build/static/js/example.js.gz").read_bytes()
        again = build_assets(self.root)
        self.assertEqual(
            (self.root / "build/static/js/example.js.gz").read_bytes(), before
        )
        self.assertEqual(again, self.report)
        self.assertEqual(len(again["archivos"]), 1)

    # Comprueba puertos y límites de conexiones antes de contactar con MySQL.
    def test_07_invalid_pool_or_port_fails_before_connecting(self):
        base = {
            "MYSQLHOST": "localhost",
            "MYSQLPORT": "3306",
            "MYSQLDATABASE": "test_vetcare_config",
            "MYSQLUSER": "synthetic",
            "MYSQLPASSWORD": "fixture-only",
            "VETCARE_SECRET_KEY": "Synthetic-configuration-secret-32",
        }
        with patch("vetcare.config.load_dotenv"):
            for changes in [
                {"DB_POOL_SIZE": "0"},
                {"DB_POOL_SIZE": "33"},
                {"DB_POOL_SIZE": "abc"},
                {"MYSQLPORT": "0"},
                {"MYSQLPORT": "65536"},
            ]:
                with patch.dict("os.environ", {**base, **changes}, clear=True):
                    with self.assertRaises(RuntimeError):
                        Config.load()

    # Comprueba la ruta de fotografías en producción y el arranque independiente del correo.
    def test_08_production_media_must_be_absolute_worker_does_not_need_it(self):
        base = {
            "MYSQLHOST": "localhost",
            "MYSQLPORT": "3306",
            "MYSQLDATABASE": "test_vetcare_config",
            "MYSQLUSER": "synthetic",
            "MYSQLPASSWORD": "fixture-only",
            "VETCARE_SECRET_KEY": "Synthetic-configuration-secret-32",
            "VETCARE_PRODUCTION": "true",
        }
        with patch("vetcare.config.load_dotenv"):
            with patch.dict(
                "os.environ", {**base, "MEDIA_ROOT": "relative/photos"}, clear=True
            ):
                with self.assertRaises(RuntimeError):
                    Config.load()
            with patch.dict(
                "os.environ", {**base, "VETCARE_SERVICE": "worker"}, clear=True
            ):
                self.assertTrue(Config.load().production)
