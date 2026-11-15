"""Distribución de código auditada; no incluye datos ni entornos privados."""

import os
import zipfile
from pathlib import Path

from dotenv import dotenv_values

root = Path(__file__).resolve().parent.parent
target = root / "dist/VetCare-WSGI-railway.zip"
target.parent.mkdir(exist_ok=True)
directories = {"frontend", "vetcare", "sql", "scripts", "tests", "docs"}
files = {
    "run.py",
    "requirements.txt",
    "requirements-dev.txt",
    "README.md",
    ".env.example",
    ".gitignore",
    ".gitattributes",
    ".dockerignore",
    "Dockerfile",
    "Procfile",
    "gunicorn.conf.py",
    "railway.json",
    "railway.worker.json",
    "iniciar.ps1",
    "instalar.ps1",
}
private = dotenv_values(root / ".env", interpolate=False)
secrets = [
    v.encode()
    for k, v in private.items()
    if v and len(v) >= 12 and any(word in k for word in ["PASSWORD", "SECRET", "TOKEN"])
]
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
    for parent, dirs, names in os.walk(root):
        relative = Path(parent).relative_to(root)
        dirs[:] = [
            d
            for d in dirs
            if d not in {"__pycache__", "node_modules"}
            and (relative.parts or d in directories)
        ]
        for name in names:
            path = Path(parent) / name
            rel = path.relative_to(root)
            if len(rel.parts) == 1 and name not in files:
                continue
            if name.startswith(".env") and name != ".env.example":
                continue
            if path.suffix.lower() in {".pyc", ".dump", ".gz", ".zip", ".log"}:
                continue
            if path.suffix.lower() == ".sql" and rel.parts[0] != "sql":
                continue
            data = path.read_bytes()
            if any(secret in data for secret in secrets):
                raise RuntimeError("Secreto detectado; no publicar: " + str(rel))
            archive.writestr(rel.as_posix(), data)
with zipfile.ZipFile(target) as archive:
    names = set(archive.namelist())
    assert archive.testzip() is None
    assert "sql/001_wsgi.sql" in names and "frontend/pages/dashboard.html" in names
    assert not any(
        n == ".env" or n.startswith((".venv/", ".venv-wsgi/", "media/")) for n in names
    )
print(
    "Paquete verificado sin secretos:",
    target.name,
    "archivos:",
    len(names),
    "bytes:",
    target.stat().st_size,
)
