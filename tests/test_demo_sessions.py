"""Limpieza segura, persistencia de sesión y encuesta directa; sólo MySQL aislado."""

import secrets
import unittest
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock, patch

from werkzeug.test import Client
from werkzeug.wrappers import Response

from vetcare.application import create_app
from vetcare.db import insert
from vetcare.demo import clear_operational_data, prepare_demo, table_counts
from vetcare.security import digest, hasher
from vetcare.services.mail import deliver_one, notification_state

from .support import client, provision, write


class DemoSessionTests(unittest.TestCase):
    # Prepara el entorno y los datos aislados requeridos por este grupo de pruebas.
    @classmethod
    def setUpClass(cls):
        cls.app, cls.uid = provision()
        cls.c = client(cls.app)

    # Cierra los recursos reservados por este grupo de pruebas.
    @classmethod
    def tearDownClass(cls):
        cls.app.database.close()

    # Comprueba la regresi?n de login survives more than eight hours and home redirects.
    def test_01_login_survives_more_than_eight_hours_and_home_redirects(self):
        c = client(self.app)
        token = digest(c.get_cookie("vetcare_sid").value)
        with self.app.database.lease() as db:
            db.execute(
                "UPDATE vc_session SET created=%s WHERE token_hash=%s",
                (datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30), token),
            )
            row = db.one("SELECT expires FROM vc_session WHERE token_hash=%s", (token,))
        self.assertEqual(row["expires"].year, 9999)
        self.assertEqual(c.get("/api/clientes").status_code, 200)
        self.assertEqual(c.get("/").status_code, 303)
        cookie_response = Client(self.app, Response).get("/api/session")
        self.assertTrue(cookie_response.headers.getlist("Set-Cookie"))
        for header in cookie_response.headers.getlist("Set-Cookie"):
            self.assertNotIn("Expires=", header)
            self.assertNotIn("Max-Age=", header)

    # Comprueba la regresi?n de restart invalidates session but shared workers accept it.
    def test_02_restart_invalidates_session_but_shared_workers_accept_it(self):
        c = client(self.app)
        cookie = c.get_cookie("vetcare_sid").value
        same = create_app(replace(self.app.config))
        restarted = create_app(
            replace(self.app.config, session_run_id=secrets.token_hex(32))
        )
        try:
            second = Client(same, Response)
            second.set_cookie("vetcare_sid", cookie)
            self.assertEqual(second.get("/api/clientes").status_code, 200)
            after = Client(restarted, Response)
            after.set_cookie("vetcare_sid", cookie)
            self.assertEqual(after.get("/api/clientes").status_code, 401)
        finally:
            same.database.close()
            restarted.database.close()

    # Comprueba la regresi?n de logout revokes scope.
    def test_03_logout_revokes_scope(self):
        c = client(self.app)
        token = c.get_cookie("vetcare_sid").value
        self.assertEqual(write(c, "/api/auth/logout", {}).status_code, 200)
        with self.app.database.lease() as db:
            self.assertIsNone(
                db.one(
                    "SELECT token_hash FROM vc_session_scope WHERE token_hash=%s",
                    (digest(token),),
                )
            )
        c.set_cookie("vetcare_sid", token)
        self.assertEqual(c.get("/api/clientes").status_code, 401)

    # Comprueba la regresi?n de demo preserves superuser and relations and never sends mail.
    def test_04_demo_preserves_superuser_and_relations_and_never_sends_mail(self):
        with self.app.database.lease() as db:
            ordinary = insert(
                db,
                "auth_user",
                dict(
                    username="ordinary-to-delete",
                    password=hasher.hash("Synthetic-only-password"),
                    first_name="",
                    last_name="",
                    email="",
                    is_superuser=False,
                    is_active=True,
                    is_staff=True,
                    date_joined=datetime.now(UTC).replace(tzinfo=None),
                    last_login=None,
                ),
            )
            group = insert(db, "auth_group", {"name": "Kept superuser role"})
            insert(db, "auth_user_groups", {"user_id": self.uid, "group_id": group})
            insert(db, "auth_user_groups", {"user_id": ordinary, "group_id": group})
            insert(
                db,
                "administrador",
                {"id_administrador": self.uid, "telefono": "0000000000"},
            )
            insert(
                db,
                "administrador",
                {"id_administrador": ordinary, "telefono": "0000000000"},
            )
            before = db.all("SELECT * FROM auth_user WHERE is_superuser=1 ORDER BY id")
            with db.atomic():
                report = prepare_demo(db, date(2026, 11, 17))
            self.assertEqual(
                before,
                db.all("SELECT * FROM auth_user WHERE is_superuser=1 ORDER BY id"),
            )
            self.assertEqual(db.one("SELECT COUNT(*) AS n FROM auth_user")["n"], 1)
            self.assertEqual(
                db.one("SELECT COUNT(*) AS n FROM auth_user_groups")["n"], 1
            )
            self.assertEqual(db.one("SELECT COUNT(*) AS n FROM administrador")["n"], 1)
            self.assertEqual(
                db.one("SELECT SUM(aprobada) AS n FROM adopciones_solicitud")["n"], 3
            )
            self.assertEqual(
                db.one(
                    "SELECT COUNT(*) AS n FROM adopciones_mascotaadopcion WHERE estado='Disponible'"
                )["n"],
                5,
            )
            self.assertEqual(
                db.one(
                    "SELECT COUNT(*) AS n FROM cita c JOIN mascota m ON m.id_mascota=c.mascota_id WHERE c.cliente_id<>m.cliente_id"
                )["n"],
                0,
            )
            self.assertEqual(
                db.one(
                    "SELECT COUNT(*) AS n FROM factura f JOIN (SELECT factura_id,SUM(cantidad*precio_unitario) AS total FROM factura_detallefactura GROUP BY factura_id) d ON d.factura_id=f.id_factura WHERE f.monto_total<>d.total-f.descuento+f.impuesto"
                )["n"],
                0,
            )
        calls = []
        self.assertFalse(deliver_one(self.app.database, sender=calls.append))
        self.assertEqual(calls, [])
        self.assertTrue(report["superusuarios_sin_cambios"])
        self.assertEqual(report["conteos"]["mascota"], 9)
        self.assertEqual(self.c.get("/api/clientes").status_code, 200)

    # Comprueba la regresi?n de failure rolls back cleanup.
    def test_05_failure_rolls_back_cleanup(self):
        with self.app.database.lease() as db:
            before = table_counts(db)
            with patch(
                "vetcare.demo.clinic.register_family",
                side_effect=RuntimeError("synthetic failure"),
            ):
                with self.assertRaises(RuntimeError):
                    with db.atomic():
                        prepare_demo(db, date(2026, 11, 17))
            self.assertEqual(before, table_counts(db))

    # Comprueba la regresi?n de demo can be repeated with exact counts.
    def test_06_demo_can_be_repeated_with_exact_counts(self):
        with self.app.database.lease() as db:
            if db.one("SELECT COUNT(*) AS n FROM cliente")["n"] == 0:
                with db.atomic():
                    prepare_demo(db, date(2026, 11, 17))
            # Esquema legado con FK circular: adopción cerrada -> evaluación -> adopción.
            owner = db.one(
                "SELECT id_cliente FROM cliente ORDER BY id_cliente LIMIT 1"
            )["id_cliente"]
            other = db.one(
                "SELECT id_cliente FROM cliente WHERE id_cliente<>%s ORDER BY id_cliente LIMIT 1",
                (owner,),
            )["id_cliente"]
            pet = db.one(
                "SELECT id_mascota FROM mascota WHERE cliente_id=%s LIMIT 1", (owner,)
            )["id_mascota"]
            employee = db.one(
                "SELECT id_empleado FROM empleado ORDER BY id_empleado LIMIT 1"
            )["id_empleado"]
            now = datetime.now(UTC).replace(tzinfo=None)
            aid = insert(
                db,
                "adopcion",
                dict(
                    estado="disponible",
                    activa=True,
                    motivo="Ejemplo legado",
                    observaciones="",
                    observaciones_adopcion="",
                    fecha_registro=now,
                    fecha_adopcion=None,
                    fecha_cierre=None,
                    cerrado_por_id=None,
                    cliente_adoptante_id=None,
                    cliente_origen_id=owner,
                    creado_por_id=self.uid,
                    mascota_id=pet,
                    responsable_id=employee,
                    evaluacion_aprobada_id=None,
                ),
            )
            eid = insert(
                db,
                "evaluacion_adopcion",
                dict(
                    respuestas="{}",
                    desglose="{}",
                    puntaje=80,
                    aprobada=True,
                    version="fixture",
                    fecha=now,
                    adopcion_id=aid,
                    cliente_id=other,
                    evaluado_por_id=self.uid,
                ),
            )
            db.execute(
                "UPDATE adopcion SET estado='adoptada',activa=NULL,cliente_adoptante_id=%s,evaluacion_aprobada_id=%s,fecha_adopcion=%s,fecha_cierre=%s WHERE id=%s",
                (other, eid, now, now, aid),
            )
            with db.atomic():
                report = prepare_demo(db, date(2026, 11, 17))
        self.assertEqual(report["conteos"]["cliente"], 5)
        self.assertEqual(report["conteos"]["adopciones_solicitud"], 5)
        self.assertEqual(report["avisos_reales_en_cola"], 0)

    # Comprueba la regresi?n de direct survey api is public and hides clinical relation.
    def test_07_direct_survey_api_is_public_and_hides_clinical_relation(self):
        with self.app.database.lease() as db:
            pet = db.one(
                "SELECT id FROM adopciones_mascotaadopcion WHERE estado='Disponible' ORDER BY id LIMIT 1"
            )
        if not pet:
            from .support import adoption_pet

            pet = write(
                self.c, "/adopciones/api/admin/mascotas/guardar/", adoption_pet()
            ).json["mascota"]
        visitor = client(self.app, False)
        response = visitor.get(f"/adopciones/api/mascotas/{pet['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("paciente", response.json["mascota"])
        self.assertEqual(
            visitor.get("/adopciones/api/mascotas/2147483647/").status_code, 404
        )

    # Comprueba la regresi?n de no superuser means no delete.
    def test_08_no_superuser_means_no_delete(self):
        db = Mock()
        db.all.side_effect = [[], []]
        with self.assertRaises(RuntimeError):
            clear_operational_data(db)
        db.execute.assert_not_called()

    # Comprueba la regresi?n de reserved demo addresses are never queued.
    def test_09_reserved_demo_addresses_are_never_queued(self):
        self.assertEqual(
            notification_state("client@vetcare.example.invalid"), "Demostración"
        )
        self.assertEqual(notification_state(""), "Sin correo")
        self.assertEqual(notification_state("client@example.com"), "Pendiente")


if __name__ == "__main__":
    unittest.main(verbosity=2)
