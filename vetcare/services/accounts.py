# Administra las cuentas del equipo y revoca sesiones cuando cambian sus permisos.
from datetime import UTC, datetime

from ..db import insert, update
from ..security import admin, hasher
from ..validation import Problem, email, found, required


# Exige superusuario para administrar cuentas.
def authorize(ctx):
    if not admin(ctx)["is_superuser"]:
        raise Problem("Solo un superadministrador puede gestionar cuentas.", 403)


# Lista identidades y permisos sin devolver hashes ni contraseñas.
def list_users(ctx):
    authorize(ctx)
    return {
        "status": "ok",
        "usuarios": ctx.db.all(
            "SELECT id,username,first_name,last_name,email,is_active,is_staff,is_superuser FROM auth_user ORDER BY username"
        ),
    }


# Crea/actualiza cuentas, protege permisos propios y revoca sesiones al cambiar una contraseña.
def save(ctx, user_id=None):
    authorize(ctx)
    d = ctx.data
    values = dict(
        username=required(d, "username", 150),
        first_name=required(d, "first_name", 150, True),
        last_name=required(d, "last_name", 150, True),
        email=email(d.get("email"), True),
        is_active=d.get("is_active", True) is True,
        is_staff=d.get("is_staff", True) is True,
        is_superuser=d.get("is_superuser", False) is True,
    )
    password = d.get("password")
    if password:
        if not isinstance(password, str) or not 12 <= len(password) <= 1024:
            raise Problem("La contraseña nueva debe tener al menos 12 caracteres.")
        values["password"] = hasher.hash(password)
    if user_id:
        found(ctx.db.one("SELECT id FROM auth_user WHERE id=%s FOR UPDATE", (user_id,)))
        if user_id == ctx.session["user_id"] and not (
            values["is_active"] and values["is_staff"] and values["is_superuser"]
        ):
            raise Problem("No puedes quitar tus propios permisos administrativos.")
        update(ctx.db, "auth_user", values, user_id)
        if password:
            ctx.db.execute("DELETE FROM vc_session WHERE user_id=%s", (user_id,))
    else:
        if not password:
            raise Problem("Indica una contraseña para la cuenta nueva.")
        user_id = insert(
            ctx.db,
            "auth_user",
            {
                **values,
                "date_joined": datetime.now(UTC).replace(tzinfo=None),
                "last_login": None,
            },
        )
    return {"status": "ok", "message": "Cuenta guardada.", "id": user_id}
