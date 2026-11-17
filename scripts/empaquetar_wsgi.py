"""Distribuye código verificando exclusiones y secretos; nunca publica un servicio."""

import json
import os
import zipfile
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
DIRECTORIES = {"frontend", "vetcare", "sql", "scripts", "tests", "docs", ".github"}
FILES = {
    "run.py",
    "requirements.txt",
    "requirements-dev.txt",
    "README.md",
    "vetcare-funciones.md",
    ".env.example",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    ".dockerignore",
    "Dockerfile",
    "Procfile",
    "gunicorn.conf.py",
    "railway.json",
    "railway.worker.json",
    "iniciar.ps1",
    "instalar.ps1",
}


# Obtiene sólo valores a detectar; nunca se incluyen ni se imprimen.
def private_patterns(root=ROOT):
    private = dotenv_values(root / ".env", interpolate=False)
    return [
        value.encode()
        for key, value in private.items()
        if value
        and len(value) >= 12
        and any(word in key for word in ("PASSWORD", "SECRET", "TOKEN"))
    ]


# Copia únicamente fuente permitido y valida el ZIP antes de darlo por creado.
def create_archive(target, web=False, root=ROOT):
    patterns = private_patterns(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for parent, dirs, names in os.walk(root):
            relative = Path(parent).relative_to(root)
            dirs[:] = [
                name
                for name in dirs
                if name not in {"__pycache__", "node_modules", ".ruff_cache"}
                and (relative.parts or name in DIRECTORIES)
            ]
            for name in names:
                path = Path(parent) / name
                rel = path.relative_to(root)
                if len(rel.parts) == 1 and name not in FILES:
                    continue
                if name.startswith(".env") and name != ".env.example":
                    continue
                if path.suffix.lower() in {".pyc", ".dump", ".gz", ".zip", ".log"}:
                    continue
                if path.suffix.lower() == ".sql" and rel.parts[0] != "sql":
                    continue
                if (
                    web
                    and rel.parts[:2] == ("docs", "evidencias")
                    and name != "README.md"
                ):
                    continue
                data = path.read_bytes()
                if any(secret in data for secret in patterns):
                    raise RuntimeError("Secreto detectado; no publicar: " + str(rel))
                archive.writestr(rel.as_posix(), data)
    with zipfile.ZipFile(target) as archive:
        names = set(archive.namelist())
        if archive.testzip() is not None or not {
            "Dockerfile",
            "sql/001_wsgi.sql",
            "frontend/assets/js/bootstrap.js",
        }.issubset(names):
            raise RuntimeError("Paquete incompleto o dañado.")
        if any(
            name == ".env"
            or name.startswith((".venv/", ".venv-wsgi/", "media/", "build/"))
            for name in names
        ):
            raise RuntimeError("El paquete incluye un directorio privado o generado.")
    return {
        "archivo": target.name,
        "archivos": len(names),
        "bytes": target.stat().st_size,
        "sin_secretos": True,
    }


# El paquete web omite evidencias pesadas; el completo conserva pruebas e informes.
def main():
    results = [
        create_archive(ROOT / "dist/VetCare-web.zip", web=True),
        create_archive(ROOT / "dist/VetCare-WSGI-railway.zip"),
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
