"""Fixtures sintéticos exclusivamente en una base aislada; nunca vacían Railway."""

import json
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from passlib.hash import django_pbkdf2_sha256
from werkzeug.test import Client
from werkzeug.wrappers import Response

from run import seed
from vetcare.application import create_app
from vetcare.config import Config
from vetcare.db import Database, insert
from vetcare.migrations import migrate

PASSWORD = "Fixture-only-for-tests-2026"
USERNAME = "wsgi-test-admin"


def provision(name=None):
    name = name or "test_vetcare_wsgi_" + uuid.uuid4().hex[:12]
    config = Config.load(database=name, testing=True)
    config.media = Path(tempfile.mkdtemp(prefix="vetcare_wsgi_test_media_"))
    database = Database(config)
    connection = database.connect(database=False)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE DATABASE `"
                + name
                + "` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
    finally:
        connection.close()
    migrate(database)
    seed(database)
    with database.lease() as db:
        uid = insert(
            db,
            "auth_user",
            dict(
                username=USERNAME,
                password=django_pbkdf2_sha256.hash(PASSWORD),
                first_name="Prueba",
                last_name="Migración",
                email="test@example.invalid",
                is_superuser=True,
                is_staff=True,
                is_active=True,
                date_joined=datetime.now(UTC).replace(tzinfo=None),
                last_login=None,
            ),
        )
    (Path(tempfile.gettempdir()) / "vetcare_wsgi_test_database.json").write_text(
        json.dumps(
            {"database": config.database, "uid": uid, "media": str(config.media)}
        ),
        encoding="utf-8",
    )
    return create_app(config), uid


def client(app, login=True):
    c = Client(app, Response)
    c.get("/api/session")
    if login:
        response = c.post(
            "/api/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            headers={"X-CSRFToken": c.get_cookie("csrftoken").value},
        )
        assert response.status_code == 200, response.json
    return c


def write(c, path, data, key=None, method="POST"):
    return c.open(
        path,
        method=method,
        json=data,
        headers={
            "X-CSRFToken": c.get_cookie("csrftoken").value,
            "Idempotency-Key": key or str(uuid.uuid4()),
        },
    )


def family(document=None, count=3):
    return dict(
        nombre="Familia",
        apellido="Pruebas",
        documento=document or uuid.uuid4().hex[:25],
        telefono="3000000000",
        direccion="Datos sintéticos",
        email="test@example.invalid",
        mascotas=[
            dict(
                nombre="Paciente " + str(i),
                especie="Perro",
                raza="Criollo",
                sexo="Hembra",
                edad=2,
                peso="4.50",
                observaciones="Prueba",
            )
            for i in range(count)
        ],
    )


def adoption_pet():
    return dict(
        nombre="Compañera de pruebas",
        especie="Perro",
        raza="Criolla",
        sexo="Hembra",
        edad_aproximada="2 años",
        peso="5",
        ingreso="2026-01-01",
        esterilizada=True,
        descripcion="Datos sintéticos para verificar la migración",
        personalidad="Tranquila",
        salud="Revisión de prueba",
        vacunacion="Al día",
        necesidades="",
        estado="Disponible",
    )


def applicant(q):
    return dict(
        cuestionario=q["id"],
        solicitante=dict(
            nombre="Solicitante sintético",
            documento="TEST-" + uuid.uuid4().hex[:12],
            edad=25,
            telefono="3000000000",
            email="test@example.invalid",
            direccion="Dirección de pruebas",
            ocupacion="Estudiante",
            presupuesto_cop=200000,
            ingreso_aproximado="",
            tipo_vivienda="Apartamento",
            tenencia_vivienda="Propia",
            consentimiento=True,
        ),
        respuestas={
            str(p["id"]): p["opciones"][0]["id"]
            for c in q["criterios"]
            for p in c["preguntas"]
        },
    )
