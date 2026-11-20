const express = require("express");
const mysql = require("mysql2/promise");
const path = require("path");

const app = express();
const puerto = Number(process.env.PORT) || 3000;

const baseDatos = mysql.createPool({
  host: process.env.DB_HOST || "localhost",
  port: Number(process.env.DB_PORT) || 3306,
  user: process.env.DB_USER || "root",
  password: process.env.DB_PASSWORD || "",
  database: process.env.DB_NAME || "veterinaria_u_proyect",
  waitForConnections: true,
  connectionLimit: 5,
  charset: "utf8mb4"
});

const columnasConsulta =
  "id_consulta AS idConsulta, nombre_mascota AS nombreMascota, " +
  "motivo_consulta AS motivoConsulta, CAST(valor_consulta AS CHAR) AS valorConsulta, " +
  "consulta_pagada AS consultaPagada, veterinario_asignado AS veterinarioAsignado";

app.use(express.json());

app.get("/", function (req, res) {
  res.sendFile(path.join(__dirname, "index.html"));
});

app.get("/estilos.css", function (req, res) {
  res.sendFile(path.join(__dirname, "estilos.css"));
});

app.get("/script.js", function (req, res) {
  res.sendFile(path.join(__dirname, "script.js"));
});

app.get("/api/consultas", async function (req, res) {
  const [filas] = await baseDatos.execute(
    "SELECT " + columnasConsulta + " FROM consultas ORDER BY id_consulta DESC"
  );
  res.json(filas.map(convertirConsulta));
});

// Esta ruta contiene la regla: pendiente de pago y valor superior a $50.000.
app.get("/api/consultas/reporte/abono-pendiente", async function (req, res) {
  const [filas] = await baseDatos.execute(
    "SELECT " + columnasConsulta +
    " FROM consultas WHERE consulta_pagada = FALSE AND valor_consulta > 50000.00" +
    " ORDER BY valor_consulta DESC"
  );
  res.json(filas.map(convertirConsulta));
});

app.get("/api/consultas/:id", async function (req, res) {
  const consulta = await buscarConsulta(req.params.id);
  if (!consulta) {
    return res.status(404).json({
      error: "CONSULTA_NO_ENCONTRADA",
      mensaje: "No existe una consulta con ese identificador."
    });
  }
  res.json(consulta);
});

app.post("/api/consultas", async function (req, res) {
  const resultado = validarConsulta(req.body);
  if (resultado.error) {
    return res.status(400).json({
      error: "DATOS_INCOMPLETOS",
      mensaje: resultado.error
    });
  }

  const consulta = resultado.consulta;
  const [insercion] = await baseDatos.execute(
    "INSERT INTO consultas " +
    "(nombre_mascota, motivo_consulta, valor_consulta, consulta_pagada, veterinario_asignado) " +
    "VALUES (?, ?, ?, ?, ?)",
    [
      consulta.nombreMascota,
      consulta.motivoConsulta,
      consulta.valorConsulta,
      consulta.consultaPagada,
      consulta.veterinarioAsignado
    ]
  );

  res.status(201).json(await buscarConsulta(insercion.insertId));
});

app.put("/api/consultas/:id", async function (req, res) {
  const id = convertirId(req.params.id);
  if (!id || !(await buscarConsulta(id))) {
    return res.status(404).json({
      error: "CONSULTA_NO_ENCONTRADA",
      mensaje: "No existe una consulta con ese identificador."
    });
  }

  const resultado = validarConsulta(req.body);
  if (resultado.error) {
    return res.status(400).json({
      error: "DATOS_INCOMPLETOS",
      mensaje: resultado.error
    });
  }

  const consulta = resultado.consulta;
  await baseDatos.execute(
    "UPDATE consultas SET nombre_mascota = ?, motivo_consulta = ?, " +
    "valor_consulta = ?, consulta_pagada = ?, veterinario_asignado = ? " +
    "WHERE id_consulta = ?",
    [
      consulta.nombreMascota,
      consulta.motivoConsulta,
      consulta.valorConsulta,
      consulta.consultaPagada,
      consulta.veterinarioAsignado,
      id
    ]
  );
  res.json(await buscarConsulta(id));
});

app.delete("/api/consultas/:id", async function (req, res) {
  const id = convertirId(req.params.id);
  if (!id) {
    return res.status(404).json({
      error: "CONSULTA_NO_ENCONTRADA",
      mensaje: "No existe una consulta con ese identificador."
    });
  }

  try {
    const [resultado] = await baseDatos.execute(
      "DELETE FROM consultas WHERE id_consulta = ?",
      [id]
    );
    if (resultado.affectedRows === 0) {
      return res.status(404).json({
        error: "CONSULTA_NO_ENCONTRADA",
        mensaje: "No existe una consulta con ese identificador."
      });
    }
    res.json({ mensaje: "Consulta eliminada." });
  } catch (error) {
    if (error.code === "ER_ROW_IS_REFERENCED_2") {
      return res.status(409).json({
        error: "CONSULTA_CON_HISTORIAL",
        mensaje: "No se puede borrar: esta consulta tiene historia clínica asociada."
      });
    }
    throw error;
  }
});

// Express muestra un mensaje claro si el JSON está mal o la base no responde.
app.use(function (error, req, res, next) {
  if (error.status === 400 && error.type === "entity.parse.failed") {
    return res.status(400).json({
      error: "JSON_INVALIDO",
      mensaje: "Revisa los datos enviados e inténtalo de nuevo."
    });
  }

  console.error("Error en la solicitud:", error.message);
  res.status(500).json({
    error: "ERROR_SERVIDOR",
    mensaje: "No se pudo completar la solicitud. Revisa el servidor y la base de datos."
  });
});

async function buscarConsulta(idRecibido) {
  const id = convertirId(idRecibido);
  if (!id) {
    return null;
  }

  const [filas] = await baseDatos.execute(
    "SELECT " + columnasConsulta + " FROM consultas WHERE id_consulta = ?",
    [id]
  );
  return filas.length ? convertirConsulta(filas[0]) : null;
}

function convertirConsulta(fila) {
  return {
    idConsulta: Number(fila.idConsulta),
    nombreMascota: fila.nombreMascota,
    motivoConsulta: fila.motivoConsulta,
    valorConsulta: fila.valorConsulta,
    consultaPagada: Boolean(fila.consultaPagada),
    veterinarioAsignado: fila.veterinarioAsignado || ""
  };
}

function convertirId(valor) {
  const id = Number(valor);
  return Number.isInteger(id) && id > 0 ? id : null;
}

function validarConsulta(datos) {
  if (!datos || typeof datos !== "object" || Array.isArray(datos)) {
    return { error: "Envía los datos de la consulta en formato JSON." };
  }

  const nombreMascota =
    typeof datos.nombreMascota === "string" ? datos.nombreMascota.trim() : "";
  const motivoConsulta =
    typeof datos.motivoConsulta === "string" ? datos.motivoConsulta.trim() : "";
  const valorTexto = String(datos.valorConsulta ?? "").trim();
  const veterinarioAsignado =
    typeof datos.veterinarioAsignado === "string"
      ? datos.veterinarioAsignado.trim()
      : "";
  const valorConsulta = Number(valorTexto);

  if (!nombreMascota || !motivoConsulta || !valorTexto) {
    return { error: "Nombre, motivo y valor de la consulta son obligatorios." };
  }
  if (nombreMascota.length > 120 || motivoConsulta.length > 200) {
    return { error: "Revisa la longitud del nombre o del motivo." };
  }
  if (!/^\d{1,8}(\.\d{1,2})?$/.test(valorTexto) || !Number.isFinite(valorConsulta)) {
    return { error: "El valor no puede ser negativo y admite máximo dos decimales." };
  }
  if (
    datos.veterinarioAsignado !== undefined &&
    datos.veterinarioAsignado !== null &&
    typeof datos.veterinarioAsignado !== "string"
  ) {
    return { error: "El nombre del veterinario debe ser texto." };
  }
  if (veterinarioAsignado.length > 120) {
    return { error: "El nombre del veterinario no puede superar 120 caracteres." };
  }
  if (
    datos.consultaPagada !== undefined &&
    typeof datos.consultaPagada !== "boolean"
  ) {
    return { error: "El estado de pago debe ser verdadero o falso." };
  }

  return {
    consulta: {
      nombreMascota: nombreMascota,
      motivoConsulta: motivoConsulta,
      valorConsulta: valorConsulta.toFixed(2),
      consultaPagada: datos.consultaPagada === true,
      veterinarioAsignado: veterinarioAsignado || null
    }
  };
}

app.listen(puerto, function () {
  console.log("Veterinaria U Proyect está disponible en http://localhost:" + puerto);
});
