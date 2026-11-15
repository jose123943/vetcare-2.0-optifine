from decimal import Decimal

from ..db import insert, update
from ..http import page
from ..validation import Problem, choice, found, integer, money, required
from .clinic import APPOINTMENTS, NOW, appointment

INVOICES = """SELECT f.*,CONCAT(c.nombre,' ',c.apellido) AS cliente,c.nombre,c.apellido,c.documento,c.email,c.telefono,
 a.fecha AS cita_fecha,a.motivo AS cita_motivo,m.nombre AS mascota_nombre,m.especie,m.raza
 FROM factura f JOIN cliente c ON c.id_cliente=f.cliente_id JOIN cita a ON a.id_cita=f.cita_id JOIN mascota m ON m.id_mascota=a.mascota_id"""


def summary(ctx):
    r = ctx.db.one("""SELECT COUNT(*) AS total_facturas,COALESCE(SUM(estado_pago='Pagada'),0) AS facturas_pagadas,
       COALESCE(SUM(estado_pago='Pendiente'),0) AS facturas_pendientes,
       COALESCE(SUM(CASE WHEN estado_pago='Pagada' THEN monto_total ELSE 0 END),0) AS total_ingresos,
       COALESCE(SUM(CASE WHEN estado_pago='Pendiente' THEN monto_total ELSE 0 END),0) AS total_pendiente FROM factura""")
    return {"status": "ok", "resumen": r}


def list_invoices(ctx):
    state = ctx.request.args.get("estado")
    sql = INVOICES
    params = ()
    if state in ("Pagada", "Pendiente", "Cancelada"):
        sql += " WHERE f.estado_pago=%s"
        params = (state,)
    sql += " ORDER BY f.fecha_emision DESC,f.id_factura DESC"

    def serialize(f):
        return dict(
            id=f["id_factura"],
            fecha=f["fecha_emision"],
            cliente=f["cliente"],
            monto=str(f["monto_total"]),
            estado=f["estado_pago"],
            cita_motivo=f["cita_motivo"],
            pdf_url=f"/inicio/api/facturas/{f['id_factura']}/pdf/",
        )

    return page(sql, params, ctx, "facturas", serialize)


def get_invoice(ctx, invoice_id):
    f = found(ctx.db.one(INVOICES + " WHERE f.id_factura=%s", (invoice_id,)))
    f["servicios"] = ctx.db.all(
        "SELECT servicio,cantidad,precio_unitario,cantidad*precio_unitario AS total FROM factura_detallefactura WHERE factura_id=%s ORDER BY id",
        (invoice_id,),
    )
    return f


def detail(ctx, invoice_id):
    f = get_invoice(ctx, invoice_id)
    return {
        "status": "ok",
        "detalle": dict(
            id=f["id_factura"],
            fecha_emision=f["fecha_emision"],
            monto_total=str(f["monto_total"]),
            estado_pago=f["estado_pago"],
            cliente_nombre=f["cliente"],
            cliente_email=f["email"],
            cliente_telefono=f["telefono"],
            mascota_nombre=f["mascota_nombre"],
            descuento=str(f["descuento"]),
            impuesto=str(f["impuesto"]),
            servicios=f["servicios"],
            pdf_url=f"/inicio/api/facturas/{invoice_id}/pdf/",
        ),
    }


def save(ctx):
    d = ctx.data
    cid = integer(d.get("cita_id"), "cita", 1)
    owner = integer(d.get("cliente_id"), "cliente", 1)
    c = found(
        ctx.db.one(
            "SELECT m.cliente_id FROM cita a JOIN mascota m ON m.id_mascota=a.mascota_id WHERE a.id_cita=%s",
            (cid,),
        )
    )
    if c["cliente_id"] != owner:
        raise Problem("La cita no pertenece al cliente seleccionado.")
    rows = d.get("servicios")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise Problem("Agrega al menos un servicio real.")
    prepared = [
        dict(
            servicio=required(r, "servicio", 200),
            cantidad=integer(r.get("cantidad"), "cantidad", 1, 10000),
            precio_unitario=money(r.get("precio_unitario")),
        )
        for r in rows
    ]
    subtotal = sum((r["cantidad"] * r["precio_unitario"] for r in prepared), Decimal(0))
    discount = money(d.get("descuento", 0))
    tax = money(d.get("impuesto", 0))
    if discount > subtotal:
        raise Problem("El descuento supera el subtotal.")
    total = money(subtotal - discount + tax)
    if total <= 0:
        raise Problem("La factura debe tener un total mayor que cero.")
    pk = insert(
        ctx.db,
        "factura",
        dict(
            fecha_emision=NOW().date(),
            monto_total=total,
            estado_pago=choice(
                d.get("estado_pago", "Pendiente"), ("Pagada", "Pendiente", "Cancelada")
            ),
            cita_id=cid,
            cliente_id=owner,
            administrador_id=ctx.session["user_id"],
            descuento=discount,
            impuesto=tax,
            metodo_pago=required(d, "metodo_pago", 50, True),
        ),
    )
    ctx.db.many(
        "INSERT INTO factura_detallefactura(factura_id,servicio,cantidad,precio_unitario) VALUES (%s,%s,%s,%s)",
        [(pk, r["servicio"], r["cantidad"], r["precio_unitario"]) for r in prepared],
    )
    return {
        "status": "ok",
        "message": "Factura registrada.",
        "id": pk,
        "monto_total": str(total),
        "pdf_url": f"/inicio/api/facturas/{pk}/pdf/",
    }


def change_state(ctx):
    pk = integer(ctx.data.get("factura_id"), "factura", 1)
    found(
        ctx.db.one(
            "SELECT id_factura FROM factura WHERE id_factura=%s FOR UPDATE", (pk,)
        )
    )
    update(
        ctx.db,
        "factura",
        {
            "estado_pago": choice(
                ctx.data.get("estado_pago"), ("Pendiente", "Pagada", "Cancelada")
            )
        },
        pk,
        "id_factura",
    )
    return {"status": "ok", "message": "Estado de factura actualizado."}


def options(ctx):
    rows = ctx.db.all(
        APPOINTMENTS
        + " WHERE a.estado<>'Cancelada' ORDER BY a.fecha DESC,a.id_cita DESC"
    )
    return {
        "status": "ok",
        "citas": [{**appointment(r), "cliente_nombre": r["cliente"]} for r in rows],
    }
