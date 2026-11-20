# Construye una factura PDF a partir de los datos y los importes guardados.
import os
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..validation import Problem


# Formatea un importe como moneda COP para el documento.
def cop(value):
    return (
        "$ "
        + f"{Decimal(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        + " COP"
    )


# Genera el PDF con ReportLab, detalle real, totales y marca de gestión interna.
def build(f, root):
    lines = f["servicios"]
    total = f["monto_total"]
    if total <= 0:
        raise Problem("La factura no tiene un importe válido para el documento.")
    subtotal = (
        sum((r["cantidad"] * r["precio_unitario"] for r in lines), Decimal(0))
        if lines
        else total
    )
    if lines and subtotal - f["descuento"] + f["impuesto"] != total:
        raise Problem("El detalle no coincide con el total almacenado.")
    out = BytesIO()
    doc = SimpleDocTemplate(
        out,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=38,
        bottomMargin=55,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Brand",
            fontSize=27,
            leading=32,
            textColor=colors.HexColor("#127565"),
            spaceAfter=10,
        )
    )

    # Escapa texto y lo convierte en un párrafo del documento.
    def p(value, style="BodyText"):
        return Paragraph(escape(str(value)), styles[style])

    story = []
    logo = root / "frontend/assets/images/huella.png"
    if logo.exists():
        story.append(Image(str(logo), width=30, height=30, hAlign="LEFT"))
    story += [
        p("VetCare", "Brand"),
        p("Cuidamos su bienestar"),
        Spacer(1, 14),
        p(f"FACTURA DE GESTIÓN INTERNA · F{f['id_factura']:06d}", "Heading2"),
        p(f"Emisión: {f['fecha_emision']:%d/%m/%Y} · Estado: {f['estado_pago']}"),
    ]
    for key, label in [
        ("VETCARE_NIT", "NIT"),
        ("VETCARE_ADDRESS", "Dirección"),
        ("VETCARE_PHONE", "Teléfono"),
        ("VETCARE_EMAIL", "Correo"),
    ]:
        if os.getenv(key):
            story.append(p(label + ": " + os.environ[key]))
    story += [
        Spacer(1, 16),
        p("Cliente y paciente", "Heading2"),
        p(f["cliente"]),
        p(
            f"Documento: {f['documento'] or 'No registrado'} · Teléfono: {f['telefono']}"
        ),
        p(f"Correo: {f['email'] or 'No registrado'}"),
        p(f"Mascota: {f['mascota_nombre']} · {f['especie']} · {f['raza']}"),
        Spacer(1, 18),
    ]
    rows = [[p("Servicio"), p("Cant."), p("Precio unitario"), p("Total")]]
    if lines:
        rows += [
            [
                p(r["servicio"]),
                p(r["cantidad"]),
                p(cop(r["precio_unitario"])),
                p(cop(r["total"])),
            ]
            for r in lines
        ]
    else:
        rows.append(
            [
                p("Importe histórico registrado · " + f["cita_motivo"]),
                p("—"),
                p("Sin desglose"),
                p(cop(total)),
            ]
        )
    table = Table(rows, colWidths=[210, 35, 135, 152], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dff2ed")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e4e0")),
            ]
        )
    )
    story += [
        table,
        Spacer(1, 18),
        p("Subtotal: " + cop(subtotal)),
        p("Descuento: " + cop(f["descuento"])),
        p("Impuestos registrados: " + cop(f["impuesto"])),
        p("TOTAL: " + cop(total), "Heading2"),
        p("Método de pago: " + (f["metodo_pago"] or "No registrado")),
        Spacer(1, 20),
        p(
            "Documento de gestión interna. No constituye factura electrónica autorizada por la DIAN."
        ),
    ]

    # Dibuja pie de página y numeración en cada hoja.
    def footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#4c6961"))
        canvas.drawString(
            40, 28, "VetCare · Gracias por confiar en el cuidado de tu mascota"
        )
        canvas.drawRightString(572, 28, f"Página {document.page}")

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
