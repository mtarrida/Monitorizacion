"""Ejecuta las pruebas del motor del Constructor (JavaScript puro) con Node.js, si está instalado."""
import os
import shutil
import subprocess

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.skipif(shutil.which("node") is None, reason="Hace falta Node.js para probar el motor del Constructor")
def test_motor_del_constructor():
    resultado = subprocess.run(
        ["node", os.path.join("tests", "web", "test_motor.js")],
        cwd=RAIZ, capture_output=True, text=True, timeout=60,
    )
    assert resultado.returncode == 0, resultado.stderr or resultado.stdout
    assert "MOTOR OK" in resultado.stdout
