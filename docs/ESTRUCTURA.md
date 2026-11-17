# Estructura y lectura del código

Los archivos se agrupan por responsabilidad. Los comentarios situados sobre funciones y secciones explican el trabajo que realiza cada bloque. El proyecto mantiene Python WSGI, MySQL y JavaScript nativo.

```text
VetCare/
├── run.py                      Comandos de ejecución y administración
├── vetcare/                    Backend Python
│   ├── application.py          HTTP, rutas, permisos y recursos públicos
│   ├── config.py               Entorno validado antes de arrancar
│   ├── db.py                   Pool, consultas y transacciones SQL
│   ├── security.py             Acceso, sesiones, CSRF y permisos
│   ├── http.py                 Contexto, cookies, JSON y paginación
│   ├── migrations.py           SQL versionado con checksums
│   ├── maintenance.py          Respaldos e integridad
│   ├── demo.py                 Limpieza y datos ficticios explícitos
│   └── services/               Reglas de clínica, facturación y adopción
├── frontend/
│   ├── pages/                  Las cuatro pantallas HTML
│   └── assets/
│       ├── css/                Base, interfaz y adopciones
│       ├── js/                 Módulos de cada pantalla
│       └── images/             Imágenes que utiliza la aplicación
├── scripts/                    Configuración, mantenimiento y publicación
├── sql/                        Migraciones aplicadas; sus bytes no se editan
├── tests/
│   ├── test_*.py               Pruebas automatizadas de backend
│   ├── fixtures/               Datos sintéticos de compatibilidad
│   └── browser/                Preparación, servidor y recorridos Edge
├── docs/
│   ├── ESTRUCTURA.md           Este mapa
│   ├── RAILWAY.md              Pasos de publicación y variables privadas
│   ├── PRUEBAS_WSGI.md         Alcance y resultados comprobados
│   └── evidencias/             JSON, capturas, PDF y salidas de pruebas
├── .github/workflows/          Comprobaciones automáticas de GitHub
├── build/                      Gzip/manifiesto generados, fuera de Git
├── dist/                       ZIP de distribución, fuera de Git
└── media/                      Fotos privadas persistentes, fuera de Git
```

## Cómo sigue una petición

El servidor carga `vetcare/wsgi.py` o `run.py serve`. `application.py` identifica la ruta, comprueba sesión/permisos y llama al servicio. El servicio valida datos y utiliza `db.py`; las escrituras de negocio confirman datos e idempotencia en una transacción. `http.py` prepara la respuesta y sus cookies.

`frontend/assets/js/bootstrap.js` obtiene la sesión y carga los módulos correspondientes. `clinic.js` controla las pestañas administrativas; `owner-search.js` comparte el buscador; `configuration.js` administra cuentas y cuestionarios. Los módulos `adoptions-admin.js` y `adoptions-public.js` separan la gestión privada y el catálogo público. `interface.js` sólo controla presentación y animaciones.

## Herramientas

| Comando con el Python del entorno | Responsabilidad |
|---|---|
| `scripts/configurar_wsgi.py` | Configura MySQL y firma en `.env` privado |
| `scripts/configurar_gmail.py` | Valida y guarda SMTP sin enviar correos de prueba |
| `scripts/limpiar_datos.py` | Previsualiza la limpieza; sólo `--aplicar` vacía datos |
| `scripts/preparar_demostracion.py` | Carga ejemplos sólo cuando se solicita explícitamente |
| `scripts/probar_wsgi.py` | Ejecuta la suite en bases `test_vetcare_` aisladas |
| `scripts/verificar_despliegue.py` | Revisa estructura; `--con-base` consulta MySQL sin modificarlo |
| `scripts/build_assets.py` | Genera gzip y manifiesto sin Node ni conexión SQL |
| `scripts/empaquetar_wsgi.py` | Distribuye código con exclusión y comprobación de secretos |
| `scripts/documentar_funciones.py` | Actualiza la referencia técnica del Markdown |

Las pruebas y la documentación de recuperación se conservan porque permiten verificar funciones y recuperar versiones. Los informes anteriores son históricos; no equivalen al estado actual de la base.

## Archivos que no admiten comentarios internos

Los JSON de Railway deben seguir siendo JSON válido. Sus claves están explicadas en `RAILWAY.md`. Las migraciones SQL aplicadas no se reformatean ni reciben comentarios nuevos, porque eso cambiaría sus checksums. [sql/README.md](../sql/README.md) explica sus grupos sin alterar los archivos ya registrados en MySQL.

## Entornos y archivos generados

`.env`, `.venv-wsgi`, `media`, `build`, `dist`, cachés y respaldos privados no se incluyen en Git ni en la imagen. Los recursos comprimidos se generan durante el build; en desarrollo se sirve el código fuente legible. No se retiró ninguna dependencia declarada que siga siendo necesaria para funciones existentes.

La revisión automática de herramientas bloqueó la eliminación de las carpetas antiguas que quedaron vacías, sin dar un motivo más concreto que bloqueo de política. No contienen código y no se incluyen en los ZIP. Las cachés locales previamente bloqueadas permanecen excluidas de Git y de la distribución; esto no impide ejecutar ni publicar el código organizado.
