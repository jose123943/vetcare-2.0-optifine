"""Reglas de agenda, filtro exacto de propietario, pagos y limpieza, en MySQL aislado."""

import unittest
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from threading import Event
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from pypdf import PdfReader

from vetcare.demo import (
    OPERATIONAL_TABLES,
    clear_operational_data,
    prepare_demo,
    table_counts,
)
from vetcare.services.clinic import complete_finished_appointments
from vetcare.services.scheduler import start_monitor, stop_monitor

from .support import client, family, provision, write


class AgendaPaymentTests(unittest.TestCase):
    # Prepara el entorno y los datos aislados requeridos por este grupo de pruebas.
    @classmethod
    def setUpClass(cls):
        cls.app, cls.uid = provision()
        cls.c = client(cls.app)

    # Cierra los recursos reservados por este grupo de pruebas.
    @classmethod
    def tearDownClass(cls):
        cls.app.database.close()

    def appointment(self, **changes):
        owner = write(self.c, "/api/clientes", family(count=2)).json["cliente_id"]
        pet = self.c.get(f"/api/clientes/{owner}/mascotas").json["mascotas"][0]["id"]
        vet = write(
            self.c,
            "/api/veterinarios",
            dict(
                nombre="Profesional",
                apellido="Prueba",
                telefono="0000000000",
                especialidad="General",
            ),
        ).json["id"]
        data = dict(
            cliente_id=owner,
            mascota=pet,
            veterinario=vet,
            fecha="2027-03-01",
            hora="10:00",
            duracion_minutos=30,
            motivo="Control sintético",
        )
        data.update(changes)
        response = write(self.c, "/api/citas", data)
        self.assertEqual(response.status_code, 200, response.json)
        return data, response.json["cita"]

    # Comprueba la regresi?n de only programada on creation.
    def test_01_only_programada_on_creation(self):
        data, appointment = self.appointment()
        self.assertEqual(appointment["estado"], "Programada")
        for state in ["Pendiente", "Confirmada", "Atendida", "Cancelada", "Otro"]:
            self.assertEqual(
                write(
                    self.c, "/api/citas", dict(data, estado=state, hora="15:00")
                ).status_code,
                400,
            )

    # Comprueba la regresi?n de finishing time and colombia timezone.
    def test_02_finishing_time_and_colombia_timezone(self):
        _, appointment = self.appointment()
        with self.app.database.lease() as db:
            before = db.one("SELECT COUNT(*) AS n FROM pagInicio_notificacion")["n"]
            complete_finished_appointments(
                db, datetime(2027, 3, 1, 15, 29, 59, tzinfo=UTC)
            )
            self.assertEqual(
                db.one(
                    "SELECT estado FROM cita WHERE id_cita=%s", (appointment["id"],)
                )["estado"],
                "Programada",
            )
            complete_finished_appointments(db, datetime(2027, 3, 1, 15, 30, tzinfo=UTC))
            self.assertEqual(
                db.one(
                    "SELECT estado FROM cita WHERE id_cita=%s", (appointment["id"],)
                )["estado"],
                "Atendida",
            )
            complete_finished_appointments(db, datetime(2027, 3, 1, 15, 30, tzinfo=UTC))
            self.assertEqual(
                db.one("SELECT COUNT(*) AS n FROM pagInicio_notificacion")["n"], before
            )

    # Comprueba la regresi?n de agenda get persists completion and preserves cancelled.
    def test_03_agenda_get_persists_completion_and_preserves_cancelled(self):
        data, appointment = self.appointment(hora="11:00")
        cancelled = write(self.c, "/api/citas", dict(data, hora="12:00")).json["cita"]
        write(
            self.c,
            f"/api/citas/{cancelled['id']}",
            dict(data, hora="12:00", estado="Cancelada"),
            method="PUT",
        )
        with patch(
            "vetcare.services.clinic.NOW",
            return_value=datetime(2027, 3, 1, 13, tzinfo=ZoneInfo("America/Bogota")),
        ):
            self.assertEqual(self.c.get("/api/citas").status_code, 200)
        with self.app.database.lease() as db:
            self.assertEqual(
                db.one(
                    "SELECT estado FROM cita WHERE id_cita=%s", (appointment["id"],)
                )["estado"],
                "Atendida",
            )
            self.assertEqual(
                db.one("SELECT estado FROM cita WHERE id_cita=%s", (cancelled["id"],))[
                    "estado"
                ],
                "Cancelada",
            )

    # Comprueba la regresi?n de owner list search and exact pet filter.
    def test_04_owner_list_search_and_exact_pet_filter(self):
        data, _ = self.appointment()
        other, _ = self.appointment()
        owner = self.c.get(f"/api/clientes/{data['cliente_id']}").json["cliente"]
        self.assertTrue(self.c.get("/api/clientes").json["clientes"])
        search = self.c.get(
            "/api/clientes", query_string={"q": owner["documento"]}
        ).json["clientes"]
        self.assertEqual([row["id"] for row in search], [data["cliente_id"]])
        rows = self.c.get(
            "/api/mascotas",
            query_string={"cliente_id": data["cliente_id"], "q": "no-coincide"},
        ).json["mascotas"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(pet["cliente_id"] == data["cliente_id"] for pet in rows))
        self.assertNotEqual(data["cliente_id"], other["cliente_id"])
        self.assertEqual(
            self.c.get("/api/mascotas?cliente_id=malicioso").status_code, 400
        )

    # Comprueba la regresi?n de three payment methods detail change and pdf.
    def test_05_three_payment_methods_detail_change_and_pdf(self):
        _, appointment = self.appointment()
        for method in ["Transferencia", "Efectivo", "Tarjeta"]:
            data = dict(
                cita_id=appointment["id"],
                cliente_id=appointment["cliente_id"],
                servicios=[
                    dict(
                        servicio="Consulta de prueba",
                        cantidad=1,
                        precio_unitario="45000",
                    )
                ],
                metodo_pago=method,
                estado_pago="Pagada",
            )
            response = write(self.c, "/api/facturas", data)
            self.assertEqual(response.status_code, 200, response.json)
            fid = response.json["id"]
            detail = self.c.get(f"/inicio/api/detalle-factura/{fid}/").json["detalle"]
            self.assertEqual(detail["metodo_pago"], method)
            content = self.c.get(response.json["pdf_url"]).data
            text = " ".join(
                page.extract_text() for page in PdfReader(BytesIO(content)).pages
            )
            self.assertIn(method, text)
            changed = write(
                self.c,
                "/inicio/api/actualizar-estado-factura/",
                dict(factura_id=fid, estado_pago="Pendiente", metodo_pago="Tarjeta"),
            )
            self.assertEqual(changed.status_code, 200, changed.json)
            self.assertEqual(
                self.c.get(f"/inicio/api/detalle-factura/{fid}/").json["detalle"][
                    "metodo_pago"
                ],
                "Tarjeta",
            )

    # Comprueba la regresi?n de invalid payment does not insert invoice.
    def test_06_invalid_payment_does_not_insert_invoice(self):
        _, appointment = self.appointment()
        with self.app.database.lease() as db:
            before = db.one("SELECT COUNT(*) AS n FROM factura")["n"]
        for method in ["", None, "Cripto", "efectivo"]:
            response = write(
                self.c,
                "/api/facturas",
                dict(
                    cita_id=appointment["id"],
                    cliente_id=appointment["cliente_id"],
                    servicios=[
                        dict(servicio="Consulta", cantidad=1, precio_unitario="1")
                    ],
                    metodo_pago=method,
                ),
            )
            self.assertEqual(response.status_code, 400)
        with self.app.database.lease() as db:
            self.assertEqual(db.one("SELECT COUNT(*) AS n FROM factura")["n"], before)

    # Comprueba la regresi?n de periodic monitor does not require smtp.
    def test_07_periodic_monitor_does_not_require_smtp(self):
        database = MagicMock()
        done = Event()
        with patch(
            "vetcare.services.scheduler.complete_finished_appointments",
            side_effect=lambda db: done.set(),
        ) as complete:
            monitor = start_monitor(database, interval=60)
            try:
                self.assertTrue(done.wait(timeout=5))
            finally:
                stop_monitor(monitor)
            self.assertFalse(monitor[1].is_alive())
            complete.assert_called_once()

    # Comprueba la regresi?n de clear operational data preserves superusers and can rollback.
    def test_08_clear_operational_data_preserves_superusers_and_can_rollback(self):
        with self.app.database.lease() as db:
            before = table_counts(db)
            with self.assertRaises(RuntimeError):
                with db.atomic():
                    clear_operational_data(db)
                    raise RuntimeError("Prueba de rollback")
            self.assertEqual(table_counts(db), before)
            with db.atomic():
                supers = clear_operational_data(db)
                self.assertEqual(
                    db.all("SELECT * FROM auth_user WHERE is_superuser=1 ORDER BY id"),
                    supers,
                )
                counts = table_counts(db)
                self.assertFalse(any(counts[table] for table in OPERATIONAL_TABLES))
            # Conserva una demostración aislada para el recorrido de navegador posterior.
            with db.atomic():
                prepare_demo(db, datetime(2026, 11, 17).date())

    # Comprueba el orden real por fecha/hora en agenda, selectores y páginas completas.
    def test_09_appointment_order_shared_by_lists_and_selectors(self):
        data, _ = self.appointment(fecha="2027-03-30", hora="15:00")
        today = date(2027, 3, 1)
        now = datetime(2027, 3, 1, 12, tzinfo=ZoneInfo("America/Bogota"))
        slots = [
            (10, "15:00"),
            (-10, "10:00"),
            (0, "15:00"),
            (1, "11:00"),
            (-1, "09:00"),
            (0, "09:00"),
            (-1, "15:00"),
            (3, "08:00"),
            (3, "16:00"),
        ] + [(offset, "09:00") for offset in range(20, 74)]
        with self.app.database.lease() as db:
            db.many(
                "INSERT INTO cita (fecha,hora,motivo,estado,observaciones,"
                "duracion_minutos,cliente_id,mascota_id,veterinario_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                [
                    (
                        today + timedelta(days=offset),
                        hour,
                        "Orden de agenda: datos sintéticos",
                        "Cancelada" if index == 3 else "Programada",
                        "Prueba aislada, sin notificación",
                        30,
                        data["cliente_id"],
                        data["mascota"],
                        data["veterinario"],
                    )
                    for index, (offset, hour) in enumerate(slots)
                ],
            )
            fixtures = db.all(
                "SELECT id_cita AS id,fecha,TIME_FORMAT(hora,'%%H:%%i') AS hora,"
                "estado FROM cita WHERE mascota_id=%s",
                (data["mascota"],),
            )

        def key(row):
            stamp = datetime.fromisoformat(f"{row['fecha']}T{row['hora']}")
            past = stamp.date() < today
            seconds = (stamp - datetime(2027, 1, 1)).total_seconds()
            return (past, -seconds if past else seconds, row["id"])

        ordered = sorted(fixtures, key=key)
        own_ids = {row["id"] for row in fixtures}
        pending = [
            row
            for row in ordered
            if row["estado"] != "Cancelada"
            and datetime.fromisoformat(f"{row['fecha']}T{row['hora']}")
            + timedelta(minutes=30)
            > now.replace(tzinfo=None)
        ]
        routes = [
            ("/api/citas", ordered),
            ("/inicio/api/citas/", ordered),
            (f"/inicio/api/citas-mascota/{data['mascota']}/", ordered),
            (
                "/inicio/api/datos-factura/",
                [row for row in ordered if row["estado"] != "Cancelada"],
            ),
            ("/api/citas/pendientes", pending),
            ("/inicio/api/citas/pendientes/", pending),
            ("/inicio/api/dashboard/", pending),
        ]
        with patch("vetcare.services.clinic.NOW", return_value=now):
            for path, expected in routes:
                with self.subTest(path=path):
                    response = self.c.get(path)
                    self.assertEqual(response.status_code, 200, response.json)
                    rows = response.json["citas"]
                    self.assertEqual(rows, sorted(rows, key=key))
                    self.assertEqual(
                        [row["id"] for row in rows if row["id"] in own_ids],
                        [row["id"] for row in expected],
                    )

            complete = self.c.get("/api/citas").json["citas"]
            collected = []
            index = 1
            while index:
                response = self.c.get(f"/api/citas?pagina={index}").json
                collected.extend(response["citas"])
                index = response["siguiente"]
            self.assertGreater(len(collected), 50)
            self.assertEqual(collected, complete)


if __name__ == "__main__":
    unittest.main(verbosity=2)
