"""Ejecuta integración real y guarda evidencia sin secretos ni fixtures."""

import json
import sys
import time
import unittest
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
suite = unittest.defaultTestLoader.loadTestsFromNames(
    ["tests.test_wsgi", "tests.test_smtp"]
)
start = time.monotonic()
with (root / "docs/wsgi-pruebas.txt").open("w", encoding="utf-8") as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
report = {
    "ejecutadas": result.testsRun,
    "fallos": len(result.failures),
    "errores": len(result.errors),
    "omitidas": len(result.skipped),
    "duracion_segundos": round(time.monotonic() - start, 3),
    "exito": result.wasSuccessful(),
    "framework_requerido": False,
    "base_de_pruebas": "test_vetcare_* (aislada)",
}
(root / "docs/wsgi_pruebas.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(json.dumps(report))
raise SystemExit(0 if result.wasSuccessful() else 1)
