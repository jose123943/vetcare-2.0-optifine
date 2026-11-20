const rutaConsultas = "/api/consultas";
let consultas = [];
let filtroActual = "todas";
let idEnEdicion = null;

const formulario = document.querySelector("#formulario-consulta");
const listaConsultas = document.querySelector("#lista-consultas");
const mensaje = document.querySelector("#mensaje");
const estadoApi = document.querySelector("#estado-api");
const textoEstadoApi = document.querySelector("#texto-estado-api");
const botonGuardar = document.querySelector("#boton-guardar");
const botonCancelar = document.querySelector("#boton-cancelar");
const resultadosReporte = document.querySelector("#resultados-reporte");

const formatoPesos = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0
});

document.querySelector("#fecha-hoy").textContent =
  new Intl.DateTimeFormat("es-CO", {
    weekday: "long",
    day: "numeric",
    month: "long"
  }).format(new Date());

formulario.addEventListener("submit", guardarConsulta);
botonCancelar.addEventListener("click", limpiarFormulario);
document.querySelector("#busqueda").addEventListener("input", dibujarConsultas);
document.querySelector("#boton-reintentar").addEventListener("click", cargarConsultas);
document.querySelector("#boton-reporte").addEventListener("click", verReporte);

document.querySelectorAll("[data-filtro]").forEach(function (boton) {
  boton.addEventListener("click", function () {
    filtroActual = boton.dataset.filtro;
    document.querySelectorAll("[data-filtro]").forEach(function (otroBoton) {
      const estaActivo = otroBoton === boton;
      otroBoton.classList.toggle("active", estaActivo);
      otroBoton.setAttribute("aria-pressed", String(estaActivo));
    });
    dibujarConsultas();
  });
});

async function cargarConsultas() {
  listaConsultas.innerHTML = '<tr><td class="table-message" colspan="5">Cargando consultas…</td></tr>';
  document.querySelector("#boton-reintentar").hidden = true;
  ocultarMensaje();

  try {
    const respuesta = await fetch(rutaConsultas);
    if (!respuesta.ok) {
      throw new Error("No se pudo cargar la lista.");
    }

    consultas = await respuesta.json();
    estadoApi.classList.add("is-connected");
    estadoApi.classList.remove("is-error");
    textoEstadoApi.textContent = "Conectado";
    dibujarConsultas();
    actualizarResumen();
  } catch (error) {
    estadoApi.classList.remove("is-connected");
    estadoApi.classList.add("is-error");
    textoEstadoApi.textContent = "Sin conexión";
    listaConsultas.innerHTML =
      '<tr><td class="table-message" colspan="5">No se pudo cargar. Revisa que el servidor y MySQL estén encendidos.</td></tr>';
    document.querySelector("#boton-reintentar").hidden = false;
    document.querySelector("#total-consultas").textContent = "—";
    document.querySelector("#total-por-cobrar").textContent = "—";
    document.querySelector("#total-abonos").textContent = "—";
    mostrarMensaje(error.message, true);
  }
}

function dibujarConsultas() {
  const texto = normalizarTexto(document.querySelector("#busqueda").value.trim());
  const visibles = consultas.filter(function (consulta) {
    const coincideTexto =
      normalizarTexto(consulta.nombreMascota + " " + consulta.motivoConsulta).includes(texto);
    const coincideFiltro =
      filtroActual === "todas" ||
      (filtroActual === "pagadas" && consulta.consultaPagada) ||
      (filtroActual === "pendientes" && !consulta.consultaPagada);
    return coincideTexto && coincideFiltro;
  });

  listaConsultas.replaceChildren();

  if (visibles.length === 0) {
    const fila = document.createElement("tr");
    const celda = document.createElement("td");
    celda.className = "table-message";
    celda.colSpan = 5;
    celda.textContent = consultas.length
      ? "No hay consultas que coincidan con la búsqueda."
      : "Todavía no hay consultas. Registra la primera en el formulario.";
    fila.append(celda);
    listaConsultas.append(fila);
  } else {
    visibles.forEach(function (consulta) {
      listaConsultas.append(crearFila(consulta));
    });
  }

  document.querySelector("#contador-lista").textContent =
    visibles.length + (visibles.length === 1 ? " consulta" : " consultas");
}

function crearFila(consulta) {
  const fila = document.createElement("tr");

  const mascota = document.createElement("td");
  const nombre = document.createElement("span");
  nombre.className = "pet-name";
  nombre.textContent = consulta.nombreMascota;
  mascota.append(nombre);
  if (consulta.veterinarioAsignado) {
    const veterinario = document.createElement("span");
    veterinario.className = "vet-name";
    veterinario.textContent = consulta.veterinarioAsignado;
    mascota.append(veterinario);
  }

  const motivo = document.createElement("td");
  motivo.textContent = consulta.motivoConsulta;

  const valor = document.createElement("td");
  valor.className = "money-cell";
  valor.textContent = formatoPesos.format(Number(consulta.valorConsulta));

  const estado = document.createElement("td");
  const insignia = document.createElement("span");
  insignia.className = "badge " + (consulta.consultaPagada ? "badge-paid" : "badge-pending");
  insignia.textContent = consulta.consultaPagada ? "Pagada" : "Pendiente";
  estado.append(insignia);

  const acciones = document.createElement("td");
  acciones.className = "action-cell";
  acciones.append(
    crearBotonFila("Editar", "row-action", function () {
      editarConsulta(consulta);
    })
  );
  acciones.append(
    crearBotonFila("Borrar", "row-action delete-action", function () {
      borrarConsulta(consulta);
    })
  );

  fila.append(mascota, motivo, valor, estado, acciones);
  return fila;
}

function crearBotonFila(texto, clase, accion) {
  const boton = document.createElement("button");
  boton.type = "button";
  boton.className = clase;
  boton.textContent = texto;
  boton.addEventListener("click", accion);
  return boton;
}

async function guardarConsulta(evento) {
  evento.preventDefault();
  ocultarMensaje();

  const campos = new FormData(formulario);
  const consulta = {
    nombreMascota: campos.get("nombreMascota").trim(),
    motivoConsulta: campos.get("motivoConsulta").trim(),
    valorConsulta: Number(campos.get("valorConsulta")),
    veterinarioAsignado: campos.get("veterinarioAsignado").trim(),
    consultaPagada: campos.get("consultaPagada") === "on"
  };

  const metodo = idEnEdicion ? "PUT" : "POST";
  const url = idEnEdicion ? rutaConsultas + "/" + idEnEdicion : rutaConsultas;

  try {
    const respuesta = await fetch(url, {
      method: metodo,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(consulta)
    });
    const resultado = await respuesta.json();

    if (!respuesta.ok) {
      throw new Error(resultado.mensaje || "No se pudo guardar la consulta.");
    }

    const estabaEditando = Boolean(idEnEdicion);
    limpiarFormulario();
    await cargarConsultas();
    mostrarMensaje(estabaEditando ? "Consulta actualizada." : "Consulta registrada.");
  } catch (error) {
    mostrarMensaje(error.message, true);
  }
}

function editarConsulta(consulta) {
  idEnEdicion = consulta.idConsulta;
  formulario.elements.nombreMascota.value = consulta.nombreMascota;
  formulario.elements.motivoConsulta.value = consulta.motivoConsulta;
  formulario.elements.valorConsulta.value = Number(consulta.valorConsulta);
  formulario.elements.veterinarioAsignado.value = consulta.veterinarioAsignado || "";
  formulario.elements.consultaPagada.checked = consulta.consultaPagada;
  document.querySelector("#etiqueta-formulario").textContent = "EDITAR VISITA";
  document.querySelector("#titulo-formulario").textContent = "Actualizar consulta";
  botonGuardar.innerHTML = "<span aria-hidden=\"true\">✓</span> Guardar cambios";
  botonCancelar.hidden = false;
  formulario.elements.nombreMascota.focus();
}

function limpiarFormulario() {
  formulario.reset();
  idEnEdicion = null;
  document.querySelector("#etiqueta-formulario").textContent = "NUEVA VISITA";
  document.querySelector("#titulo-formulario").textContent = "Registrar consulta";
  botonGuardar.innerHTML = "<span aria-hidden=\"true\">＋</span> Guardar consulta";
  botonCancelar.hidden = true;
}

async function borrarConsulta(consulta) {
  const confirmar = window.confirm(
    "¿Borrar la consulta de " + consulta.nombreMascota + "? Si tiene historia clínica, la base de datos no permitirá eliminarla."
  );
  if (!confirmar) {
    return;
  }

  try {
    const respuesta = await fetch(rutaConsultas + "/" + consulta.idConsulta, {
      method: "DELETE"
    });
    const resultado = await respuesta.json();
    if (!respuesta.ok) {
      throw new Error(resultado.mensaje || "No se pudo borrar la consulta.");
    }

    if (idEnEdicion === consulta.idConsulta) {
      limpiarFormulario();
    }
    await cargarConsultas();
    mostrarMensaje("Consulta eliminada.");
  } catch (error) {
    mostrarMensaje(error.message, true);
  }
}

async function verReporte() {
  const boton = document.querySelector("#boton-reporte");
  boton.disabled = true;
  boton.textContent = "Cargando reporte…";

  try {
    const respuesta = await fetch(rutaConsultas + "/reporte/abono-pendiente");
    const filas = await respuesta.json();
    if (!respuesta.ok) {
      throw new Error(filas.mensaje || "No se pudo cargar el reporte.");
    }

    dibujarReporte(filas);
  } catch (error) {
    resultadosReporte.hidden = false;
    document.querySelector("#titulo-resultados").textContent = error.message;
    document.querySelector("#lista-reporte").replaceChildren();
  } finally {
    boton.disabled = false;
    boton.innerHTML = 'Ver consultas que aplican <span aria-hidden="true">→</span>';
  }
}

function dibujarReporte(filas) {
  const titulo = document.querySelector("#titulo-resultados");
  const lista = document.querySelector("#lista-reporte");
  lista.replaceChildren();
  resultadosReporte.hidden = false;

  if (filas.length === 0) {
    titulo.textContent = "No hay consultas que requieran abono.";
    return;
  }

  titulo.textContent = filas.length + (filas.length === 1
    ? " consulta requiere abono:"
    : " consultas requieren abono:");

  filas.forEach(function (consulta) {
    const elemento = document.createElement("li");
    const mascota = document.createElement("span");
    const valor = document.createElement("span");
    mascota.textContent = consulta.nombreMascota;
    valor.textContent = formatoPesos.format(Number(consulta.valorConsulta));
    elemento.append(mascota, valor);
    lista.append(elemento);
  });
}

async function actualizarResumen() {
  document.querySelector("#total-consultas").textContent = String(consultas.length);
  const porCobrar = consultas
    .filter(function (consulta) {
      return !consulta.consultaPagada;
    })
    .reduce(function (total, consulta) {
      return total + Number(consulta.valorConsulta);
    }, 0);
  document.querySelector("#total-por-cobrar").textContent = formatoPesos.format(porCobrar);

  try {
    const respuesta = await fetch(rutaConsultas + "/reporte/abono-pendiente");
    if (!respuesta.ok) {
      throw new Error("No se pudo cargar el reporte.");
    }
    const abonos = await respuesta.json();
    document.querySelector("#total-abonos").textContent = String(abonos.length);
  } catch (error) {
    document.querySelector("#total-abonos").textContent = "—";
  }
}

function normalizarTexto(texto) {
  return texto
    .toLocaleLowerCase("es")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function mostrarMensaje(texto, esError) {
  mensaje.textContent = texto;
  mensaje.classList.toggle("is-error", Boolean(esError));
  mensaje.hidden = false;
}

function ocultarMensaje() {
  mensaje.hidden = true;
  mensaje.classList.remove("is-error");
}

cargarConsultas();
