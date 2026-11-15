import json
from contextlib import ExitStack
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from werkzeug.wrappers import Request, Response

from .validation import Problem


def json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds())
        return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"
    raise TypeError(type(value).__name__)


def response_json(value, status=200):
    return Response(
        json.dumps(value, ensure_ascii=False, default=json_default),
        status=status,
        content_type="application/json; charset=utf-8",
    )


class Context:
    def __init__(self, app, environ):
        self.app = app
        self.request = Request(environ)
        self.request.max_content_length = 6 * 1024 * 1024
        self.request.max_form_memory_size = 1024 * 1024
        self.request.max_form_parts = 100
        self._db = None
        self._data = None
        self.stack = ExitStack()
        self.cookies = []
        self.clear_cookies = False
        self.session = None

    @property
    def db(self):
        if self._db is None:
            self._db = self.stack.enter_context(self.app.database.lease())
        return self._db

    @property
    def data(self):
        if self._data is None:
            self._data = (
                self.request.get_json()
                if self.request.is_json
                else self.request.form.to_dict()
            )
            if not isinstance(self._data, dict):
                raise Problem("Envía un objeto JSON válido.")
        return self._data

    def finish(self, response):
        for name, value, http_only in self.cookies:
            response.set_cookie(
                name,
                value,
                httponly=http_only,
                secure=self.app.config.production,
                samesite="Lax",
                path="/",
            )
        if self.clear_cookies:
            for name in ["vetcare_sid", "csrftoken", "sessionid"]:
                response.delete_cookie(
                    name, path="/", secure=self.app.config.production, samesite="Lax"
                )
        return response


def page(query, params, ctx, key, serialize=lambda row: row, size=50, always=False):
    if not always and "pagina" not in ctx.request.args:
        return {"status": "ok", key: [serialize(r) for r in ctx.db.all(query, params)]}
    try:
        index = int(ctx.request.args.get("pagina", "1"))
        if not 1 <= index <= 100000:
            raise ValueError()
    except ValueError:
        raise Problem("Página no válida.")
    rows = ctx.db.all(
        query + " LIMIT %s OFFSET %s", (*params, size + 1, (index - 1) * size)
    )
    return {
        "status": "ok",
        key: [serialize(r) for r in rows[:size]],
        "pagina": index,
        "siguiente": index + 1 if len(rows) > size else None,
    }
