import re
from datetime import date, time
from decimal import Decimal, InvalidOperation


class Problem(Exception):
    def __init__(self, message, status=400):
        self.message = message
        self.status = status
        super().__init__(message)


def required(row, name, max_length=200, optional=False):
    value = str(row.get(name, "") or "").strip()
    if not value and not optional:
        raise Problem(f"El campo {name} es obligatorio.")
    if len(value) > max_length:
        raise Problem(f"{name} admite hasta {max_length} caracteres.")
    return value


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


def day(value, name="fecha"):
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        raise Problem(f"{name} no es una fecha válida.")


def clock(value):
    try:
        result = time.fromisoformat(str(value))
        if result.tzinfo:
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise Problem("Hora no válida.")


def email(value, optional=False):
    text = str(value or "").strip()
    if not text and optional:
        return ""
    if len(text) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", text):
        raise Problem("Correo electrónico no válido.")
    return text


def choice(value, allowed, name="estado"):
    if value not in allowed:
        raise Problem(f"{name} no es válido.")
    return value


def found(row):
    if row is None:
        raise Problem("El registro solicitado no existe.", 404)
    return row
