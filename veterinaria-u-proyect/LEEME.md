# Veterinaria U Proyect

Aplicación sencilla para registrar, buscar, actualizar y eliminar consultas veterinarias. La página está hecha con HTML, CSS y JavaScript; el servidor JavaScript ofrece la API y MySQL guarda los datos.

## Archivos

- index.html: estructura de la página.
- estilos.css: colores, distribución y adaptación a pantallas pequeñas.
- script.js: formulario, búsqueda, filtros y comunicación con la API.
- server.js: rutas, validaciones y conexión con MySQL.
- veterinaria.sql: tablas, relación y datos de ejemplo.

Todo está en esta misma carpeta para que sea fácil de recorrer y explicar.

## Cómo iniciar

1. Abre veterinaria.sql en MySQL Workbench o HeidiSQL y ejecútalo. Crea la base veterinaria_u_proyect con las tablas consultas e historial_clinico.
2. Abre una terminal en esta carpeta y ejecuta npm install.
3. Si MySQL usa el usuario root sin contraseña, ejecuta npm start. Si tus datos son distintos, configura DB_USER y DB_PASSWORD antes de iniciar. También puedes cambiar DB_HOST, DB_PORT y DB_NAME.
4. Abre http://localhost:3000 en el navegador.

El servidor usa por defecto MySQL en localhost:3306, usuario root, contraseña vacía y base veterinaria_u_proyect.

## Cómo explicarlo

1. El formulario envía los datos al servidor con fetch.
2. El servidor valida los campos y ejecuta una consulta SQL con parámetros.
3. La página vuelve a pedir la lista y dibuja las consultas.
4. El botón de reporte consulta una ruta que busca consultas sin pagar cuyo valor supera $50.000. Es un control administrativo y no retrasa la atención de urgencias.
5. historial_clinico.id_consulta apunta a consultas.id_consulta. La llave foránea usa ON DELETE RESTRICT, por eso MySQL impide borrar una consulta que tenga historia clínica; la API responde con un conflicto 409.

## Rutas de la API

- GET /api/consultas: listar consultas.
- GET /api/consultas/:id: buscar una consulta.
- POST /api/consultas: registrar una consulta.
- PUT /api/consultas/:id: actualizarla.
- DELETE /api/consultas/:id: borrarla si no tiene historia clínica.
- GET /api/consultas/reporte/abono-pendiente: mostrar consultas de más de $50.000 que siguen sin pagar.

Los errores de datos incompletos responden 400, una consulta inexistente responde 404 y una consulta con historia asociada responde 409. Si MySQL no responde, la página muestra un mensaje y permite reintentar.

## Ayuda usada

Se usó un asistente de IA para organizar y redactar el código inicial. El grupo debe recorrer cada archivo, ejecutar el proyecto y explicar las rutas, la relación SQL y la regla de abono antes de sustentarlo.
