# Evidencia de la migración WSGI

Pruebas realizadas en Windows, Python 3.14, MySQL 8.4.13 de Railway y un entorno `.venv-wsgi` sin Django. Las escrituras automatizadas usan bases nuevas con prefijo `test_vetcare_`, separadas de la base operativa. No se instalaron fixtures en `railway`.

## Resultados comprobados

| Comprobación | Resultado / evidencia |
|---|---|
| Suite final tras retirar el código anterior | **30 pruebas, 0 fallos, 0 errores, 0 omitidas**, 178,89 s. `wsgi_pruebas.json`, `wsgi-pruebas.txt` |
| Recuperación y estados | Dos casos incluidos en la suite final, también repetidos aisladamente: interrupción deliberada de una conexión propia en base aislada, respuesta 503 y recuperación; edición de mascota conserva propietario inactivo. `wsgi-pruebas-conexion-estado.txt` |
| Transporte SMTP | Un caso incluido en la suite final, también verificado por separado, con socket SMTP local real, MIME texto+HTML y caracteres escapados; no envía a Internet. `wsgi-smtp.txt` |
| Navegador clínico Edge | Registro de tres mascotas, propietario/selección de pacientes, agenda, factura y PDF, móvil y logout. `wsgi-navegador-clinica.txt` |
| Navegador de adopciones Edge | Catálogo escritorio/tableta/móvil, cuestionario, resultado, revisión de bienestar, autorización y entrega. `wsgi-navegador-adopciones.txt` |
| Navegador de configuración Edge | Login con cuenta sintética real, alta de cuenta, creación/edición/publicación de borrador y vacuna. `wsgi-navegador-configuracion.txt` |
| Navegador CRUD y fotografías Edge | Edición de cliente, bloqueo de eliminación con historiales, eliminación de cliente vacío, alta/edición/baja de veterinario y registro de mascota de adopción con fotografía. `wsgi-navegador-crud.txt` |
| Compatibilidad de contraseñas | Vector PBKDF2 generado por el programa anterior verificado sin Django; login de cuenta sintética PBKDF2 actualiza a Argon2 |
| Compatibilidad de resultados privados antiguos | Firma de sesión anterior verificada y acceso del visitante a su solicitud; una firma alterada se rechaza |
| Seguridad | Sesión expirable/revocada, cookies HttpOnly/SameSite, Secure/HSTS en producción simulada, CSRF/Origin, staff/superusuario, bloqueo de intentos, IDOR, JSON inválido e inyección SQL |
| Concurrencia | Tres altas con igual clave producen un único cliente; citas simultáneas incompatibles se serializan; reenvíos de factura/adopción y segunda entrega se rechazan o devuelven la respuesta original |
| Adopciones | 66 % y 66,5 % no aprueban; 67 % sí. Fracciones exactas, snapshots y datos previos sin recalcular |
| Datos reales | Lectura SQL de 2 clientes, 2 mascotas, 4 citas y 3 facturas; generación de los 3 PDF históricos. `wsgi_lectura_datos_reales.json` |
| Integridad | **33 de 33 tablas originales idénticas**, comparando todas sus filas y columnas con el respaldo privado. `wsgi_integridad_completa.json` |
| Conexión y arranque real | `python run.py check` confirma MySQL y `Django instalado: False`; seis rutas web, salud, sesión, catálogo y estáticos responden 200. `wsgi_arranque_real.json` |
| Dependencias y código | `pip check` correcto; compilación y análisis de importaciones sin Django/Flask/FastAPI; verificación estática del backend sin errores básicos |

En total se comprobaron **30 pruebas automatizadas en la ejecución final**, además de cuatro recorridos de navegador. El ejecutor reúne 29 casos de la aplicación y uno de SMTP para futuras ejecuciones. También se prueba la cola de correos, fallo sin perder la cita y reintento, historiales, validaciones, rollback, fechas adyacentes sin solapamiento, paginación y PDF leído con pypdf. Los screenshots y el PDF de ejemplo contienen datos sintéticos. Se corrigió un fallo que bloqueaba formularios con `input name="id"`: se obtiene el identificador mediante `getAttribute`, evitando que el campo oculte `form.id`.

## Rendimiento observado

Mismo PC y base MySQL aislada, servicios sin escrituras concurrentes durante las mediciones, cliente HTTP en proceso, ocho muestras por ruta después de calentamiento. La versión anterior utilizó su middleware y sesión de base de datos; la nueva utilizó sesión SQL propia y pool. Se conservaron las muestras sin seleccionar sólo las favorables.

| Ruta | Mediana anterior | Mediana WSGI | Consultas antes → después |
|---|---:|---:|---:|
| Dashboard | 848,13 ms | 499,49 ms | 4 → 3 |
| Mascotas, página 1 | 684,22 ms | 341,85 ms | 3 → 2 |
| Facturas, página 1 | 671,53 ms | 332,49 ms | 3 → 2 |
| Cuestionario público | 334,62 ms | 360,69 ms | 1 → 2 |

Las reducciones medidas de las tres primeras rutas son aproximadamente 41 %, 50 % y 50 %. El cuestionario público empeora un 7,8 % en esta muestra: la versión anterior tenía caché local caliente y la nueva consulta directamente la estructura vigente. No se afirma que todas las rutas sean más rápidas ni que estos tiempos representen Railway en su red privada. Los contadores de la nueva aplicación excluyen inicialización del driver y control de transacciones; la comparación de latencia sí incluye la petición completa. Fuentes: `wsgi_rendimiento_old.json`, `wsgi_rendimiento_new.json`.

## Pendientes externos y alcance de la validación

1. **Cuenta personal real:** no se conoce su contraseña de acceso al sistema. Su fila/hash siguen intactos y se verificó el mismo formato heredado con cuenta sintética; falta un login manual de esa cuenta. La contraseña MySQL no es la contraseña de acceso a VetCare.
2. **SMTP externo:** no está configurado un proveedor/buzón real verificado. Se comprobaron generación, outbox, fallo/reintento y envío SMTP local. Falta entrega real con TLS y credenciales del proveedor.
3. **Railway público:** no se creó ni sustituyó el servicio web. Faltan acceso autenticado y autorización para costos, construcción Docker en Linux, prueba del dominio HTTPS, volumen persistente y rendimiento dentro de Railway. Las pruebas de cabeceras de producción son locales; no sustituyen esa validación.

La migración de código local está implementada y verificada en el alcance descrito. Estos puntos impiden declarar verificada una puesta en producción completa.

El vector de compatibilidad incluido en `tests/fixtures/legacy.json` fue generado por la versión anterior con una clave y contraseña **exclusivamente sintéticas**. Permite repetir las pruebas en otro equipo sin instalar el framework anterior, sin depender de archivos temporales privados y sin utilizar la clave de firma real como fixture.
