# Evidencias y archivos generados

Aquí se conservan los JSON de resultados y las salidas de las pruebas. Cada informe corresponde a su ejecución; las cifras históricas no describen necesariamente la base actual.

Las capturas PNG y los PDF sintéticos se retiraron del proyecto el 20 de noviembre de 2026: son resultados generados y no intervienen en el funcionamiento de la aplicación. Se conservaron en el respaldo privado verificado `limpieza_archivos_20261120_090957_949.zip`, dentro de `.codex/backups/vetcare` del usuario.

Los recorridos de `tests/browser/` vuelven a producir esas imágenes y documentos en esta carpeta. Permanecen excluidos de Git mediante `.gitignore`. Los PDF del historial solicitados para la documentación general siguen en `docs/`.

El paquete completo incluye las evidencias que estén disponibles al generarlo. `VetCare-web.zip` omite los resultados históricos pesados. Ambos ZIP se crean con `scripts/empaquetar_wsgi.py`; no se conservan distribuciones antiguas dentro del código fuente.

Los respaldos SQL con filas reales, credenciales, cookies de navegador y fotos privadas permanecen fuera del repositorio y de ambos paquetes.
