# Prepara datos ficticios o limpia datos operativos cuando se solicita expresamente.
"""Datos ficticios de formación; limpieza transaccional autorizada por el operador."""

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

from werkzeug.datastructures import MultiDict

from .db import insert
from .services import adoptions, billing, clinic

# Se limpian primero los registros dependientes para respetar las relaciones entre tablas.
OPERATIONAL_TABLES = (
    "adopciones_entrega",
    "adopciones_revision",
    "adopciones_respuesta",
    "adopciones_solicitud",
    "adopciones_mascotaadopcion",
    "evaluacion_adopcion",
    "adopcion",
    "factura_detallefactura",
    "factura",
    "tratamiento",
    "historial_de_vacunas",
    "pagInicio_notificacion",
    "pagInicio_operacion",
    "cita",
    "mascota",
    "veterinario",
    "empleado",
    "cliente",
    "django_admin_log",
    "django_session",
    "vc_login_bucket",
)
# Conserva cuentas y cuestionarios necesarios para seguir usando la aplicación después de limpiar.
CONFIGURATION_TABLES = {
    "adopciones_cuestionario",
    "adopciones_criterio",
    "adopciones_pregunta",
    "adopciones_opcion",
    "auth_user",
    "auth_group",
    "auth_permission",
    "auth_group_permissions",
    "auth_user_groups",
    "auth_user_user_permissions",
    "administrador",
    "django_content_type",
    "django_migrations",
    "vc_schema_migration",
    "vc_session",
    "vc_session_scope",
}

FAMILIES = [
    (
        "Laura",
        "Martínez",
        [
            ("Luna", "Gato", "Hembra", 3, "4.20"),
            ("Simón", "Perro", "Macho", 2, "12.50"),
        ],
    ),
    ("Carlos", "Gómez", [("Rocky", "Perro", "Macho", 4, "20.00")]),
    (
        "Ana",
        "Torres",
        [
            ("Mía", "Gato", "Hembra", 1, "3.80"),
            ("Bruno", "Perro", "Macho", 5, "18.00"),
            ("Kiara", "Gato", "Hembra", 2, "4.00"),
        ],
    ),
    ("Diego", "Ramírez", [("Toby", "Perro", "Macho", 2, "8.50")]),
    (
        "Sofía",
        "Castro",
        [("Nina", "Perro", "Hembra", 3, "10.00"), ("Leo", "Gato", "Macho", 2, "4.80")],
    ),
]
VETERINARIANS = [
    ("Valentina", "Rojas", "Medicina general"),
    ("Andrés", "Herrera", "Medicina felina"),
    ("Camila", "Mendoza", "Prevención y bienestar"),
    ("Sebastián", "López", "Consulta general"),
    ("Daniela", "Morales", "Seguimiento clínico"),
]
RESCUES = [
    ("Nala", "Gato", "Hembra"),
    ("Max", "Perro", "Macho"),
    ("Mila", "Gato", "Hembra"),
    ("Coco", "Perro", "Macho"),
    ("Olivia", "Gato", "Hembra"),
]


# Obtiene conteos sin exponer nombres, correos u otros datos de personas.
def table_counts(db):
    names = [next(iter(row.values())) for row in db.all("SHOW TABLES")]
    return {
        name: db.one("SELECT COUNT(*) AS n FROM `" + name.replace("`", "``") + "`")["n"]
        for name in names
    }


# Valida tablas conocidas, limpia hijos/relaciones operativas y conserva superusuarios y configuración.
def clear_operational_data(db):
    """Se ejecuta dentro de la transacción del llamador, sin desactivar claves foráneas."""
    existing = set(table_counts(db))
    unknown = existing - set(OPERATIONAL_TABLES) - CONFIGURATION_TABLES
    if unknown:
        raise RuntimeError(
            "Hay tablas sin clasificar; no se limpia: " + ", ".join(sorted(unknown))
        )
    supers = db.all(
        "SELECT * FROM auth_user WHERE is_superuser=1 ORDER BY id FOR UPDATE"
    )
    if not supers:
        raise RuntimeError("No se limpia una base sin superusuarios existentes.")
    # Rompe la referencia circular del esquema histórico respetando sus CHECK.
    db.execute(
        "UPDATE adopcion SET estado='cancelada',activa=NULL,cliente_adoptante_id=NULL,"
        "evaluacion_aprobada_id=NULL,fecha_adopcion=NULL,fecha_cierre=COALESCE(fecha_cierre,UTC_TIMESTAMP(6))"
    )
    for table in OPERATIONAL_TABLES:
        db.execute("DELETE FROM `" + table + "`")
    db.execute(
        "DELETE FROM vc_session WHERE user_id IS NULL OR user_id IN (SELECT id FROM auth_user WHERE is_superuser=0)"
    )
    for table in ("auth_user_groups", "auth_user_user_permissions"):
        db.execute(
            "DELETE FROM `"
            + table
            + "` WHERE user_id IN (SELECT id FROM auth_user WHERE is_superuser=0)"
        )
    db.execute(
        "DELETE FROM administrador WHERE id_administrador IN (SELECT id FROM auth_user WHERE is_superuser=0)"
    )
    db.execute("DELETE FROM auth_user WHERE is_superuser=0")
    return supers


# Calcula y guarda respuestas y puntuación de una solicitud ficticia con el motor real.
def save_demo_application(ctx, pet_id, index, questionnaire, base_date):
    """Solicitud de ejemplo con respuestas y evaluación calculadas por el motor real."""
    applicant = dict(
        nombre=f"Solicitante de demostración {index}",
        documento=f"DEMO-ADOP-{index:03d}",
        edad=25 + index,
        telefono=f"00000000{index:02d}",
        email=f"adopcion{index}@vetcare.example.invalid",
        direccion=f"Dirección ficticia {index}",
        ocupacion="Datos de demostración",
        ingreso_aproximado="Recursos ficticios de formación",
        presupuesto_cop=200000,
        tipo_vivienda="Apartamento",
        tenencia_vivienda="Familiar",
        consentimiento=True,
    )
    choose = max if index <= 3 else min
    answers = {
        str(p["id"]): choose(p["opciones"], key=lambda o: o["valor"])["id"]
        for c in questionnaire["criterios"]
        for p in c["preguntas"]
    }
    result = adoptions.evaluate(questionnaire, answers)
    values = adoptions.application_values(applicant)
    values.update(
        codigo=uuid.uuid4().hex,
        mascota_id=pet_id,
        cuestionario_id=questionnaire["id"],
        porcentaje=result["porcentaje"],
        aprobada=result["aprobada"],
        evaluacion=json.dumps(result["evaluacion"], ensure_ascii=False),
        alertas=json.dumps(result["alertas"], ensure_ascii=False),
        recomendaciones=json.dumps(result["recomendaciones"], ensure_ascii=False),
        estado="Pendiente",
        clave="demo-" + uuid.uuid4().hex,
        huella=hashlib.sha256(json.dumps(answers, sort_keys=True).encode()).hexdigest(),
        propietario_sesion=secrets.token_hex(32),
        creada=datetime.combine(base_date, datetime.min.time())
        + timedelta(hours=9, minutes=index),
    )
    pk = insert(ctx.db, "adopciones_solicitud", values)
    ctx.db.many(
        "INSERT INTO adopciones_respuesta(solicitud_id,pregunta_id,opcion_id,original) VALUES (%s,%s,%s,%s)",
        [
            (
                pk,
                r["pregunta_id"],
                r["opcion_id"],
                json.dumps(r["original"], ensure_ascii=False),
            )
            for r in result["snapshots"]
        ],
    )


# Carga el conjunto completo dentro de una transacción y verifica conteos, relaciones y conservación de cuentas.
def prepare_demo(db, base_date):
    """Reemplaza datos operativos y verifica el resultado antes del COMMIT exterior."""
    supers = clear_operational_data(db)
    actor = next(
        (row["id"] for row in supers if row["is_active"] and row["is_staff"]),
        supers[0]["id"],
    )
    ctx = SimpleNamespace(
        db=db,
        data={},
        session={"user_id": actor},
        request=SimpleNamespace(args=MultiDict()),
    )
    questionnaire = adoptions.questionnaire(ctx)
    customers = []
    pets = []
    vets = []
    appointments = []
    invoices = []
    rescues = []
    for index, (first, last, animals) in enumerate(FAMILIES, 1):
        ctx.data = dict(
            nombre=first,
            apellido=last,
            documento=f"DEMO-CLI-{index:03d}",
            telefono=f"00000000{index:02d}",
            direccion=f"Dirección ficticia de demostración {index}",
            email=f"cliente{index}@vetcare.example.invalid",
            mascotas=[
                dict(
                    nombre=name,
                    especie=species,
                    raza="Criollo",
                    sexo=sex,
                    edad=age,
                    peso=weight,
                    observaciones="Paciente ficticio para demostración; no usar como historia clínica real.",
                )
                for name, species, sex, age, weight in animals
            ],
        )
        customer = clinic.register_family(ctx)["cliente_id"]
        customers.append(customer)
        pets.append(clinic.pets(ctx, customer)["mascotas"])
    for index, (first, last, specialty) in enumerate(VETERINARIANS, 1):
        ctx.data = dict(
            nombre=first,
            apellido=last,
            telefono=f"00000001{index:02d}",
            especialidad=specialty,
        )
        vets.append(clinic.save_vet(ctx)["id"])
    for index in range(5):
        day = base_date + timedelta(days=index - 2)
        ctx.data = dict(
            cliente_id=customers[index],
            mascota=pets[index][0]["id"],
            veterinario=vets[index],
            fecha=day.isoformat(),
            hora=f"{9 + index:02d}:00",
            duracion_minutos=30,
            motivo=[
                "Consulta de control (demo)",
                "Revisión general (demo)",
                "Control preventivo (demo)",
                "Valoración inicial (demo)",
                "Seguimiento (demo)",
            ][index],
            estado="Programada",
            observaciones="Registro ficticio de capacitación.",
        )
        appointment = clinic.save_appointment(ctx)["cita"]
        appointments.append(appointment["id"])
        db.execute(
            "UPDATE pagInicio_notificacion SET estado='Demostración',error='Ejemplo: no se envían correos reales.' WHERE cita_id=%s",
            (appointment["id"],),
        )
        ctx.data = dict(
            cita_id=appointment["id"],
            cliente_id=customers[index],
            estado_pago="Pagada" if index < 2 else "Pendiente",
            metodo_pago="Efectivo"
            if index == 0
            else "Transferencia"
            if index == 1
            else "Tarjeta",
            descuento=5000 if index == 1 else 0,
            impuesto=0,
            servicios=[
                dict(
                    servicio="Consulta de demostración",
                    cantidad=1,
                    precio_unitario=str(40000 + index * 5000),
                ),
                dict(
                    servicio="Servicio complementario de demostración",
                    cantidad=1,
                    precio_unitario="15000",
                ),
            ],
        )
        invoices.append(billing.save(ctx)["id"])
        ctx.data = dict(
            mascota_id=pets[index][0]["id"],
            nombre_vacuna="Vacuna de demostración",
            lote=f"DEMO-{index + 1:03d}",
            fecha_aplicacion=(base_date - timedelta(days=30 + index)).isoformat(),
            fecha_vencimiento=(base_date + timedelta(days=330 - index)).isoformat(),
        )
        clinic.save_vaccine(ctx)
        ctx.data = dict(
            cita_id=appointment["id"],
            fecha_inicio=day.isoformat(),
            descripcion="Plan de seguimiento ficticio; no constituye indicación médica.",
            medicamento="Producto de demostración",
            dosis="Dato ficticio; sin pauta clínica",
            duracion="Ejemplo de seguimiento",
        )
        clinic.save_treatment(ctx)
    for index, (name, species, sex) in enumerate(RESCUES, 1):
        ctx.data = dict(
            nombre=name,
            especie=species,
            raza="Criollo",
            sexo=sex,
            edad_aproximada=f"{index % 3 + 1} años",
            peso="4.50" if species == "Gato" else "12.00",
            ingreso=(base_date - timedelta(days=5 + index)).isoformat(),
            esterilizada=index % 2 == 0,
            estado="Disponible",
            paciente="",
            descripcion=f"{name} forma parte del catálogo ficticio de formación de VetCare.",
            personalidad="Ejemplo de ficha: tranquila y sociable.",
            salud="Ficha simulada; requiere valoración veterinaria real.",
            vacunacion="Registro de demostración; no es certificado clínico.",
            necesidades="Datos ficticios para practicar el proceso de adopción.",
        )
        pet = adoptions.save_pet(ctx)["mascota"]
        rescues.append(pet["id"])
        save_demo_application(ctx, pet["id"], index, questionnaire, base_date)
    clinic.complete_finished_appointments(db)
    after = db.all("SELECT * FROM auth_user WHERE is_superuser=1 ORDER BY id")
    if supers != after:
        raise RuntimeError(
            "La verificación detectó cambios en los superusuarios; se revierte la operación."
        )
    counts = table_counts(db)
    expected = {
        "cliente": 5,
        "mascota": 9,
        "veterinario": 5,
        "empleado": 5,
        "cita": 5,
        "factura": 5,
        "factura_detallefactura": 10,
        "historial_de_vacunas": 5,
        "tratamiento": 5,
        "adopciones_mascotaadopcion": 5,
        "adopciones_solicitud": 5,
        "adopciones_respuesta": 5
        * sum(len(c["preguntas"]) for c in questionnaire["criterios"]),
        "pagInicio_notificacion": 5,
    }
    if any(counts.get(table) != number for table, number in expected.items()):
        raise RuntimeError("Los conteos no coinciden; se revierte la operación.")
    if db.one(
        "SELECT COUNT(*) AS n FROM pagInicio_notificacion WHERE estado='Pendiente'"
    )["n"]:
        raise RuntimeError("La demostración dejó correos pendientes; se revierte.")
    if db.one("SELECT COUNT(*) AS n FROM auth_user WHERE is_superuser=0")["n"]:
        raise RuntimeError("Quedaron cuentas no autorizadas; se revierte.")
    return {
        "fecha_base": base_date.isoformat(),
        "superusuarios_conservados": len(supers),
        "superusuarios_sin_cambios": True,
        "conteos": expected,
        "clientes_ids": customers,
        "mascotas_clinicas_ids": [[p["id"] for p in group] for group in pets],
        "veterinarios_ids": vets,
        "citas_ids": appointments,
        "facturas_ids": invoices,
        "adopcion_ids": rescues,
        "avisos_reales_en_cola": 0,
    }
