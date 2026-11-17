import importlib.util
import json
import os
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from passlib.hash import django_pbkdf2_sha256
from PIL import Image
from pypdf import PdfReader

from vetcare.application import create_app
from vetcare.config import Config
from vetcare.db import insert
from vetcare.security import decode_legacy, digest, verify_password
from vetcare.services.adoptions import evaluate
from vetcare.services.mail import deliver_one

from .support import (
    PASSWORD,
    USERNAME,
    adoption_pet,
    applicant,
    client,
    family,
    provision,
    write,
)


class MigrationTests(unittest.TestCase):
    # Prepara el entorno y los datos aislados requeridos por este grupo de pruebas.
    @classmethod
    def setUpClass(cls):
        info = Path(tempfile.gettempdir()) / "vetcare_wsgi_test_database.json"
        if os.getenv("VETCARE_REUSE_TEST_DB") == "true" and info.exists():
            state = json.loads(info.read_text())
            config = Config.load(database=state["database"], testing=True)
            config.media = Path(state["media"])
            config.session_run_id = state.get("session_run_id", config.session_run_id)
            cls.app = create_app(config)
        else:
            cls.app, _ = provision()
        cls.c = client(cls.app)

    # Cierra los recursos reservados por este grupo de pruebas.
    @classmethod
    def tearDownClass(cls):
        cls.app.database.close()

    def checked(self, response, code=200):
        self.assertEqual(response.status_code, code, response.json)
        result = response.json
        response.get_data()
        response.close()
        return result

    def make_family(self, count=3):
        d = family(count=count)
        saved = self.checked(write(self.c, "/api/clientes", d))
        pets = self.checked(
            self.c.get("/api/clientes/" + str(saved["cliente_id"]) + "/mascotas")
        )["mascotas"]
        return d, saved["cliente_id"], pets

    def make_vet(self):
        return self.checked(
            write(
                self.c,
                "/api/veterinarios",
                dict(
                    nombre="Ana",
                    apellido="Prueba",
                    telefono="3000000000",
                    especialidad="General",
                ),
            )
        )["id"]

    def appointment_data(self):
        _, cid, pets = self.make_family()
        return dict(
            cliente_id=cid,
            mascota=pets[0]["id"],
            veterinario=self.make_vet(),
            fecha="2027-01-10",
            hora="10:00",
            motivo="Consulta sintética",
            duracion_minutos=30,
        )

    def make_appointment(self):
        d = self.appointment_data()
        r = self.checked(write(self.c, "/api/citas", d))
        return d, r["cita"]

    def make_adoption(self):
        pet = self.checked(
            write(self.c, "/adopciones/api/admin/mascotas/guardar/", adoption_pet())
        )["mascota"]
        visitor = client(self.app, False)
        q = self.checked(visitor.get("/adopciones/api/cuestionario/"))
        data = applicant(q)
        return pet, visitor, data

    # Comprueba la regresi?n de no framework and start.
    def test_01_no_framework_and_start(self):
        self.assertIsNone(importlib.util.find_spec("django"))
        for path in ["/adopciones/", "/health/live/", "/health/ready/"]:
            response = self.c.get(path)
            self.assertEqual(response.status_code, 200)
            response.get_data()
            response.close()
        self.assertEqual(self.c.get("/").status_code, 303)
        anon = client(self.app, False)
        response = anon.get("/")
        self.assertEqual(response.status_code, 200)
        response.get_data()
        response.close()
        for html in (self.app.config.root / "frontend/pages").glob("*.html"):
            text = html.read_text(encoding="utf-8")
            self.assertNotIn("{%", text)
            self.assertNotIn("{{", text)

    # Comprueba la regresi?n de legacy password hash upgrades after login.
    def test_02_legacy_password_hash_upgrades_after_login(self):
        with self.app.database.lease() as db:
            db.execute(
                "UPDATE auth_user SET password=%s WHERE username=%s",
                (django_pbkdf2_sha256.hash(PASSWORD), USERNAME),
            )
        client(self.app)
        with self.app.database.lease() as db:
            stored = db.one(
                "SELECT password FROM auth_user WHERE username=%s", (USERNAME,)
            )["password"]
        self.assertTrue(stored.startswith("$argon2"))
        self.assertTrue(verify_password(PASSWORD, stored))
        self.assertFalse(verify_password("wrong", stored))
        from werkzeug.test import Client
        from werkzeug.wrappers import Response

        headers = (
            Client(self.app, Response).get("/api/session").headers.getlist("Set-Cookie")
        )
        self.assertTrue(
            any(
                "vetcare_sid=" in h and "HttpOnly" in h and "SameSite=Lax" in h
                for h in headers
            )
        )

    # Comprueba la regresi?n de private routes csrf methods and expiration.
    def test_03_private_routes_csrf_methods_and_expiration(self):
        anon = client(self.app, False)
        self.checked(anon.get("/api/clientes"), 401)
        self.checked(self.c.post("/api/clientes", json=family()), 403)
        self.checked(self.c.delete("/api/citas"), 405)
        r = self.c.post(
            "/api/clientes",
            json=family(),
            headers={
                "X-CSRFToken": self.c.get_cookie("csrftoken").value,
                "Origin": "https://evil.invalid",
                "Idempotency-Key": str(uuid.uuid4()),
            },
        )
        self.checked(r, 403)
        stale = client(self.app)
        with self.app.database.lease() as db:
            db.execute(
                "UPDATE vc_session SET expires=UTC_TIMESTAMP()-INTERVAL 1 SECOND WHERE token_hash=%s",
                (digest(stale.get_cookie("vetcare_sid").value),),
            )
        self.checked(stale.get("/api/clientes"), 401)

    # Comprueba la regresi?n de login throttle and logout.
    def test_04_login_throttle_and_logout(self):
        c = client(self.app, False)
        name = "invalid-" + uuid.uuid4().hex
        for _ in range(6):
            self.checked(
                write(c, "/api/auth/login", {"username": name, "password": "wrong"}),
                401,
            )
        self.checked(
            write(c, "/api/auth/login", {"username": name, "password": "wrong"}), 429
        )
        c = client(self.app)
        token = c.get_cookie("vetcare_sid").value
        self.checked(write(c, "/api/auth/logout", {}))
        self.assertIsNone(c.get_cookie("vetcare_sid"))
        c.set_cookie("vetcare_sid", token)
        self.checked(c.get("/api/clientes"), 401)

    # Comprueba la regresi?n de family three pets and idempotency.
    def test_05_family_three_pets_and_idempotency(self):
        d = family()
        key = str(uuid.uuid4())
        a = self.checked(
            write(self.c, "/inicio/api/registrar/cliente-mascota/", d, key)
        )
        b = self.checked(
            write(self.c, "/inicio/api/registrar/cliente-mascota/", d, key)
        )
        self.assertEqual(a, b)
        pets = self.checked(self.c.get(f"/api/clientes/{a['cliente_id']}/mascotas"))[
            "mascotas"
        ]
        self.assertEqual(len(pets), 3)
        d["nombre"] = "Otro"
        self.checked(
            write(self.c, "/inicio/api/registrar/cliente-mascota/", d, key), 409
        )

    # Comprueba la regresi?n de invalid child rolls back parent.
    def test_06_invalid_child_rolls_back_parent(self):
        d = family()
        d["mascotas"][-1]["peso"] = "NaN"
        self.checked(write(self.c, "/api/clientes", d), 400)
        with self.app.database.lease() as db:
            self.assertIsNone(
                db.one(
                    "SELECT id_cliente FROM cliente WHERE documento=%s",
                    (d["documento"],),
                )
            )

    # Comprueba la regresi?n de concurrent same key only one family.
    def test_07_concurrent_same_key_only_one_family(self):
        d = family()
        key = str(uuid.uuid4())
        sid = self.c.get_cookie("vetcare_sid").value
        csrf = self.c.get_cookie("csrftoken").value

        def send(_):
            c = client(self.app, False)
            c.set_cookie("vetcare_sid", sid)
            c.set_cookie("csrftoken", csrf)
            return write(c, "/api/clientes", d, key)

        with ThreadPoolExecutor(max_workers=3) as executor:
            responses = list(executor.map(send, range(3)))
        bodies = [self.checked(r) for r in responses]
        self.assertEqual(len({r["cliente_id"] for r in bodies}), 1)

    # Comprueba la regresi?n de unique document and sql injection.
    def test_08_unique_document_and_sql_injection(self):
        d, cid, pets = self.make_family()
        self.checked(write(self.c, "/api/clientes", d), 409)
        self.assertEqual(
            self.checked(
                self.c.get("/api/clientes", query_string={"q": "' OR 1=1 --"})
            )["clientes"],
            [],
        )
        self.assertEqual(
            len(
                self.checked(
                    self.c.get("/api/clientes", query_string={"q": d["documento"]})
                )["clientes"]
            ),
            1,
        )

    # Comprueba la regresi?n de edit pet and existing owner and deletion rules.
    def test_09_edit_pet_and_existing_owner_and_deletion_rules(self):
        d, cid, pets = self.make_family()
        p = pets[0]
        self.checked(write(self.c, f"/api/clientes/{cid}/mascotas", d["mascotas"][0]))
        payload = {
            **d,
            **d["mascotas"][0],
            "nombre": d["nombre"],
            "nombreMascota": "Renombrada",
            "mascotaId": p["id"],
            "clienteId": cid,
        }
        self.checked(write(self.c, "/inicio/api/editar-registro/", payload))
        self.assertEqual(
            self.checked(self.c.get(f"/api/mascotas/{p['id']}"))["mascota"]["nombre"],
            "Renombrada",
        )
        self.checked(write(self.c, f"/api/clientes/{cid}", {}, method="DELETE"), 400)
        self.checked(write(self.c, f"/api/mascotas/{p['id']}", {}, method="DELETE"))
        self.assertEqual(
            self.checked(self.c.get(f"/api/clientes/{cid}"))["cliente"]["id"], cid
        )

    # Comprueba la regresi?n de appointment owner overlap adjacent and cancel.
    def test_10_appointment_owner_overlap_adjacent_and_cancel(self):
        d, appointment = self.make_appointment()
        self.checked(write(self.c, "/api/citas", d), 400)
        other = dict(d, hora="10:30")
        self.checked(write(self.c, "/api/citas", other))
        _, cid, _ = self.make_family()
        self.checked(
            write(self.c, "/api/citas", dict(d, cliente_id=cid, hora="12:00")), 404
        )
        self.checked(
            write(
                self.c,
                f"/api/citas/{appointment['id']}",
                dict(d, estado="Cancelada"),
                method="PUT",
            )
        )
        self.checked(write(self.c, "/api/citas", d))

    # Comprueba la regresi?n de concurrent appointment conflict.
    def test_11_concurrent_appointment_conflict(self):
        d = self.appointment_data()
        sid = self.c.get_cookie("vetcare_sid").value
        csrf = self.c.get_cookie("csrftoken").value

        def send(_):
            c = client(self.app, False)
            c.set_cookie("vetcare_sid", sid)
            c.set_cookie("csrftoken", csrf)
            return write(c, "/api/citas", d)

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(send, range(2)))
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [200, 400],
            [r.json for r in responses],
        )

    # Comprueba la regresi?n de vaccine treatment history and protected delete.
    def test_12_vaccine_treatment_history_and_protected_delete(self):
        _, a = self.make_appointment()
        mid = a["mascota_id"]
        v = dict(
            mascota_id=mid,
            nombre_vacuna="Rabia",
            lote="Pruebas",
            fecha_aplicacion="2026-01-01",
            fecha_vencimiento="2027-01-01",
        )
        self.checked(write(self.c, "/api/vacunas", v))
        self.checked(
            write(self.c, "/api/vacunas", dict(v, fecha_vencimiento="2025-01-01")), 400
        )
        t = dict(
            cita_id=a["id"],
            fecha_inicio="2026-01-01",
            descripcion="Revisión",
            medicamento="Prueba",
            dosis="Según indicación",
            duracion="3 días",
        )
        self.checked(write(self.c, "/api/tratamientos", t))
        self.assertEqual(
            len(
                self.checked(self.c.get(f"/inicio/api/vacunas-mascota/{mid}/"))[
                    "vacunas"
                ]
            ),
            1,
        )
        self.assertEqual(
            len(
                self.checked(self.c.get(f"/inicio/api/tratamientos-mascota/{mid}/"))[
                    "tratamientos"
                ]
            ),
            1,
        )
        self.checked(write(self.c, f"/api/mascotas/{mid}", {}, method="DELETE"), 400)

    # Comprueba la regresi?n de invoice decimal pdf and replay.
    def test_13_invoice_decimal_pdf_and_replay(self):
        _, a = self.make_appointment()
        d = dict(
            cita_id=a["id"],
            cliente_id=a["cliente_id"],
            servicios=[
                dict(
                    servicio="Consulta real de pruebas",
                    cantidad=2,
                    precio_unitario="40000.25",
                )
            ],
            descuento="1000",
            impuesto="0",
            estado_pago="Pagada",
            metodo_pago="Efectivo",
        )
        key = str(uuid.uuid4())
        r = self.checked(write(self.c, "/api/facturas", d, key))
        self.assertEqual(r["monto_total"], "79000.50")
        self.assertEqual(self.checked(write(self.c, "/api/facturas", d, key)), r)
        response = self.c.get(r["pdf_url"])
        self.assertEqual(response.status_code, 200)
        reader = PdfReader(BytesIO(response.data))
        text = " ".join(page.extract_text() for page in reader.pages)
        self.assertIn("Consulta real de pruebas", text)
        self.assertIn("79.000,50", text)
        self.checked(write(self.c, "/api/facturas", dict(d, descuento="999999")), 400)

    # Comprueba la regresi?n de outbox transaction and delivery.
    def test_14_outbox_transaction_and_delivery(self):
        _, a = self.make_appointment()
        sent = []
        with patch.dict(os.environ, {"DEFAULT_FROM_EMAIL": "test@example.invalid"}):
            while deliver_one(self.app.database, sender=sent.append):
                pass
        self.assertTrue(sent)
        self.assertTrue(
            all(m.get_content_type() == "multipart/alternative" for m in sent)
        )
        self.assertTrue(
            any("text/html" == part.get_content_type() for part in sent[-1].walk())
        )
        with self.app.database.lease() as db:
            self.assertEqual(
                db.one(
                    "SELECT estado FROM pagInicio_notificacion WHERE cita_id=%s",
                    (a["id"],),
                )["estado"],
                "Enviada",
            )

    # Comprueba la regresi?n de email failure does not lose appointment.
    def test_15_email_failure_does_not_lose_appointment(self):
        _, a = self.make_appointment()

        def fail(message):
            raise RuntimeError("private SMTP detail should never be stored")

        while deliver_one(self.app.database, sender=fail):
            pass
        with self.app.database.lease() as db:
            n = db.one(
                "SELECT id,estado,error FROM pagInicio_notificacion WHERE cita_id=%s",
                (a["id"],),
            )
        self.assertEqual(n["estado"], "Fallida")
        self.assertEqual(n["error"], "RuntimeError")
        self.checked(
            write(self.c, f"/inicio/api/notificaciones/{n['id']}/reintentar/", {})
        )

    # Comprueba la regresi?n de exact adoption threshold.
    def test_16_exact_adoption_threshold(self):
        for score, approved in [(66, False), (67, True), (100, True)]:
            q = {
                "criterios": [
                    dict(
                        nombre="Cuidado",
                        peso=100,
                        recomendacion="Planificar",
                        preguntas=[
                            dict(
                                id=1,
                                texto="Pregunta",
                                opciones=[
                                    dict(
                                        id=2, texto="Respuesta", valor=score, alerta=""
                                    )
                                ],
                            )
                        ],
                    )
                ]
            }
            self.assertEqual(evaluate(q, {"1": 2})["aprobada"], approved)
        q["criterios"][0]["preguntas"].append(
            dict(
                id=3,
                texto="Otra",
                opciones=[dict(id=4, texto="Respuesta", valor=66, alerta="")],
            )
        )
        q["criterios"][0]["preguntas"][0]["opciones"][0]["valor"] = 67
        result = evaluate(q, {"1": 2, "3": 4})
        self.assertEqual(result["porcentaje"], Decimal("66.500000"))
        self.assertFalse(result["aprobada"])

    # Comprueba la regresi?n de adoption submit privacy and replay.
    def test_17_adoption_submit_privacy_and_replay(self):
        pet, c, d = self.make_adoption()
        key = str(uuid.uuid4())
        path = f"/adopciones/api/mascotas/{pet['id']}/solicitar/"
        result = self.checked(write(c, path, d, key))["resultado"]
        self.assertTrue(result["aprobada"])
        self.assertEqual(self.checked(write(c, path, d, key))["resultado"], result)
        self.checked(c.get(result["url"]))
        anon = client(self.app, False)
        self.checked(anon.get(result["url"]), 404)
        self.checked(write(anon, path, d, key), 403)
        self.checked(write(c, path, dict(d, porcentaje=100)), 400)
        public = self.checked(c.get("/adopciones/api/catalogo/"))
        self.assertNotIn("paciente", str(public))
        self.assertNotIn("documento", str(result))

    # Comprueba la regresi?n de adoption review single delivery and immutable versions.
    def test_18_adoption_review_single_delivery_and_immutable_versions(self):
        pet, c, d = self.make_adoption()
        self.checked(write(c, f"/adopciones/api/mascotas/{pet['id']}/solicitar/", d))
        with self.app.database.lease() as db:
            s = db.one(
                "SELECT id FROM adopciones_solicitud WHERE mascota_id=%s", (pet["id"],)
            )
        path = f"/adopciones/api/admin/solicitudes/{s['id']}/revisar/"
        review = dict(
            accion="Autorizar", notas="Plan revisado", bienestar_verificado=True
        )
        self.checked(write(self.c, path, dict(review, bienestar_verificado=False)), 400)
        self.checked(write(self.c, path, review))
        self.checked(write(self.c, path, dict(review, accion="Entregar")))
        self.checked(write(self.c, path, dict(review, accion="Entregar")), 400)
        with self.app.database.lease() as db:
            self.assertEqual(
                db.one(
                    "SELECT COUNT(*) AS n FROM adopciones_entrega WHERE mascota_id=%s",
                    (pet["id"],),
                )["n"],
                1,
            )
        self.checked(
            write(
                self.c,
                f"/adopciones/api/admin/cuestionarios/{d['cuestionario']}/",
                {},
                method="PUT",
            ),
            400,
        )

    # Comprueba la regresi?n de questionnaire clone edit publish.
    def test_19_questionnaire_clone_edit_publish(self):
        q = self.checked(self.c.get("/adopciones/api/cuestionario/"))
        clone = self.checked(
            write(
                self.c,
                "/adopciones/api/admin/cuestionario/pesos/",
                dict(
                    cuestionario=q["id"],
                    pesos={str(c["id"]): c["peso"] for c in q["criterios"]},
                    publicar=False,
                ),
            )
        )["id"]
        draft = self.checked(
            self.c.get(f"/adopciones/api/admin/cuestionarios/{clone}/")
        )["cuestionario"]
        p = draft["criterios"][0]["preguntas"][0]
        self.checked(
            write(
                self.c,
                f"/adopciones/api/admin/cuestionarios/{clone}/",
                dict(
                    pregunta_id=p["id"], texto="Texto revisado", opciones=p["opciones"]
                ),
                method="PUT",
            )
        )
        self.checked(
            write(self.c, f"/adopciones/api/admin/cuestionarios/{clone}/publicar/", {})
        )
        self.assertEqual(
            self.checked(self.c.get("/adopciones/api/cuestionario/"))["id"], clone
        )

    # Comprueba la regresi?n de photo reencoded and safe static.
    def test_20_photo_reencoded_and_safe_static(self):
        pet, _, _ = self.make_adoption()
        output = BytesIO()
        Image.new("RGB", (20, 20), "green").save(output, "PNG")
        output.seek(0)
        r = self.c.post(
            f"/adopciones/api/admin/mascotas/{pet['id']}/foto/",
            data={"fotografia": (output, "photo.png")},
            headers={
                "X-CSRFToken": self.c.get_cookie("csrftoken").value,
                "Idempotency-Key": str(uuid.uuid4()),
            },
        )
        data = self.checked(r)
        photo = self.c.get(data["fotografia"])
        self.assertEqual(photo.status_code, 200)
        self.assertEqual(photo.mimetype, "image/webp")
        photo.get_data()
        photo.close()
        self.assertEqual(self.c.get("/static/../../.env").status_code, 404)

    # Comprueba la regresi?n de accounts permissions and session revocation.
    def test_21_accounts_permissions_and_session_revocation(self):
        name = "staff-" + uuid.uuid4().hex[:12]
        d = dict(
            username=name,
            password=PASSWORD,
            first_name="Staff",
            last_name="",
            email="",
            is_staff=True,
            is_active=True,
            is_superuser=False,
        )
        uid = self.checked(write(self.c, "/api/admin/usuarios", d))["id"]
        c = client(self.app, False)
        self.checked(
            write(c, "/api/auth/login", dict(username=name, password=PASSWORD))
        )
        self.checked(c.get("/api/admin/usuarios"), 403)
        self.checked(
            write(
                self.c,
                f"/api/admin/usuarios/{uid}",
                dict(d, is_active=False),
                method="PUT",
            )
        )
        self.checked(c.get("/api/clientes"), 401)

    # Comprueba la regresi?n de legacy visitor signature compatibility.
    def test_22_legacy_visitor_signature_compatibility(self):
        fixture = Path(__file__).parent / "fixtures/legacy.json"
        data = json.loads(fixture.read_text())
        self.assertTrue(verify_password(data["password"], data["hash"]))
        self.assertEqual(
            decode_legacy(data["session_data"], data["secret"]).get("adoption_owner"),
            "owner-migration-fixture",
        )
        self.assertEqual(
            decode_legacy(data["session_data"] + "bad", data["secret"]), {}
        )

    # Comprueba la regresi?n de paginated tables and canonical gets.
    def test_23_paginated_tables_and_canonical_gets(self):
        for path, key in [
            ("/api/mascotas", "mascotas"),
            ("/api/citas", "citas"),
            ("/api/facturas", "facturas"),
        ]:
            d = self.checked(self.c.get(path + "?pagina=1"))
            self.assertLessEqual(len(d[key]), 50)
            self.assertIn("siguiente", d)
        self.checked(self.c.get("/api/mascotas?pagina=bad"), 400)

    # Comprueba la regresi?n de production headers host https and secure cookie.
    def test_24_production_headers_host_https_and_secure_cookie(self):
        from dataclasses import replace

        from werkzeug.test import Client
        from werkzeug.wrappers import Response

        production = create_app(replace(self.app.config, production=True))
        try:
            c = Client(production, Response)
            self.assertEqual(
                c.get("/", headers={"Host": "unknown.invalid"}).status_code, 400
            )
            self.assertEqual(c.get("/").status_code, 308)
            self.assertEqual(c.get("/health/live/").status_code, 200)
            r = c.get("/api/session", headers={"X-Forwarded-Proto": "https"})
            self.assertEqual(r.status_code, 200)
            self.assertIn("max-age=", r.headers["Strict-Transport-Security"])
            self.assertTrue(
                any(
                    "Secure" in h and "HttpOnly" in h
                    for h in r.headers.getlist("Set-Cookie")
                )
            )
            self.assertEqual(r.headers["X-Frame-Options"], "DENY")
        finally:
            production.database.close()

    # Comprueba la regresi?n de old visitor can still read private result.
    def test_25_old_visitor_can_still_read_private_result(self):
        from dataclasses import replace
        from werkzeug.test import Client
        from werkzeug.wrappers import Response

        fixture = Path(__file__).parent / "fixtures/legacy.json"
        legacy_data = json.loads(fixture.read_text())
        pet, c, d = self.make_adoption()
        result = self.checked(
            write(c, f"/adopciones/api/mascotas/{pet['id']}/solicitar/", d)
        )["resultado"]
        token = uuid.uuid4().hex
        with self.app.database.lease() as db:
            insert(
                db,
                "django_session",
                dict(
                    session_key=token,
                    session_data=json.loads(fixture.read_text())["session_data"],
                    expire_date=datetime.now() + timedelta(days=1),
                ),
            )
            db.execute(
                "UPDATE adopciones_solicitud SET propietario_sesion=%s WHERE codigo=%s",
                (digest("owner-migration-fixture"), uuid.UUID(result["codigo"]).hex),
            )
        legacy_app = create_app(replace(self.app.config, secret=legacy_data["secret"]))
        try:
            old = Client(legacy_app, Response)
            old.set_cookie("sessionid", token)
            self.checked(old.get("/adopciones/api/solicitud/" + result["codigo"] + "/"))
        finally:
            legacy_app.database.close()

    # Comprueba la regresi?n de malformed payload no internal error.
    def test_26_malformed_payload_no_internal_error(self):
        self.checked(
            write(
                self.c,
                "/api/citas",
                {
                    "fecha": "2027-01-01",
                    "hora": "10:00",
                    "motivo": "Prueba",
                    "mascota": [],
                },
            ),
            400,
        )

        self.checked(
            self.c.post(
                "/api/clientes",
                data="[1,2]",
                content_type="application/json",
                headers={
                    "X-CSRFToken": self.c.get_cookie("csrftoken").value,
                    "Idempotency-Key": str(uuid.uuid4()),
                },
            ),
            400,
        )

    # Comprueba la regresi?n de dead connection returns 503 then recovers.
    def test_28_dead_connection_returns_503_then_recovers(self):
        with self.app.database.lease() as db:
            identity = db.one("SELECT CONNECTION_ID() AS id,DATABASE() AS name")
            self.assertTrue(identity["name"].startswith("test_vetcare_"))
        controller = self.app.database.connect()
        try:
            with controller.cursor() as cursor:
                cursor.execute("KILL CONNECTION %s", (identity["id"],))
        finally:
            controller.close()
        self.checked(self.c.get("/api/clientes"), 503)
        self.checked(self.c.get("/api/clientes"))

    # Comprueba la regresi?n de pet edit preserves inactive owner.
    def test_29_pet_edit_preserves_inactive_owner(self):
        d, cid, pets = self.make_family()
        self.checked(
            write(
                self.c, f"/api/clientes/{cid}", dict(d, estado="Inactivo"), method="PUT"
            )
        )
        payload = {
            **d,
            **d["mascotas"][0],
            "nombre": d["nombre"],
            "nombreMascota": "Editada",
            "mascotaId": pets[0]["id"],
            "clienteId": cid,
        }
        self.checked(write(self.c, "/inicio/api/editar-registro/", payload))
        self.assertEqual(
            self.checked(self.c.get(f"/api/clientes/{cid}"))["cliente"]["estado"],
            "Inactivo",
        )

    # Comprueba la regresi?n de archived history permissions and no framework imports.
    def test_27_archived_history_permissions_and_no_framework_imports(self):
        import ast

        anon = client(self.app, False)
        self.checked(anon.get("/api/admin/historico/adopciones"), 401)
        self.checked(self.c.get("/api/admin/historico/adopciones"))
        self.checked(self.c.get("/api/admin/historico/adopciones/2147483647"), 404)
        sources = [
            self.app.config.root / "run.py",
            *(self.app.config.root / "vetcare").rglob("*.py"),
        ]
        for path in sources:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                modules = (
                    [n.name for n in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                    if isinstance(node, ast.ImportFrom)
                    else []
                )
                self.assertFalse(
                    any(
                        m.split(".")[0] in ("django", "flask", "fastapi")
                        for m in modules
                    ),
                    str(path),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
