# Indica cómo iniciar el servidor web y el consumidor independiente de correos.
web: gunicorn --config gunicorn.conf.py vetcare.wsgi:application
worker: python run.py worker
