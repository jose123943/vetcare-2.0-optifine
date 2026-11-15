"""Consulta protegida de antecedentes anteriores al catálogo público actual."""

from ..http import page
from ..validation import found


def adoptions(ctx):
    return page(
        "SELECT a.id,a.estado,a.fecha_registro,a.fecha_adopcion,a.motivo,a.observaciones,"
        "a.observaciones_adopcion,m.nombre AS mascota,c.nombre,c.apellido "
        "FROM adopcion a JOIN mascota m ON m.id_mascota=a.mascota_id "
        "JOIN cliente c ON c.id_cliente=a.cliente_origen_id ORDER BY a.id DESC",
        (),
        ctx,
        "adopciones",
        always=True,
    )


def detail(ctx, adoption_id):
    row = found(ctx.db.one("SELECT * FROM adopcion WHERE id=%s", (adoption_id,)))
    evaluations = ctx.db.all(
        "SELECT id,fecha,puntaje,aprobada,version,respuestas,desglose,cliente_id "
        "FROM evaluacion_adopcion WHERE adopcion_id=%s ORDER BY id",
        (adoption_id,),
    )
    # No recalcular ni trasladar al nuevo umbral resultados históricos de otro esquema.
    return {"status": "ok", "adopcion": row, "evaluaciones": evaluations}
