"""Configuración local privada. No imprime contraseñas ni sobrescribe un .env existente."""

import getpass
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import set_key

from vetcare.config import ROOT

path = ROOT / ".env"
if path.exists():
    print(".env ya existe. Se conserva su configuración privada.")
    raise SystemExit(0)
values = {}
for key, label in [
    ("MYSQLHOST", "Host público de Railway (Connect)"),
    ("MYSQLPORT", "Puerto público"),
    ("MYSQLDATABASE", "Base de datos"),
    ("MYSQLUSER", "Usuario MySQL"),
]:
    values[key] = input(label + ": ").strip()
    if not values[key]:
        raise SystemExit("No se guardó: falta " + key)
values["MYSQLPASSWORD"] = getpass.getpass(
    "Contraseña completa de MySQL (no se mostrará): "
)
if not values["MYSQLPASSWORD"]:
    raise SystemExit("No se guardó: falta MYSQLPASSWORD.")
if not values["MYSQLPORT"].isdigit():
    raise SystemExit("El puerto debe ser numérico.")
path.write_text((ROOT / ".env.example").read_text(encoding="utf-8"), encoding="utf-8")
for key, value in {**values, "VETCARE_SECRET_KEY": secrets.token_urlsafe(48)}.items():
    set_key(path, key, value)
print("Archivo .env privado creado. No se guarda en Git ni en el paquete compartido.")
