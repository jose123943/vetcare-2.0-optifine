import json
import uuid
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..db import insert, update
from ..http import page
from ..validation import (
    Problem,
    choice,
    clock,
    day,
    email,
    found,
    integer,
    money,
    required,
)
from .mail import notification_state

ACTIVE = ("Pendiente", "Programada", "Confirmada")


def NOW():
    return datetime.now(ZoneInfo("America/Bogota"))


PETS = "SELECT m.*,c.nombre AS propietario_nombre,c.apellido AS propietario_apellido,c.telefono,c.email FROM mascota m JOIN cliente c ON c.id_cliente=m.cliente_id"
APPOINTMENTS = """SELECT a.*,m.nombre AS mascota,c.id_cliente AS cliente_id,CONCAT(c.nombre,' ',c.apellido) AS cliente,
 CONCAT(e.nombre,' ',e.apellido) AS veterinario FROM cita a JOIN mascota m ON m.id_mascota=a.mascota_id
 JOIN cliente c ON c.id_cliente=m.cliente_id JOIN veterinario v ON v.id_veterinario=a.veterinario_id
 JOIN empleado e ON e.id_empleado=v.id_veterinario"""


def pet_data(m):
    return {
        "id": m["id_mascota"],
        "nombre": m["nombre"],
        "mascota": m["nombre"],
        "especie": m["especie"],
        "raza": m["raza"],
        "edad": m["edad"],
        "peso": str(m["peso"]),
        "sexo": m["sexo"],
        "observaciones": m["observaciones"],
        "cliente_id": m["cliente_id"],
        "cliente": m["propietario_nombre"] + " " + m["propietario_apellido"],
        "telefono": m["telefono"],
        "email": m["email"],
    }


def owner(c):
    return {
        "id": c["id_cliente"],
        **{
            k: c[k]
            for k in [
                "nombre",
                "apellido",
                "documento",
                "telefono",
                "email",
                "direccion",
                "estado",
            ]
        },
    }


def time_value(value):
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds())
        return time(seconds // 3600, seconds // 60 % 60, seconds % 60)
    return value


def appointment(c):
    hour = time_value(c["hora"])
    return {
        "id": c["id_cita"],
        **{
            k: c[k]
            for k in [
                "fecha",
                "motivo",
                "estado",
                "observaciones",
                "duracion_minutos",
                "mascota_id",
                "mascota",
                "cliente_id",
                "cliente",
                "veterinario_id",
                "veterinario",
            ]
        },
        "hora": hour.strftime("%H:%M"),
        "vencida": c["estado"] in ACTIVE
        and datetime.combine(c["fecha"], hour) < NOW().replace(tzinfo=None),
    }


def dashboard(ctx):
    today = NOW().date()
    stats = ctx.db.one(
        """SELECT (SELECT COUNT(*) FROM cita) AS total,
      (SELECT COUNT(*) FROM cita WHERE fecha=%s) AS hoy,
      (SELECT COUNT(*) FROM cita WHERE estado IN ('Pendiente','Programada','Confirmada')) AS pendientes,
      (SELECT COUNT(*) FROM cliente WHERE estado='Activo') AS clientes,
      (SELECT COUNT(*) FROM historial_de_vacunas WHERE fecha_venc<=%s) AS vacunas,
      (SELECT COUNT(*) FROM mascota) AS mascotas,(SELECT COUNT(*) FROM veterinario) AS veterinarios""",
        (today, today),
    )
    return {
        "status": "ok",
        "stats": stats,
        "citas": [
            appointment(r)
            for r in ctx.db.all(
                APPOINTMENTS
                + " WHERE a.estado IN ('Pendiente','Programada','Confirmada') ORDER BY a.fecha,a.hora,a.id_cita"
            )
        ],
    }


def customers(ctx, customer_id=None):
    if customer_id:
        return {
            "status": "ok",
            "cliente": owner(
                found(
                    ctx.db.one(
                        "SELECT * FROM cliente WHERE id_cliente=%s", (customer_id,)
                    )
                )
            ),
        }
    term = "%" + ctx.request.args.get("q", "").strip()[:150] + "%"
    rows = ctx.db.all(
        "SELECT * FROM cliente WHERE CONCAT(nombre,' ',apellido) LIKE %s OR documento LIKE %s OR telefono LIKE %s ORDER BY nombre,apellido LIMIT 100",
        (term, term, term),
    )
    return {"status": "ok", "clientes": [owner(r) for r in rows]}


def pets(ctx, customer_id=None):
    if customer_id:
        c = customers(ctx, customer_id)["cliente"]
        return {
            "status": "ok",
            "cliente": c,
            "mascotas": [
                pet_data(r)
                for r in ctx.db.all(
                    PETS + " WHERE m.cliente_id=%s ORDER BY m.id_mascota",
                    (customer_id,),
                )
            ],
        }
    q = "%" + ctx.request.args.get("q", "").strip()[:150] + "%"
    query = (
        PETS
        + " WHERE m.nombre LIKE %s OR CONCAT(c.nombre,' ',c.apellido) LIKE %s OR c.documento LIKE %s OR c.telefono LIKE %s OR c.email LIKE %s ORDER BY m.id_mascota"
    )
    return page(query, (q,) * 5, ctx, "mascotas", pet_data)


def customer_values(d, new=False):
    document = required(d, "documento", 30, optional=not new) or None
    return dict(
        nombre=required(d, "nombre", 50),
        apellido=required(d, "apellido", 50),
        documento=document,
        telefono=required(d, "telefono", 20),
        direccion=required(d, "direccion", 150),
        email=email(required(d, "email", 100, True), True),
        estado=choice(d.get("estado", "Activo"), ("Activo", "Inactivo")),
    )


def pet_values(d):
    return dict(
        nombre=required(d, "nombre", 50),
        especie=required(d, "especie", 50),
        raza=required(d, "raza", 50),
        edad=integer(d.get("edad"), "edad", 0, 100),
        peso=money(d.get("peso"), "999.99"),
        sexo=required(d, "sexo", 20, True),
        observaciones=required(d, "observaciones", 10000, True),
    )


def register_family(ctx):
    d = ctx.data
    values = customer_values(d, True)
    rows = d.get("mascotas")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 50:
        raise Problem("Registra entre 1 y 50 mascotas.")
    prepared = [pet_values(r) for r in rows]
    customer = insert(ctx.db, "cliente", values)
    columns = tuple(prepared[0]) + ("cliente_id",)
    ctx.db.many(
        "INSERT INTO mascota ("
        + ",".join("`" + k + "`" for k in columns)
        + ") VALUES ("
        + ",".join(["%s"] * len(columns))
        + ")",
        [(*r.values(), customer) for r in prepared],
    )
    return {
        "status": "ok",
        "message": f"Cliente y {len(rows)} mascota(s) registrados.",
        "cliente_id": customer,
    }


def add_pet(ctx, customer_id):
    found(
        ctx.db.one("SELECT id_cliente FROM cliente WHERE id_cliente=%s", (customer_id,))
    )
    pk = insert(ctx.db, "mascota", {**pet_values(ctx.data), "cliente_id": customer_id})
    return {"status": "ok", "message": "Mascota registrada.", "id": pk}


def pet_detail(ctx, pet_id):
    m = found(ctx.db.one(PETS + " WHERE m.id_mascota=%s", (pet_id,)))
    c = found(
        ctx.db.one("SELECT * FROM cliente WHERE id_cliente=%s", (m["cliente_id"],))
    )
    return {"status": "ok", "mascota": pet_data(m), "cliente": owner(c)}


def edit_record(ctx):
    d = ctx.data
    pk = integer(d.get("mascotaId"), "mascota", 1)
    cid = integer(d.get("clienteId"), "cliente", 1)
    found(
        ctx.db.one(
            "SELECT id_mascota FROM mascota WHERE id_mascota=%s AND cliente_id=%s FOR UPDATE",
            (pk, cid),
        )
    )
    customer = customer_values(d)
    if "estado" not in d:
        customer.pop("estado")
    pet = pet_values({**d, "nombre": d.get("nombreMascota")})
    update(ctx.db, "cliente", customer, cid, "id_cliente")
    update(ctx.db, "mascota", pet, pk, "id_mascota")
    return {"status": "ok", "message": "Cliente y mascota actualizados."}


def delete_pet(ctx, pet_id):
    found(
        ctx.db.one(
            "SELECT id_mascota FROM mascota WHERE id_mascota=%s FOR UPDATE", (pet_id,)
        )
    )
    history = ctx.db.one(
        """SELECT EXISTS(SELECT 1 FROM cita WHERE mascota_id=%s) OR
       EXISTS(SELECT 1 FROM historial_de_vacunas WHERE mascota_id=%s) OR EXISTS(SELECT 1 FROM adopciones_mascotaadopcion WHERE paciente_id=%s) AS present""",
        (pet_id,) * 3,
    )
    if history["present"]:
        raise Problem(
            "La mascota tiene historial. Se conserva para proteger sus registros."
        )
    ctx.db.execute("DELETE FROM mascota WHERE id_mascota=%s", (pet_id,))
    return {"status": "ok", "message": "Mascota eliminada. Se conserva el propietario."}


def edit_customer(ctx, customer_id):
    found(
        ctx.db.one(
            "SELECT id_cliente FROM cliente WHERE id_cliente=%s FOR UPDATE",
            (customer_id,),
        )
    )
    values = customer_values(ctx.data)
    if "estado" not in ctx.data:
        values.pop("estado")
    update(ctx.db, "cliente", values, customer_id, "id_cliente")
    return {"status": "ok", "message": "Cliente actualizado."}


def delete_customer(ctx, customer_id):
    found(
        ctx.db.one(
            "SELECT id_cliente FROM cliente WHERE id_cliente=%s FOR UPDATE",
            (customer_id,),
        )
    )
    if ctx.db.one(
        "SELECT EXISTS(SELECT 1 FROM mascota WHERE cliente_id=%s) OR EXISTS(SELECT 1 FROM factura WHERE cliente_id=%s) AS present",
        (customer_id, customer_id),
    )["present"]:
        raise Problem(
            "El cliente tiene mascotas o facturas. Puedes marcarlo como inactivo."
        )
    ctx.db.execute("DELETE FROM cliente WHERE id_cliente=%s", (customer_id,))
    return {"status": "ok", "message": "Cliente eliminado sin historiales asociados."}


def vets(ctx):
    return {
        "status": "ok",
        "veterinarios": ctx.db.all(
            "SELECT v.id_veterinario AS id,e.nombre,e.apellido,e.telefono,v.especialidad FROM veterinario v JOIN empleado e ON e.id_empleado=v.id_veterinario ORDER BY v.id_veterinario"
        ),
    }


def save_vet(ctx):
    d = ctx.data
    values = {
        k: required(d, k, 20 if k == "telefono" else 50)
        for k in ["nombre", "apellido", "telefono"]
    }
    specialty = required(d, "especialidad", 100)
    if d.get("id"):
        pk = integer(d["id"], "veterinario", 1)
        found(
            ctx.db.one(
                "SELECT id_veterinario FROM veterinario WHERE id_veterinario=%s FOR UPDATE",
                (pk,),
            )
        )
        update(ctx.db, "empleado", values, pk, "id_empleado")
        update(ctx.db, "veterinario", {"especialidad": specialty}, pk, "id_veterinario")
    else:
        pk = insert(ctx.db, "empleado", {**values, "cargo": "Veterinario"})
        insert(ctx.db, "veterinario", {"id_veterinario": pk, "especialidad": specialty})
    return {"status": "ok", "message": "Veterinario guardado.", "id": pk}


def delete_vet(ctx, vet_id):
    found(
        ctx.db.one(
            "SELECT id_veterinario FROM veterinario WHERE id_veterinario=%s FOR UPDATE",
            (vet_id,),
        )
    )
    if ctx.db.one(
        "SELECT id_cita FROM cita WHERE veterinario_id=%s LIMIT 1", (vet_id,)
    ):
        raise Problem("El veterinario tiene citas; se conserva su historial.")
    ctx.db.execute("DELETE FROM veterinario WHERE id_veterinario=%s", (vet_id,))
    ctx.db.execute("DELETE FROM empleado WHERE id_empleado=%s", (vet_id,))
    return {"status": "ok", "message": "Veterinario eliminado."}


def appointment_list(ctx, pet_id=None, pending=False):
    query = APPOINTMENTS
    params = ()
    if pet_id:
        query += " WHERE a.mascota_id=%s"
        params = (pet_id,)
    elif pending:
        query += " WHERE a.estado IN ('Pendiente','Programada','Confirmada')"
    query += (
        " ORDER BY a.fecha" + (" ASC" if pending else " DESC") + ",a.hora,a.id_cita"
    )
    return page(query, params, ctx, "citas", appointment)


def appointment_detail(ctx, appointment_id):
    c = found(ctx.db.one(APPOINTMENTS + " WHERE a.id_cita=%s", (appointment_id,)))
    ns = ctx.db.all(
        "SELECT id,estado,intentos,error,creada FROM pagInicio_notificacion WHERE cita_id=%s ORDER BY id",
        (appointment_id,),
    )
    return {"status": "ok", "cita": appointment(c), "notificaciones": ns}


def save_appointment(ctx, appointment_id=None):
    d = ctx.data
    values = dict(
        fecha=day(d.get("fecha")),
        hora=clock(d.get("hora")),
        motivo=required(d, "motivo", 200),
        estado=choice(d.get("estado", "Pendiente"), (*ACTIVE, "Atendida", "Cancelada")),
        observaciones=required(d, "observaciones", 10000, True),
        duracion_minutos=integer(d.get("duracion_minutos", 30), "duración", 5, 480),
    )
    mid = integer(d.get("mascota"), "mascota", 1)
    cid = integer(d.get("cliente_id"), "cliente", 1)
    vid = integer(d.get("veterinario"), "veterinario", 1)
    m = found(
        ctx.db.one(
            "SELECT m.nombre,c.nombre AS cliente_nombre,c.apellido,c.email FROM mascota m JOIN cliente c ON c.id_cliente=m.cliente_id WHERE m.id_mascota=%s AND m.cliente_id=%s",
            (mid, cid),
        )
    )
    old = (
        found(
            ctx.db.one(
                "SELECT * FROM cita WHERE id_cita=%s FOR UPDATE", (appointment_id,)
            )
        )
        if appointment_id
        else None
    )
    ids = sorted({vid, old["veterinario_id"]} if old else {vid})
    rows = ctx.db.all(
        "SELECT v.id_veterinario,e.nombre,e.apellido FROM veterinario v JOIN empleado e ON e.id_empleado=v.id_veterinario WHERE v.id_veterinario IN ("
        + ",".join(["%s"] * len(ids))
        + ") ORDER BY v.id_veterinario FOR UPDATE",
        ids,
    )
    vet = next((v for v in rows if v["id_veterinario"] == vid), None)
    if not vet:
        raise Problem("El veterinario no existe.", 404)
    start = datetime.combine(values["fecha"], values["hora"])
    end = start + timedelta(minutes=values["duracion_minutos"])
    if start.date() != end.date():
        raise Problem("La cita debe terminar el mismo día.")
    if values["estado"] in ACTIVE:
        # Segundos numéricos: evita comparaciones lexicográficas entre TIME(6)
        # y parámetros, que pueden tratar una hora adyacente como solapada.
        conflict = ctx.db.one(
            "SELECT id_cita FROM cita WHERE veterinario_id=%s AND fecha=%s AND estado IN ('Pendiente','Programada','Confirmada') AND id_cita<>%s AND TIME_TO_SEC(hora)<TIME_TO_SEC(%s) AND TIME_TO_SEC(hora)+duracion_minutos*60>TIME_TO_SEC(%s) LIMIT 1",
            (vid, values["fecha"], appointment_id or 0, end.time(), start.time()),
        )
        if conflict:
            raise Problem("El veterinario tiene otra cita en ese horario.")
    values.update(mascota_id=mid, veterinario_id=vid, cliente_id=cid)
    if old:
        update(ctx.db, "cita", values, appointment_id, "id_cita")
        pk = appointment_id
    else:
        pk = insert(ctx.db, "cita", values)
    changed = old is None or any(
        str(old[k] if k != "hora" else time_value(old[k])) != str(values[k])
        for k in values
    )
    if changed:
        context = dict(
            cliente=m["cliente_nombre"] + " " + m["apellido"],
            mascota=m["nombre"],
            veterinario=vet["nombre"] + " " + vet["apellido"],
            fecha=values["fecha"].isoformat(),
            hora=values["hora"].strftime("%H:%M"),
            motivo=values["motivo"],
            estado=values["estado"],
        )
        insert(
            ctx.db,
            "pagInicio_notificacion",
            dict(
                cita_id=pk,
                revision=uuid.uuid4().hex,
                destinatario=m["email"],
                asunto=("Actualización" if old else "Confirmación")
                + " de cita veterinaria — VetCare",
                contexto=json.dumps(context, ensure_ascii=False),
                estado=notification_state(m["email"]),
                intentos=0,
                error="",
                creada=datetime.now(UTC).replace(tzinfo=None),
                enviada=None,
            ),
        )
    return {
        "status": "ok",
        "message": "Cita guardada. "
        + {
            "Pendiente": "Correo en cola.",
            "Sin correo": "Cliente sin correo; no se enviará notificación.",
            "Demostración": "Datos de demostración; no se enviará correo real.",
        }[notification_state(m["email"])],
        "cita": appointment(
            found(ctx.db.one(APPOINTMENTS + " WHERE a.id_cita=%s", (pk,)))
        ),
    }


def vaccines(ctx, pet_id):
    rows = ctx.db.all(
        "SELECT id_vacuna AS id,nombre_vacuna AS nombre,fecha_aplic AS fecha_aplicacion,fecha_venc AS fecha_vencimiento,lote FROM historial_de_vacunas WHERE mascota_id=%s ORDER BY fecha_aplic DESC",
        (pet_id,),
    )
    for r in rows:
        r["dias_para_vencer"] = (r["fecha_vencimiento"] - NOW().date()).days
    return {"status": "ok", "vacunas": rows}


def save_vaccine(ctx):
    d = ctx.data
    applied = day(d.get("fecha_aplicacion"))
    expires = day(d.get("fecha_vencimiento"))
    if expires < applied:
        raise Problem("El vencimiento no puede ser anterior a la aplicación.")
    mid = integer(d.get("mascota_id"), "mascota", 1)
    found(ctx.db.one("SELECT id_mascota FROM mascota WHERE id_mascota=%s", (mid,)))
    pk = insert(
        ctx.db,
        "historial_de_vacunas",
        dict(
            nombre_vacuna=required(d, "nombre_vacuna", 100),
            fecha_aplic=applied,
            fecha_venc=expires,
            lote=required(d, "lote", 50),
            mascota_id=mid,
        ),
    )
    return {"status": "ok", "message": "Vacuna registrada.", "id": pk}


def treatments(ctx, pet_id):
    rows = ctx.db.all(
        "SELECT t.id_tratamiento AS id,t.descripcion,t.medicamento,t.dosis,t.duracion,t.fecha_inicio,a.fecha AS cita_fecha,a.motivo AS cita_motivo FROM tratamiento t JOIN cita a ON a.id_cita=t.cita_id WHERE a.mascota_id=%s ORDER BY t.fecha_inicio DESC",
        (pet_id,),
    )
    return {"status": "ok", "tratamientos": rows}


def save_treatment(ctx):
    d = ctx.data
    cid = integer(d.get("cita_id"), "cita", 1)
    found(ctx.db.one("SELECT id_cita FROM cita WHERE id_cita=%s", (cid,)))
    pk = insert(
        ctx.db,
        "tratamiento",
        dict(
            cita_id=cid,
            fecha_inicio=day(d.get("fecha_inicio")),
            descripcion=required(d, "descripcion", 200),
            medicamento=required(d, "medicamento", 100),
            dosis=required(d, "dosis", 50),
            duracion=required(d, "duracion", 50),
        ),
    )
    return {"status": "ok", "message": "Tratamiento registrado.", "id": pk}
