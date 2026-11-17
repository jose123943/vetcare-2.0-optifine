import hashlib
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pymysql
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.routing import Map, Rule
from werkzeug.utils import redirect, safe_join, send_file, send_from_directory

from . import security
from .config import Config
from .db import Database, insert, update
from .http import Context, response_json
from .services import accounts, adoptions, billing, clinic, history, mail, pdf
from .validation import Problem, found

logger = logging.getLogger("vetcare")


class Application:
    def __init__(self, config=None):
        self.config = config or Config.load()
        self.database = Database(self.config)
        self.routes = []
        self.handlers = {}
        self.register_routes()
        self.router = Map(self.routes, strict_slashes=False)
        self.wsgi = (
            ProxyFix(self.dispatch, x_for=1, x_proto=1)
            if self.config.production
            else self.dispatch
        )

    def __call__(self, environ, start_response):
        return self.wsgi(environ, start_response)

    def add(self, method, path, fn, admin=False, write=False):
        name = "route" + str(len(self.handlers))
        self.handlers[name] = (fn, admin, write)
        self.routes.append(Rule(path, endpoint=name, methods=[method]))

    def dispatch(self, environ, start_response):
        start = time.monotonic()
        ctx = Context(self, environ)
        try:
            hostname = ctx.request.host.split(":", 1)[0]
            if hostname not in self.config.hosts:
                raise Problem("Host no autorizado.", 400)
            if (
                self.config.production
                and ctx.request.scheme != "https"
                and not ctx.request.path.startswith("/health/")
            ):
                response = redirect(
                    ctx.request.url.replace("http://", "https://", 1), 308
                )
            else:
                endpoint, args = self.router.bind_to_environ(environ).match()
                fn, staff, write = self.handlers[endpoint]
                if staff:
                    security.admin(ctx)
                if ctx.request.method not in ("GET", "HEAD", "OPTIONS"):
                    security.csrf(ctx)
                result = self.mutate(ctx, fn, args) if write else fn(ctx, **args)
                response = (
                    result if hasattr(result, "status_code") else response_json(result)
                )
        except Problem as exc:
            response = response_json(
                {"status": "error", "message": exc.message}, exc.status
            )
        except HTTPException as exc:
            response = response_json(
                {
                    "status": "error",
                    "message": "Método no permitido."
                    if exc.code == 405
                    else "Recurso no disponible.",
                },
                exc.code,
            )
        except (ValueError, TypeError, KeyError):
            response = response_json(
                {
                    "status": "error",
                    "message": "Revisa los tipos de datos y los campos obligatorios del formulario.",
                },
                400,
            )
        except pymysql.IntegrityError:
            response = response_json(
                {
                    "status": "error",
                    "message": "Los datos únicos ya existen o tienen historial relacionado. Revisa el documento y las asociaciones.",
                },
                409,
            )
        except (pymysql.Error, TimeoutError) as exc:
            logger.error(
                "Base de datos temporalmente no disponible: %s", type(exc).__name__
            )
            response = response_json(
                {
                    "status": "error",
                    "message": "MySQL no está disponible temporalmente. Puedes reintentar con la misma clave de operación.",
                },
                503,
            )
        except Exception as exc:
            logger.error("Fallo interno: %s", type(exc).__name__)
            response = response_json(
                {
                    "status": "error",
                    "message": "No se pudo completar la operación. Conserva el formulario y vuelve a intentar.",
                },
                500,
            )
        finally:
            ctx.stack.close()
        ctx.finish(response)
        response.headers["Server-Timing"] = (
            f"app;dur={(time.monotonic() - start) * 1000:.1f}"
        )
        response.headers["X-VetCare-SQL-Queries"] = str(
            ctx._db.queries if ctx._db else 0
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        if not ctx.request.path.startswith(("/static/", "/adopciones/fotos/")):
            response.headers["Cache-Control"] = "no-store, private"
        if self.config.production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response(environ, start_response)

    def mutate(self, ctx, fn, args):
        key = ctx.request.headers.get("Idempotency-Key", "")
        if not key or len(key) > 100:
            raise Problem("Falta la clave de operación. Recarga el formulario.")
        file_hashes = {}
        for name, upload in ctx.request.files.items():
            digest = hashlib.sha256()
            while chunk := upload.stream.read(65536):
                digest.update(chunk)
            upload.stream.seek(0)
            file_hashes[name] = digest.hexdigest()
        fingerprint = hashlib.sha256(
            (
                ctx.request.path
                + ctx.request.method
                + json.dumps(ctx.data, sort_keys=True)
                + (json.dumps(file_hashes, sort_keys=True) if file_hashes else "")
            ).encode()
        ).hexdigest()
        inserted = False
        try:
            with ctx.db.atomic():
                op = insert(
                    ctx.db,
                    "pagInicio_operacion",
                    dict(
                        usuario_id=ctx.session["user_id"],
                        clave=key,
                        huella=fingerprint,
                        respuesta="{}",
                        codigo=200,
                        creada=datetime.now(UTC).replace(tzinfo=None),
                    ),
                )
                inserted = True
                result = fn(ctx, **args)
                update(
                    ctx.db,
                    "pagInicio_operacion",
                    dict(
                        respuesta=json.dumps(result, ensure_ascii=False, default=str),
                        codigo=200,
                    ),
                    op,
                )
                return result
        except pymysql.IntegrityError:
            if inserted:
                raise
            previous = ctx.db.one(
                "SELECT huella,respuesta FROM pagInicio_operacion WHERE usuario_id=%s AND clave=%s",
                (ctx.session["user_id"], key),
            )
            if not previous:
                raise
            if previous["huella"] != fingerprint:
                raise Problem("Esta clave ya fue utilizada con otros datos.", 409)
            return adoptions.load_json(previous["respuesta"])

    def asset(self, ctx, path):
        return send_from_directory(
            self.config.root / "frontend/assets", path, ctx.request.environ, max_age=0
        )

    def html(self, ctx, name):
        return send_from_directory(
            self.config.root / "frontend/pages",
            name + ".html",
            ctx.request.environ,
            max_age=0,
        )

    def dashboard_html(self, ctx):
        try:
            security.admin(ctx)
        except Problem as exc:
            if exc.status == 401:
                return redirect("/", 303)
            raise
        return self.html(ctx, "dashboard")

    def session(self, ctx):
        user = security.user(ctx)
        return {
            "status": "ok",
            "user": (
                {
                    **user,
                    "id": user["uid"],
                    "name": (
                        " ".join(filter(None, [user["first_name"], user["last_name"]]))
                        or user["username"]
                    ),
                }
                if user
                else None
            ),
        }

    def photo(self, ctx, pet_id):
        p = found(
            ctx.db.one(
                "SELECT fotografia FROM adopciones_mascotaadopcion WHERE id=%s",
                (pet_id,),
            )
        )
        name = p["fotografia"]
        if (
            not name
            or not name.startswith("adopciones/")
            or Path(name).suffix.lower() not in (".webp", ".png", ".jpg", ".jpeg")
        ):
            raise Problem("Imagen no disponible.", 404)
        path = safe_join(str(self.config.media), name)
        if not path or not Path(path).is_file():
            raise Problem("Imagen no disponible.", 404)
        response = send_file(path, ctx.request.environ, conditional=True, max_age=3600)
        return response

    def upload(self, ctx, pet_id):
        upload = ctx.request.files.get("fotografia")
        if not upload:
            raise Problem("Selecciona una fotografía.")
        raw = upload.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            raise Problem("La fotografía debe tener hasta 5 MB.")
        try:
            image = Image.open(BytesIO(raw))
            if image.width * image.height > 20000000:
                raise ValueError()
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((1200, 1200))
            output = BytesIO()
            image.save(output, "WEBP", quality=82)
        except (
            ValueError,
            OSError,
            UnidentifiedImageError,
            Image.DecompressionBombError,
        ):
            raise Problem("La imagen no es válida o supera las dimensiones permitidas.")
        found(
            ctx.db.one(
                "SELECT id FROM adopciones_mascotaadopcion WHERE id=%s FOR UPDATE",
                (pet_id,),
            )
        )
        name = "adopciones/" + uuid.uuid4().hex + ".webp"
        target = self.config.media / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(output.getvalue())
        update(
            ctx.db,
            "adopciones_mascotaadopcion",
            {"fotografia": name, "actualizada": datetime.now(UTC).replace(tzinfo=None)},
            pet_id,
        )
        return {
            "status": "ok",
            "message": "Fotografía optimizada y guardada.",
            "fotografia": f"/adopciones/fotos/{pet_id}/?v={uuid.uuid4().hex}",
        }

    def invoice_pdf(self, ctx, invoice_id):
        body = pdf.build(billing.get_invoice(ctx, invoice_id), self.config.root)
        return send_file(
            BytesIO(body),
            ctx.request.environ,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"VetCare-F{invoice_id:06d}.pdf",
        )

    def own_html(self, ctx, code):
        adoptions.own_result(ctx, code)
        return self.html(ctx, "result")

    def ready(self, ctx):
        ctx.db.one("SELECT 1 AS ok")
        return {"status": "ok"}

    def login_html(self, ctx):
        account = security.user(ctx)
        if account and account["is_staff"]:
            return redirect("/inicio/", 303)
        return self.html(ctx, "login")

    def register_routes(self):
        add = self.add
        add("GET", "/", self.login_html)
        add("POST", "/", security.login)
        add("POST", "/api/auth/login", security.login)
        add("GET", "/inicio/", self.dashboard_html)
        add(
            "GET",
            "/admin/",
            lambda ctx: redirect("/inicio/#configuracion", 303),
            admin=True,
        )
        add(
            "POST", "/salir/", lambda ctx: (security.logout(ctx), redirect("/", 303))[1]
        )
        add("POST", "/api/auth/logout", security.logout)
        add("GET", "/api/session", self.session)
        add("GET", "/static/<path:path>", self.asset)
        add(
            "GET",
            "/health/live/",
            lambda ctx: {"status": "ok", "service": "VetCare Python WSGI"},
        )
        add("GET", "/health/ready/", self.ready)
        add("GET", "/adopciones/", lambda ctx: self.html(ctx, "catalog"))
        add("GET", "/adopciones/solicitud/<uuid:code>/", self.own_html)
        add("GET", "/adopciones/fotos/<int:pet_id>/", self.photo)
        read = [
            ("dashboard/", clinic.dashboard),
            ("mascotas/", clinic.pets),
            ("mascotas-selector/", clinic.pets),
            ("clientes/", clinic.customers),
            ("clientes/<int:customer_id>/mascotas/", clinic.pets),
            ("detalle-mascota/<int:pet_id>/", clinic.pet_detail),
            ("cargar-datos-agenda/", clinic.vets),
            ("citas/", clinic.appointment_list),
            (
                "citas/pendientes/",
                lambda ctx: clinic.appointment_list(ctx, pending=True),
            ),
            ("citas/<int:appointment_id>/", clinic.appointment_detail),
            ("citas-mascota/<int:pet_id>/", clinic.appointment_list),
            ("vacunas-mascota/<int:pet_id>/", clinic.vaccines),
            ("tratamientos-mascota/<int:pet_id>/", clinic.treatments),
            ("resumen-facturas/", billing.summary),
            ("listar-facturas/", billing.list_invoices),
            ("detalle-factura/<int:invoice_id>/", billing.detail),
            ("datos-factura/", billing.options),
            ("facturas/<int:invoice_id>/pdf/", self.invoice_pdf),
            ("notificaciones/", mail.list_messages),
        ]
        writes = [
            ("POST", "registrar/cliente-mascota/", clinic.register_family),
            ("POST", "clientes/<int:customer_id>/agregar-mascota/", clinic.add_pet),
            ("POST", "editar-registro/", clinic.edit_record),
            ("DELETE", "eliminar-registro/<int:pet_id>/", clinic.delete_pet),
            ("POST", "veterinarios/guardar/", clinic.save_vet),
            ("DELETE", "veterinarios/<int:vet_id>/", clinic.delete_vet),
            ("POST", "registrar/cita/", clinic.save_appointment),
            ("POST", "citas/<int:appointment_id>/editar/", clinic.save_appointment),
            ("POST", "registrar-vacuna/", clinic.save_vaccine),
            ("POST", "registrar-tratamiento/", clinic.save_treatment),
            ("POST", "registrar-factura/", billing.save),
            ("POST", "actualizar-estado-factura/", billing.change_state),
            ("POST", "notificaciones/<int:message_id>/reintentar/", mail.retry),
        ]
        for path, fn in read:
            add("GET", "/inicio/api/" + path, fn, admin=True)
        for method, path, fn in writes:
            add(method, "/inicio/api/" + path, fn, admin=True, write=True)
        for method, path, fn in [
            ("GET", "clientes", clinic.customers),
            ("GET", "clientes/<int:customer_id>", clinic.customers),
            ("GET", "clientes/<int:customer_id>/mascotas", clinic.pets),
            ("GET", "mascotas", clinic.pets),
            ("GET", "mascotas/<int:pet_id>", clinic.pet_detail),
            ("GET", "veterinarios", clinic.vets),
            ("GET", "citas", clinic.appointment_list),
            (
                "GET",
                "citas/pendientes",
                lambda ctx: clinic.appointment_list(ctx, pending=True),
            ),
            ("GET", "citas/<int:appointment_id>", clinic.appointment_detail),
            ("GET", "facturas", billing.list_invoices),
            ("GET", "facturas/<int:invoice_id>", billing.detail),
            ("GET", "facturas/<int:invoice_id>/pdf", self.invoice_pdf),
        ]:
            add(method, "/api/" + path, fn, admin=True)
        for method, path, fn in [
            ("POST", "clientes", clinic.register_family),
            ("PUT", "clientes/<int:customer_id>", clinic.edit_customer),
            ("DELETE", "clientes/<int:customer_id>", clinic.delete_customer),
            ("POST", "clientes/<int:customer_id>/mascotas", clinic.add_pet),
            ("DELETE", "mascotas/<int:pet_id>", clinic.delete_pet),
            ("POST", "veterinarios", clinic.save_vet),
            ("PUT", "veterinarios", clinic.save_vet),
            ("POST", "citas", clinic.save_appointment),
            ("PUT", "citas/<int:appointment_id>", clinic.save_appointment),
            ("POST", "vacunas", clinic.save_vaccine),
            ("POST", "tratamientos", clinic.save_treatment),
            ("POST", "facturas", billing.save),
        ]:
            add(method, "/api/" + path, fn, admin=True, write=True)
        for prefix in ["/adopciones/api/", "/api/adopciones/"]:
            add("GET", prefix + "mascotas/<int:pet_id>/", adoptions.public_pet)
            add("GET", prefix + "catalogo/", adoptions.catalog)
            add("GET", prefix + "cuestionario/", adoptions.schema)
            add("POST", prefix + "mascotas/<int:pet_id>/solicitar/", adoptions.apply)
            add("GET", prefix + "solicitud/<uuid:code>/", adoptions.own_result)
            add(
                "GET",
                prefix + "admin/mascotas/",
                lambda ctx: adoptions.catalog(ctx, True),
                admin=True,
            )
            add(
                "GET", prefix + "admin/solicitudes/", adoptions.applications, admin=True
            )
            add(
                "GET",
                prefix + "admin/solicitudes/<int:application_id>/",
                adoptions.detail,
                admin=True,
            )
            add(
                "POST",
                prefix + "admin/mascotas/guardar/",
                adoptions.save_pet,
                admin=True,
                write=True,
            )
            add(
                "POST",
                prefix + "admin/mascotas/<int:pet_id>/foto/",
                self.upload,
                admin=True,
                write=True,
            )
            add(
                "POST",
                prefix + "admin/solicitudes/<int:application_id>/revisar/",
                adoptions.review,
                admin=True,
                write=True,
            )
            add(
                "POST",
                prefix + "admin/cuestionario/pesos/",
                adoptions.clone_questionnaire,
                admin=True,
                write=True,
            )
            add(
                "GET",
                prefix + "admin/cuestionarios/",
                lambda ctx: {
                    "status": "ok",
                    "cuestionarios": ctx.db.all(
                        "SELECT id,nombre,activa FROM adopciones_cuestionario ORDER BY id DESC"
                    ),
                },
                admin=True,
            )
            add(
                "GET",
                prefix + "admin/cuestionarios/<int:qid>/",
                lambda ctx, qid: {
                    "status": "ok",
                    "cuestionario": adoptions.questionnaire(ctx, qid),
                },
                admin=True,
            )
            add(
                "PUT",
                prefix + "admin/cuestionarios/<int:qid>/",
                adoptions.edit_draft,
                admin=True,
                write=True,
            )
            add(
                "POST",
                prefix + "admin/cuestionarios/<int:qid>/publicar/",
                adoptions.publish,
                admin=True,
                write=True,
            )
        add("GET", "/api/admin/usuarios", accounts.list_users, admin=True)
        add("GET", "/api/admin/historico/adopciones", history.adoptions, admin=True)
        add(
            "GET",
            "/api/admin/historico/adopciones/<int:adoption_id>",
            history.detail,
            admin=True,
        )
        add("POST", "/api/admin/usuarios", accounts.save, admin=True, write=True)
        add(
            "PUT",
            "/api/admin/usuarios/<int:user_id>",
            accounts.save,
            admin=True,
            write=True,
        )


def create_app(config=None):
    return Application(config)
