# Controla el acceso, las contraseñas, las sesiones y los permisos de cada usuario.
import base64
import hashlib
import json
import secrets
import zlib
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from itsdangerous import BadSignature, Signer
from passlib.hash import django_argon2, django_pbkdf2_sha1, django_pbkdf2_sha256

from .db import insert
from .validation import Problem

# Verifica contraseñas mediante una biblioteca especializada, sin guardarlas en texto legible.
hasher = PasswordHasher()
# Mantiene una comprobación comparable cuando el usuario no existe para no revelar cuentas por tiempos.
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(24))


# Calcula SHA-256 para tokens, claves de control y propietarios de sesiones.
def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


# Verifica hashes Argon2 y formatos heredados sin almacenar contraseñas en claro.
def verify_password(password, stored):
    if not isinstance(password, str) or not password or len(password) > 1024:
        return False
    try:
        if stored.startswith("$argon2"):
            return hasher.verify(stored, password)
        for prefix, handler in [
            ("pbkdf2_sha256$", django_pbkdf2_sha256),
            ("pbkdf2_sha1$", django_pbkdf2_sha1),
            ("argon2$", django_argon2),
        ]:
            if stored.startswith(prefix):
                return handler.verify(password, stored)
        return False
    except (ValueError, TypeError, VerificationError, InvalidHashError):
        return False


# Recupera una sesión vigente y, para usuarios, comprueba la identidad de ejecución; si falta crea una anónima.
def ensure_session(ctx):
    if ctx.session is not None:
        return ctx.session
    token = ctx.request.cookies.get("vetcare_sid", "")
    row = (
        ctx.db.one(
            "SELECT s.*,u.id AS uid,u.username,u.first_name,u.last_name,u.is_active,u.is_staff,u.is_superuser "
            "FROM vc_session s LEFT JOIN auth_user u ON u.id=s.user_id "
            "LEFT JOIN vc_session_scope scope ON scope.token_hash=s.token_hash "
            "WHERE s.token_hash=%s AND s.expires>UTC_TIMESTAMP(6) "
            "AND (s.user_id IS NULL OR scope.run_id=%s)",
            (digest(token), ctx.app.config.session_run_id),
        )
        if token
        else None
    )
    if row and row.get("user_id") and not row["is_active"]:
        ctx.db.execute(
            "DELETE FROM vc_session WHERE token_hash=%s", (row["token_hash"],)
        )
        row = None
    if not row:
        row = new_session(ctx, owner_hash=legacy_owner(ctx))
    ctx.session = row
    return row


# Reconoce de forma verificada al propietario de una solicitud procedente de una sesión antigua.
def legacy_owner(ctx):
    """Transición de solicitudes privadas antiguas con firma verificada por ItsDangerous."""
    token = ctx.request.cookies.get("sessionid", "")
    if not token or len(token) > 40:
        return None
    legacy = ctx.db.one(
        "SELECT session_data FROM django_session WHERE session_key=%s AND expire_date>UTC_TIMESTAMP(6)",
        (token,),
    )
    if not legacy:
        return None
    owner = decode_legacy(legacy["session_data"], ctx.app.config.secret).get(
        "adoption_owner"
    )
    return digest(owner) if isinstance(owner, str) and 16 <= len(owner) <= 200 else None


# Verifica la firma de una sesión heredada antes de interpretar su JSON limitado.
def decode_legacy(value, secret):
    try:
        signer = Signer(
            secret,
            salt="django.contrib.sessions.SessionStore",
            key_derivation="django-concat",
            digest_method=hashlib.sha256,
            sep=":",
        )
        unsigned = signer.unsign(value).decode().rsplit(":", 1)[0]
        compressed = unsigned.startswith(".")
        payload = unsigned[1:] if compressed else unsigned
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        if compressed:
            raw = zlib.decompressobj().decompress(raw, 65536)
        if len(raw) >= 65536:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (BadSignature, ValueError, TypeError, zlib.error):
        return {}


# Genera tokens aleatorios, guarda sus hashes y vincula el acceso autenticado a la ejecución actual.
def new_session(ctx, user_id=None, owner_hash=None):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row = dict(
        token_hash=digest(token),
        csrf_hash=digest(csrf),
        owner_hash=owner_hash or digest(secrets.token_urlsafe(32)),
        user_id=user_id,
        created=now,
        expires=datetime(9999, 12, 31, 23, 59, 59)
        if user_id is not None
        else now + timedelta(hours=ctx.app.config.session_hours),
    )
    insert(ctx.db, "vc_session", row)
    if user_id is not None:
        insert(
            ctx.db,
            "vc_session_scope",
            dict(token_hash=row["token_hash"], run_id=ctx.app.config.session_run_id),
        )
    ctx.cookies = [("vetcare_sid", token, True), ("csrftoken", csrf, False)]
    return row


# Obtiene únicamente identidad y permisos de una cuenta activa.
def user(ctx):
    s = ensure_session(ctx)
    return (
        {
            k: s.get(k)
            for k in [
                "uid",
                "username",
                "first_name",
                "last_name",
                "is_staff",
                "is_superuser",
            ]
        }
        if s.get("uid") and s.get("is_active")
        else None
    )


# Exige usuario activo con permiso staff antes de entrar a una API administrativa.
def admin(ctx):
    u = user(ctx)
    if not u:
        raise Problem("Inicia sesión para continuar.", 401)
    if not u["is_staff"]:
        raise Problem("Se requiere acceso administrativo.", 403)
    return u


# Comprueba el token de formulario y el origen de una escritura.
def csrf(ctx):
    s = ensure_session(ctx)
    candidate = ctx.request.headers.get("X-CSRFToken") or ctx.request.form.get(
        "csrf_token", ""
    )
    if not secrets.compare_digest(s["csrf_hash"], digest(candidate)):
        raise Problem(
            "La sesión del formulario venció. Recarga la página antes de volver a enviarlo.",
            403,
        )
    origin = ctx.request.headers.get("Origin")
    if origin and origin.rstrip("/") != ctx.request.host_url.rstrip("/"):
        raise Problem("Origen de solicitud no autorizado.", 403)


# Limita intentos, valida credenciales, actualiza el hash cuando corresponde y rota la sesión.
def login(ctx):
    csrf(ctx)
    data = ctx.data
    username = str(data.get("username", "")).strip()[:150]
    password = data.get("password", "")
    account_key = digest("account:" + username.casefold())
    ip_key = digest("ip:" + str(ctx.request.remote_addr))
    with ctx.db.atomic():
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for key, maximum in [(account_key, 6), (ip_key, 40)]:
            ctx.db.execute(
                "INSERT IGNORE INTO vc_login_bucket(bucket,attempts,window_start) VALUES (%s,0,%s)",
                (key, now),
            )
            row = ctx.db.one(
                "SELECT * FROM vc_login_bucket WHERE bucket=%s FOR UPDATE", (key,)
            )
            if row["blocked_until"] and row["blocked_until"] > now:
                raise Problem("Demasiados intentos. Espera 15 minutos.", 429)
            if now - row["window_start"] > timedelta(minutes=15):
                ctx.db.execute(
                    "UPDATE vc_login_bucket SET attempts=0,window_start=%s,blocked_until=NULL WHERE bucket=%s",
                    (now, key),
                )
                row["attempts"] = 0
            attempts = row["attempts"] + 1
            ctx.db.execute(
                "UPDATE vc_login_bucket SET attempts=%s,blocked_until=%s WHERE bucket=%s",
                (
                    attempts,
                    now + timedelta(minutes=15) if attempts >= maximum else None,
                    key,
                ),
            )
    account = ctx.db.one(
        "SELECT id,password,username,first_name,last_name,is_active,is_staff,is_superuser FROM auth_user WHERE username=%s",
        (username,),
    )
    valid = verify_password(password, account["password"] if account else DUMMY_HASH)
    if not valid or not account or not account["is_active"] or not account["is_staff"]:
        raise Problem("Usuario o contraseña incorrectos.", 401)
    with ctx.db.atomic():
        if not account["password"].startswith("$argon2") or hasher.check_needs_rehash(
            account["password"]
        ):
            ctx.db.execute(
                "UPDATE auth_user SET password=%s,last_login=UTC_TIMESTAMP(6) WHERE id=%s",
                (hasher.hash(password), account["id"]),
            )
        else:
            ctx.db.execute(
                "UPDATE auth_user SET last_login=UTC_TIMESTAMP(6) WHERE id=%s",
                (account["id"],),
            )
        ctx.db.execute("DELETE FROM vc_login_bucket WHERE bucket=%s", (account_key,))
        old = ensure_session(ctx)
        row = new_session(ctx, account["id"], old["owner_hash"])
        ctx.db.execute(
            "DELETE FROM vc_session WHERE token_hash=%s", (old["token_hash"],)
        )
        row.update(account)
        row["uid"] = account["id"]
        row.pop("password", None)
        ctx.session = row
    return {"status": "ok", "redirect": "/inicio/"}


# Revoca la sesión actual y ordena borrar sus cookies.
def logout(ctx):
    csrf(ctx)
    s = ensure_session(ctx)
    ctx.db.execute("DELETE FROM vc_session WHERE token_hash=%s", (s["token_hash"],))
    ctx.session = None
    ctx.clear_cookies = True
    return {"status": "ok", "redirect": "/"}
