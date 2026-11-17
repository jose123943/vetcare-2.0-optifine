FROM python:3.12-slim
# Entorno de ejecución: salida inmediata y sin cachés Python en la imagen.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
# Dependencias separadas del código para reutilizar la capa de instalación.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Sólo archivos de ejecución; no entran entornos, pruebas, evidencias ni secretos.
COPY vetcare ./vetcare
COPY frontend ./frontend
COPY sql ./sql
COPY scripts ./scripts
COPY run.py gunicorn.conf.py ./
# Recursos gzip preparados durante el build, sin conexión a MySQL.
RUN python scripts/build_assets.py
# Gunicorn recibe PORT desde Railway y activa el monitor de agenda por worker.
CMD ["gunicorn", "--config", "gunicorn.conf.py", "vetcare.wsgi:application"]
