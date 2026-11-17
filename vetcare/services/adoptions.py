import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal, localcontext
from fractions import Fraction

from ..db import insert, update
from ..http import page
from ..security import ensure_session
from ..validation import Problem, choice, day, email, found, integer, money, required

PET_FIELDS = [
    "nombre",
    "especie",
    "raza",
    "sexo",
    "edad_aproximada",
    "peso",
    "descripcion",
    "personalidad",
    "salud",
    "vacunacion",
    "esterilizada",
    "necesidades",
    "ingreso",
    "estado",
]


def load_json(value):
    return json.loads(value) if isinstance(value, str) else value


def pet_data(p, private=False):
    result = {k: p[k] for k in PET_FIELDS}
    result["id"] = p["id"]
    result["esterilizada"] = bool(p["esterilizada"])
    result["fotografia"] = (
        f"/adopciones/fotos/{p['id']}/?v={p['actualizada'].strftime('%Y%m%d%H%M%S%f')}"
        if p["fotografia"]
        else ""
    )
    if private:
        result["paciente"] = p["paciente_id"]
    return result


def catalog(ctx, private=False):
    params = []
    query = "SELECT * FROM adopciones_mascotaadopcion"
    filters = []
    if not private:
        filters.append("estado IN ('Disponible','En proceso')")
    if ctx.request.args.get("especie"):
        filters.append("especie=%s")
        params.append(ctx.request.args["especie"][:50])
    if ctx.request.args.get("q"):
        filters.append("(nombre LIKE %s OR raza LIKE %s OR descripcion LIKE %s)")
        params.extend(["%" + ctx.request.args["q"][:100] + "%"] * 3)
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY ingreso DESC,id DESC"
    return page(
        query, tuple(params), ctx, "mascotas", lambda p: pet_data(p, private), 24, True
    )


def public_pet(ctx, pet_id):
    pet = found(
        ctx.db.one(
            "SELECT * FROM adopciones_mascotaadopcion WHERE id=%s AND estado='Disponible'",
            (pet_id,),
        )
    )
    return {"status": "ok", "mascota": pet_data(pet)}


def questionnaire(ctx, qid=None):
    q = (
        ctx.db.one("SELECT * FROM adopciones_cuestionario WHERE id=%s", (qid,))
        if qid
        else ctx.db.one(
            "SELECT * FROM adopciones_cuestionario WHERE activa=1 ORDER BY id DESC LIMIT 1"
        )
    )
    found(q)
    rows = ctx.db.all(
        """SELECT c.id AS cid,c.nombre AS criterio,c.peso,c.recomendacion,c.orden AS corden,
      p.id AS pid,p.texto AS pregunta,p.orden AS porden,o.id AS oid,o.texto AS opcion,o.valor,o.alerta,o.orden AS oorden
      FROM adopciones_criterio c JOIN adopciones_pregunta p ON p.criterio_id=c.id
      JOIN adopciones_opcion o ON o.pregunta_id=p.id WHERE c.cuestionario_id=%s ORDER BY c.orden,c.id,p.orden,p.id,o.orden,o.id""",
        (q["id"],),
    )
    groups = {}
    for r in rows:
        c = groups.setdefault(
            r["cid"],
            dict(
                id=r["cid"],
                nombre=r["criterio"],
                peso=r["peso"],
                recomendacion=r["recomendacion"],
                preguntas={},
            ),
        )
        p = c["preguntas"].setdefault(
            r["pid"], dict(id=r["pid"], texto=r["pregunta"], opciones=[])
        )
        p["opciones"].append(
            dict(id=r["oid"], texto=r["opcion"], valor=r["valor"], alerta=r["alerta"])
        )
    for c in groups.values():
        c["preguntas"] = list(c["preguntas"].values())
    q["criterios"] = list(groups.values())
    return q


def schema(ctx):
    q = questionnaire(ctx)
    return {
        "status": "ok",
        "id": q["id"],
        "nombre": q["nombre"],
        "criterios": [
            dict(
                id=c["id"],
                nombre=c["nombre"],
                peso=c["peso"],
                preguntas=[
                    dict(
                        id=p["id"],
                        texto=p["texto"],
                        opciones=[
                            dict(id=o["id"], texto=o["texto"]) for o in p["opciones"]
                        ],
                    )
                    for p in c["preguntas"]
                ],
            )
            for c in q["criterios"]
        ],
    }


def evaluate(q, answers):
    if not isinstance(answers, dict) or sum(c["peso"] for c in q["criterios"]) != 100:
        raise Problem("El cuestionario debe sumar 100 puntos.")
    expected = {str(p["id"]) for c in q["criterios"] for p in c["preguntas"]}
    if set(answers) != expected:
        raise Problem(
            "Responde todas las preguntas de la versión indicada, sin añadir otras."
        )
    total = Fraction(0)
    details = []
    snapshots = []
    alerts = []
    recommendations = []
    for c in q["criterios"]:
        score = 0
        if not c["preguntas"]:
            raise Problem("Criterio sin preguntas.")
        for p in c["preguntas"]:
            option = next(
                (
                    o
                    for o in p["opciones"]
                    if str(o["id"]) == str(answers[str(p["id"])])
                ),
                None,
            )
            if not option or not 0 <= option["valor"] <= 100:
                raise Problem("Una respuesta no corresponde a la pregunta.")
            score += option["valor"]
            if option["alerta"]:
                alerts.append(option["alerta"])
            snapshots.append(
                dict(
                    pregunta_id=p["id"],
                    opcion_id=option["id"],
                    original=dict(
                        pregunta=p["texto"],
                        respuesta=option["texto"],
                        valor=option["valor"],
                        criterio=c["nombre"],
                        peso=c["peso"],
                    ),
                )
            )
        points = Fraction(score * c["peso"], len(c["preguntas"]) * 100)
        total += points
        details.append(
            dict(criterio=c["nombre"], obtenidos=str(float(points)), posibles=c["peso"])
        )
        if points < Fraction(c["peso"] * 67, 100):
            recommendations.append(c["recomendacion"])
    with localcontext() as context:
        context.prec = 40
        percentage = (Decimal(total.numerator) / Decimal(total.denominator)).quantize(
            Decimal(".000001"), rounding=ROUND_DOWN
        )
    return dict(
        porcentaje=percentage,
        aprobada=total >= 67,
        evaluacion=details,
        snapshots=snapshots,
        alertas=list(dict.fromkeys(alerts)),
        recomendaciones=recommendations,
    )


def public_result(s):
    code = str(uuid.UUID(str(s["codigo"])))
    return dict(
        codigo=code,
        porcentaje=str(s["porcentaje"].quantize(Decimal(".01"), rounding=ROUND_DOWN)),
        aprobada=bool(s["aprobada"]),
        estado=s["estado"],
        alertas=load_json(s["alertas"]),
        revisar=bool(load_json(s["alertas"])),
        recomendaciones=load_json(s["recomendaciones"]),
        color="passed" if s["aprobada"] else "near" if s["porcentaje"] >= 50 else "low",
        url=f"/adopciones/solicitud/{code}/",
    )


def application_values(d):
    if d.get("consentimiento") is not True:
        raise Problem("Es necesario autorizar el uso de datos para esta solicitud.")
    values = {
        k: required(d, k, n)
        for k, n in [
            ("nombre", 150),
            ("documento", 30),
            ("telefono", 30),
            ("direccion", 200),
            ("ocupacion", 100),
        ]
    }
    values.update(
        edad=integer(d.get("edad"), "edad", 18, 120),
        email=email(d.get("email")),
        presupuesto_cop=integer(d.get("presupuesto_cop"), "presupuesto", 0),
        ingreso_aproximado=required(d, "ingreso_aproximado", 80, True),
        tipo_vivienda=required(d, "tipo_vivienda", 50, True),
        tenencia_vivienda=required(d, "tenencia_vivienda", 50, True),
    )
    return values


def apply(ctx, pet_id):
    data = ctx.data
    sess = ensure_session(ctx)
    key = ctx.request.headers.get("Idempotency-Key", "")
    if not key or len(key) > 100:
        raise Problem("Falta una clave de operación válida.")
    if set(data) - {"solicitante", "respuestas", "cuestionario"}:
        raise Problem("La puntuación se calcula exclusivamente en el servidor.")
    fingerprint = hashlib.sha256(
        (str(pet_id) + json.dumps(data, sort_keys=True)).encode()
    ).hexdigest()

    def replay(previous):
        if not secrets.compare_digest(
            previous["propietario_sesion"], sess["owner_hash"]
        ):
            raise Problem("Solicitud no disponible para esta sesión.", 403)
        if previous["huella"] != fingerprint:
            raise Problem("Esta operación ya se utilizó con otras respuestas.", 409)
        return {"status": "ok", "resultado": public_result(previous)}

    previous = ctx.db.one("SELECT * FROM adopciones_solicitud WHERE clave=%s", (key,))
    if previous:
        return replay(previous)
    values = application_values(data.get("solicitante", {}))
    with ctx.db.atomic():
        pet = found(
            ctx.db.one(
                "SELECT id,estado FROM adopciones_mascotaadopcion WHERE id=%s FOR UPDATE",
                (pet_id,),
            )
        )
        # Reconsulta después del bloqueo para resolver reenvíos concurrentes.
        previous = ctx.db.one(
            "SELECT * FROM adopciones_solicitud WHERE clave=%s", (key,)
        )
        if previous:
            return replay(previous)
        if pet["estado"] != "Disponible":
            raise Problem("Esta mascota no recibe nuevas solicitudes.")
        count = ctx.db.one(
            "SELECT COUNT(*) AS n FROM adopciones_solicitud WHERE propietario_sesion=%s AND creada>=UTC_TIMESTAMP()-INTERVAL 10 MINUTE",
            (sess["owner_hash"],),
        )["n"]
        if count >= 5:
            raise Problem("Espera unos minutos antes de enviar más solicitudes.", 429)
        q = questionnaire(ctx, integer(data.get("cuestionario"), "cuestionario", 1))
        if not q["activa"]:
            raise Problem(
                "La encuesta cambió. Recarga el catálogo para usar la versión vigente."
            )
        result = evaluate(q, data.get("respuestas"))
        values.update(
            codigo=uuid.uuid4().hex,
            mascota_id=pet_id,
            cuestionario_id=q["id"],
            porcentaje=result["porcentaje"],
            aprobada=result["aprobada"],
            evaluacion=json.dumps(result["evaluacion"], ensure_ascii=False),
            alertas=json.dumps(result["alertas"], ensure_ascii=False),
            recomendaciones=json.dumps(result["recomendaciones"], ensure_ascii=False),
            estado="Pendiente",
            clave=key,
            huella=fingerprint,
            propietario_sesion=sess["owner_hash"],
            creada=datetime.now(UTC).replace(tzinfo=None),
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
        values["id"] = pk
    return {"status": "ok", "resultado": public_result(values)}


def own_result(ctx, code):
    s = found(
        ctx.db.one(
            "SELECT * FROM adopciones_solicitud WHERE codigo=%s",
            (uuid.UUID(str(code)).hex,),
        )
    )
    if not secrets.compare_digest(
        s["propietario_sesion"], ensure_session(ctx)["owner_hash"]
    ):
        raise Problem("La solicitud no está disponible para esta sesión.", 404)
    return {"status": "ok", "resultado": public_result(s)}


def save_pet(ctx):
    d = ctx.data
    old = (
        found(
            ctx.db.one(
                "SELECT * FROM adopciones_mascotaadopcion WHERE id=%s FOR UPDATE",
                (integer(d["id"], "mascota", 1),),
            )
        )
        if d.get("id")
        else None
    )
    fields = {
        k: required(d, k, n, k in ("raza", "necesidades"))
        for k, n in [
            ("nombre", 80),
            ("especie", 50),
            ("raza", 80),
            ("sexo", 20),
            ("edad_aproximada", 60),
            ("descripcion", 10000),
            ("personalidad", 10000),
            ("salud", 10000),
            ("vacunacion", 10000),
            ("necesidades", 10000),
        ]
    }
    state = choice(
        d.get("estado", old["estado"] if old else "Disponible"),
        ("Disponible", "En proceso", "Adoptada", "No disponible"),
    )
    if state == "Adoptada" and (not old or old["estado"] != "Adoptada"):
        raise Problem("Registra la entrega para marcar la mascota como adoptada.")
    if old and old["estado"] == "Adoptada" and state != "Adoptada":
        raise Problem("Esta mascota ya tiene una entrega registrada.")
    if state == "En proceso" and (not old or old["estado"] != "En proceso"):
        raise Problem("Autoriza una solicitud para iniciar el proceso.")
    if old and old["estado"] == "En proceso" and state != "En proceso":
        raise Problem("Revisa primero la solicitud autorizada.")
    patient = integer(d["paciente"], "paciente", 1) if d.get("paciente") else None
    if patient:
        found(
            ctx.db.one("SELECT id_mascota FROM mascota WHERE id_mascota=%s", (patient,))
        )
    fields.update(
        peso=money(d.get("peso"), "9999.99"),
        ingreso=day(d.get("ingreso")),
        esterilizada=d.get("esterilizada") is True,
        estado=state,
        paciente_id=patient,
        actualizada=datetime.now(UTC).replace(tzinfo=None),
    )
    if old:
        update(ctx.db, "adopciones_mascotaadopcion", fields, old["id"])
        pk = old["id"]
    else:
        pk = insert(ctx.db, "adopciones_mascotaadopcion", {**fields, "fotografia": ""})
    return {
        "status": "ok",
        "message": "Mascota de adopción guardada.",
        "mascota": pet_data(
            found(
                ctx.db.one(
                    "SELECT * FROM adopciones_mascotaadopcion WHERE id=%s", (pk,)
                )
            ),
            True,
        ),
    }


def applicant_data(s):
    return {
        **public_result(s),
        **{
            k: s[k]
            for k in [
                "id",
                "nombre",
                "documento",
                "edad",
                "telefono",
                "email",
                "direccion",
                "ocupacion",
                "presupuesto_cop",
                "ingreso_aproximado",
                "tipo_vivienda",
                "tenencia_vivienda",
                "mascota_id",
                "creada",
            ]
        },
        "mascota": s["mascota"],
        "evaluacion": load_json(s["evaluacion"]),
    }


def applications(ctx):
    query = "SELECT s.*,m.nombre AS mascota FROM adopciones_solicitud s JOIN adopciones_mascotaadopcion m ON m.id=s.mascota_id"
    params = ()
    if ctx.request.args.get("aprobada") in ("true", "false"):
        query += " WHERE s.aprobada=%s"
        params = (ctx.request.args["aprobada"] == "true",)
    return page(
        query + " ORDER BY s.id DESC",
        params,
        ctx,
        "solicitudes",
        applicant_data,
        24,
        True,
    )


def detail(ctx, application_id):
    s = found(
        ctx.db.one(
            "SELECT s.*,m.nombre AS mascota FROM adopciones_solicitud s JOIN adopciones_mascotaadopcion m ON m.id=s.mascota_id WHERE s.id=%s",
            (application_id,),
        )
    )
    return {
        "status": "ok",
        "solicitud": applicant_data(s),
        "respuestas": [
            load_json(r["original"])
            for r in ctx.db.all(
                "SELECT original FROM adopciones_respuesta WHERE solicitud_id=%s ORDER BY id",
                (application_id,),
            )
        ],
        "revisiones": ctx.db.all(
            "SELECT accion,notas,fecha,responsable_id,bienestar_verificado FROM adopciones_revision WHERE solicitud_id=%s ORDER BY id",
            (application_id,),
        ),
    }


def review(ctx, application_id):
    d = ctx.data
    sid = found(
        ctx.db.one(
            "SELECT mascota_id FROM adopciones_solicitud WHERE id=%s", (application_id,)
        )
    )
    p = found(
        ctx.db.one(
            "SELECT * FROM adopciones_mascotaadopcion WHERE id=%s FOR UPDATE",
            (sid["mascota_id"],),
        )
    )
    s = found(
        ctx.db.one(
            "SELECT * FROM adopciones_solicitud WHERE id=%s FOR UPDATE",
            (application_id,),
        )
    )
    action = choice(d.get("accion"), ("Autorizar", "Rechazar", "Entregar"), "acción")
    notes = required(d, "notas", 10000)
    verified = d.get("bienestar_verificado") is True
    if p["estado"] == "Adoptada" or s["estado"] == "Entregada":
        raise Problem("La mascota ya tiene una entrega registrada.")
    if action in ("Autorizar", "Entregar"):
        if not s["aprobada"] or s["porcentaje"] < 67:
            raise Problem("La evaluación debe alcanzar al menos el 67 % sin redondeos.")
        if not verified:
            raise Problem(
                "Confirma la revisión de respuestas y condiciones de bienestar."
            )
        if p["estado"] == "No disponible":
            raise Problem("La mascota no está disponible.")
    if action == "Autorizar":
        if s["estado"] != "Pendiente":
            raise Problem("Solo se autoriza una solicitud pendiente.")
        if ctx.db.one(
            "SELECT id FROM adopciones_solicitud WHERE mascota_id=%s AND estado='Autorizada' AND id<>%s LIMIT 1",
            (p["id"], s["id"]),
        ):
            raise Problem("Otra solicitud ya está autorizada para esta mascota.")
        s["estado"] = "Autorizada"
        p["estado"] = "En proceso"
    elif action == "Entregar":
        if s["estado"] != "Autorizada" or p["estado"] != "En proceso":
            raise Problem("Primero autoriza y revisa la solicitud.")
        insert(
            ctx.db,
            "adopciones_entrega",
            dict(
                mascota_id=p["id"],
                solicitud_id=s["id"],
                responsable_id=ctx.session["user_id"],
                notas=notes,
                fecha=datetime.now(UTC).replace(tzinfo=None),
            ),
        )
        s["estado"] = "Entregada"
        p["estado"] = "Adoptada"
    else:
        if s["estado"] not in ("Pendiente", "Autorizada"):
            raise Problem("La solicitud ya fue revisada.")
        if s["estado"] == "Autorizada":
            p["estado"] = "Disponible"
        s["estado"] = "Rechazada"
    update(ctx.db, "adopciones_solicitud", {"estado": s["estado"]}, s["id"])
    update(
        ctx.db,
        "adopciones_mascotaadopcion",
        {"estado": p["estado"], "actualizada": datetime.now(UTC).replace(tzinfo=None)},
        p["id"],
    )
    insert(
        ctx.db,
        "adopciones_revision",
        dict(
            solicitud_id=s["id"],
            responsable_id=ctx.session["user_id"],
            accion=action,
            notas=notes,
            bienestar_verificado=verified,
            fecha=datetime.now(UTC).replace(tzinfo=None),
        ),
    )
    return {
        "status": "ok",
        "message": "Revisión registrada. "
        + (
            "Entrega confirmada."
            if action == "Entregar"
            else "La mascota todavía no se ha entregado."
        ),
        "estado": s["estado"],
    }


def clone_questionnaire(ctx):
    d = ctx.data
    found(
        ctx.db.one(
            "SELECT id FROM adopciones_cuestionario WHERE id=%s FOR UPDATE",
            (integer(d.get("cuestionario"), "cuestionario", 1),),
        )
    )
    q = questionnaire(ctx, int(d["cuestionario"]))
    weights = d.get("pesos", {})
    if set(weights) != {str(c["id"]) for c in q["criterios"]}:
        raise Problem("Indica un peso por criterio.")
    weights = {k: integer(v, "peso", 1, 100) for k, v in weights.items()}
    if sum(weights.values()) != 100:
        raise Problem("Los pesos deben sumar exactamente 100.")
    pk = insert(
        ctx.db,
        "adopciones_cuestionario",
        dict(
            nombre="VetCare · Versión "
            + datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds"),
            activa=False,
            creada=datetime.now(UTC).replace(tzinfo=None),
        ),
    )
    for index, c in enumerate(q["criterios"]):
        cid = insert(
            ctx.db,
            "adopciones_criterio",
            dict(
                cuestionario_id=pk,
                nombre=c["nombre"],
                peso=weights[str(c["id"])],
                recomendacion=c["recomendacion"],
                orden=index,
            ),
        )
        for pindex, p in enumerate(c["preguntas"]):
            pid = insert(
                ctx.db,
                "adopciones_pregunta",
                dict(criterio_id=cid, texto=p["texto"], orden=pindex),
            )
            ctx.db.many(
                "INSERT INTO adopciones_opcion(pregunta_id,texto,valor,alerta,orden) VALUES (%s,%s,%s,%s,%s)",
                [
                    (pid, o["texto"], o["valor"], o["alerta"], i)
                    for i, o in enumerate(p["opciones"])
                ],
            )
    if d.get("publicar", True):
        ctx.db.execute("UPDATE adopciones_cuestionario SET activa=0 WHERE activa=1")
        ctx.db.execute("UPDATE adopciones_cuestionario SET activa=1 WHERE id=%s", (pk,))
    return {
        "status": "ok",
        "message": "Nueva versión creada; las respuestas anteriores se conservan.",
        "id": pk,
    }


def edit_draft(ctx, qid):
    """Reemplaza la edición dependiente del Admin por una API JSON con control de versión."""
    q = found(
        ctx.db.one(
            "SELECT * FROM adopciones_cuestionario WHERE id=%s FOR UPDATE", (qid,)
        )
    )
    if q["activa"] or ctx.db.one(
        "SELECT id FROM adopciones_solicitud WHERE cuestionario_id=%s LIMIT 1", (qid,)
    ):
        raise Problem("Una versión publicada o utilizada es inmutable.")
    data = ctx.data
    question = integer(data.get("pregunta_id"), "pregunta", 1)
    found(
        ctx.db.one(
            "SELECT p.id FROM adopciones_pregunta p JOIN adopciones_criterio c ON c.id=p.criterio_id WHERE p.id=%s AND c.cuestionario_id=%s",
            (question, qid),
        )
    )
    update(
        ctx.db, "adopciones_pregunta", {"texto": required(data, "texto", 300)}, question
    )
    options = data.get("opciones")
    if not isinstance(options, list) or not options:
        raise Problem("Incluye opciones de respuesta.")
    ids = {
        r["id"]
        for r in ctx.db.all(
            "SELECT id FROM adopciones_opcion WHERE pregunta_id=%s", (question,)
        )
    }
    if {integer(o.get("id"), "opción", 1) for o in options} != ids:
        raise Problem("Conserva los identificadores de las opciones de este borrador.")
    for option in options:
        update(
            ctx.db,
            "adopciones_opcion",
            dict(
                texto=required(option, "texto", 300),
                valor=integer(option.get("valor"), "valor", 0, 100),
                alerta=required(option, "alerta", 200, True),
            ),
            int(option["id"]),
        )
    return {"status": "ok", "message": "Borrador actualizado."}


def publish(ctx, qid):
    q = found(
        ctx.db.one(
            "SELECT * FROM adopciones_cuestionario WHERE id=%s FOR UPDATE", (qid,)
        )
    )
    if q["activa"] or ctx.db.one(
        "SELECT id FROM adopciones_solicitud WHERE cuestionario_id=%s LIMIT 1", (qid,)
    ):
        raise Problem("Selecciona un borrador sin uso.")
    q = questionnaire(ctx, qid)
    if sum(c["peso"] for c in q["criterios"]) != 100 or not q["criterios"]:
        raise Problem("La versión debe sumar 100 puntos y tener preguntas y opciones.")
    ctx.db.execute("UPDATE adopciones_cuestionario SET activa=0 WHERE activa=1")
    ctx.db.execute("UPDATE adopciones_cuestionario SET activa=1 WHERE id=%s", (qid,))
    return {"status": "ok", "message": "Versión publicada."}
