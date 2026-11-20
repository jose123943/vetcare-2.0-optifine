# Comprueba que los datos recibidos tengan el formato y los valores permitidos.
import re
from datetime import date, time
from decimal import Decimal, InvalidOperation


# Representa un error que puede explicarse al usuario de forma controlada.
class Problem(Exception):
    # Representa un error previsto con mensaje seguro y estado HTTP.
    def __init__(self, message, status=400):
        self.message = message
        self.status = status
        super().__init__(message)


# Valida presencia y longitud de un campo.
def required(row, name, max_length=200, optional=False):
    value = str(row.get(name, "") or "").strip()
    if not value and not optional:
        raise Problem(f"El campo {name} es obligatorio.")
    if len(value) > max_length:
        raise Problem(f"{name} admite hasta {max_length} caracteres.")
    return value


# Valida un entero exacto y su rango, excluyendo booleanos.
def integer(value, name="valor", minimum=0, maximum=2147483647):
    if isinstance(value, bool):
        raise Problem(f"{name} debe ser un número entero.")
    try:
        n = int(value)
        if str(n) != str(value).strip() or not minimum <= n <= maximum:
            raise ValueError()
        return n
    except (TypeError, ValueError):
        raise Problem(f"{name} debe estar entre {minimum} y {maximum}.")


# Valida un Decimal finito no negativo con hasta dos decimales.
def money(value, maximum="99999999.99"):
    try:
        n = Decimal(str(value))
        if (
            not n.is_finite()
            or n < 0
            or n > Decimal(maximum)
            or n != n.quantize(Decimal(".01"))
        ):
            raise ValueError()
        return n
    except (ValueError, TypeError, InvalidOperation):
        raise Problem("Importe no válido; utiliza hasta dos decimales.")


# Interpreta una fecha ISO válida.
def day(value, name="fecha"):
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        raise Problem(f"{name} no es una fecha válida.")


# Interpreta una hora local sin zona horaria incrustada.
def clock(value):
    try:
        result = time.fromisoformat(str(value))
        if result.tzinfo:
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise Problem("Hora no válida.")


# Valida la estructura básica y longitud de un correo.
def email(value, optional=False):
    text = str(value or "").strip()
    if not text and optional:
        return ""
    if len(text) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", text):
        raise Problem("Correo electrónico no válido.")
    return text


# Restringe un valor a las opciones admitidas por el servicio.
def choice(value, allowed, name="estado"):
    if value not in allowed:
        raise Problem(f"{name} no es válido.")
    return value


# Convierte la ausencia de un registro en una respuesta 404.
def found(row):
    if row is None:
        raise Problem("El registro solicitado no existe.", 404)
    return row
