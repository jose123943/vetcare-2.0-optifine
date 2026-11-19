// Gesti?n administrativa: cl?nica, agenda, historiales, facturaci?n y correos.
'use strict';

const app = document.querySelector('#app');

const modal = document.querySelector('#modal');

const esc = (value) =>
    String(value ?? '').replace(
        /[&<>"']/g,
        (c) =>
            ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;',
            })[c],
    );

const cop = (value) =>
    new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
    }).format(Number(value));

const badge = (state) =>
    `<span class="badge ${esc(state)}">${esc(state)}</span>`;

const today = () =>
    new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Bogota' }).format(
        new Date(),
    );

let generation = 0;

let pageRefreshTimer;

let mailProcessing;

let petCache = [],
    vetCache = [],
    invoiceAppointments = [];

const handlers = new WeakMap();

// Presenta avisos temporales de ?xito o error.
function toast(text, error = false) {
    const node = document.createElement('div');
    node.className = `toast ${error ? 'error' : ''}`;
    node.textContent = text;

    document.querySelector('#toasts').append(node);
    setTimeout(() => node.remove(), 7000);
}

// Centraliza peticiones JSON, permisos y errores de red.
async function api(path, options = {}) {
    const response = await fetch(
        path.startsWith('/') ? path : `/inicio/api/${path}`,
        { credentials: 'same-origin', ...options },
    );

    if (response.status === 401) {
        location.href = '/';
        throw new Error('Tu sesión ha vencido.');
    }

    let data;
    try {
        data = await response.json();
    } catch {
        throw new Error('No se pudo leer la respuesta. Intenta de nuevo.');
    }

    if (!response.ok) {
        const err = new Error(
            data.message || 'No se pudo completar la solicitud.',
        );
        err.status = response.status;
        throw err;
    }

    return data;
}

// Drena la cola en peticiones separadas: Cloud Run mantiene CPU durante cada envío.
async function processMailQueue() {
    if (mailProcessing) return mailProcessing;
    mailProcessing = (async () => {
        let processed = 0;
        for (let i = 0; i < 5; i++) {
            const result = await api('notificaciones/procesar/', {
                method: 'POST',
                body: '{}',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': vetcare.csrf(),
                },
            });
            processed += result.procesadas;
            if (!result.procesadas || !result.pendientes) break;
        }
        return processed;
    })();
    try {
        return await mailProcessing;
    } finally {
        mailProcessing = null;
    }
}

// Construye un campo escapando valores del usuario.
function field(name, label, type = 'text', value = '', extra = '') {
    return `<label>${esc(label)}<input name="${esc(name)}" type="${type}" value="${esc(value)}" ${extra}></label>`;
}

// Construye un selector con sus opciones y selecci?n actual.
function select(name, label, options, value = '', extra = '') {
    return `<label>${esc(label)}<select name="${esc(name)}" ${extra}>${options.map(([v, t]) => `<option value="${esc(v)}" ${String(v) === String(value) ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
}

// Construye un ?rea de texto segura.
function area(name, label, value = '', extra = '') {
    return `<label class="full">${esc(label)}<textarea name="${name}" ${extra}>${esc(value)}</textarea></label>`;
}

// Compone el t?tulo y las acciones de cada pesta?a.
function title(kicker, name, desc, actions = '') {
    return `<div class="page-heading"><div><div class="eyebrow">${kicker}</div><h1>${name}</h1><p>${desc}</p></div><div class="actions">${actions}</div></div>`;
}

// Presenta filas o el estado vac?o de una tabla.
function table(headers, rows, empty = 'Aún no hay registros para mostrar.') {
    return `<div class="table-wrap"><table><thead><tr>${headers.map((h) => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows || `<tr><td colspan="${headers.length}"><div class="empty"><span>♧</span>${empty}</div></td></tr>`}</tbody></table></div>`;
}

// Incluye el diagn?stico del formulario y su bot?n de guardado.
function submit(text = 'Guardar') {
    return `<div class="form-error" role="alert"></div><div class="form-actions"><button type="submit">${text}</button></div>`;
}

// Abre el di?logo reutilizable con el contenido del m?dulo.
function openModal(name, html) {
    document.querySelector('#modal-title').textContent = name;
    document.querySelector('#modal-content').innerHTML = html;
    if (!modal.open) modal.showModal();
}

// Asocia cada elemento de formulario a su operaci?n y libera referencias al retirarlo.
function bindForm(
    id,
    path,
    transform = (d) => d,
    success = () => {},
    method = 'POST',
) {
    const form = document.getElementById(id);
    form.dataset.path = path;
    form.dataset.method = method;

    handlers.set(form, { transform, success });
}

// Un único listener para todas las escrituras. Reutiliza la clave ante error de red.

// Guarda formularios con CSRF e idempotencia y restaura los controles tras un error.
document.addEventListener('submit', async (event) => {
    const form = event.target;

    if (!form.dataset.path) {
        if (form.classList.contains('logout-form')) {
            form.querySelector('button').disabled = true;
        }
        return;
    }

    event.preventDefault();

    if (form.dataset.busy || !form.reportValidity()) return;

    form.dataset.busy = '1';

    const buttons = [...form.querySelectorAll('button')];
    const labels = buttons.map((b) => b.innerHTML);

    buttons.forEach((b) => (b.disabled = true));

    const button = form.querySelector('[type=submit]');
    if (button) button.innerHTML = '<span class="spinner"></span>Guardando…';

    const errorBox = form.querySelector('.form-error');
    if (errorBox) errorBox.textContent = '';

    let storageKey;

    try {
        // El elemento es la clave: evita colisiones de ID y libera formularios retirados.

        const handler = handlers.get(form);

        if (!handler)
            throw new Error(
                'El formulario ya no está disponible. Abre de nuevo esta sección.',
            );

        const { transform, success } = handler;

        const formData = new FormData(form),
            multipart = form.enctype === 'multipart/form-data';

        const payload = transform(Object.fromEntries(formData), form);

        const body = multipart ? formData : JSON.stringify(payload);

        let signature = JSON.stringify(payload);

        if (multipart) {
            const signatures = [];
            for (const [name, value] of formData) {
                const bytes =
                    value instanceof File
                        ? await value.arrayBuffer()
                        : new TextEncoder().encode(value);
                const hash = await crypto.subtle.digest('SHA-256', bytes);
                signatures.push([
                    name,
                    Array.from(new Uint8Array(hash), (b) =>
                        b.toString(16).padStart(2, '0'),
                    ).join(''),
                ]);
            }
            signature = JSON.stringify(signatures);
        }

        const digest = await crypto.subtle.digest(
            'SHA-256',
            new TextEncoder().encode(form.dataset.path + signature),
        );

        const fingerprint = Array.from(new Uint8Array(digest), (b) =>
            b.toString(16).padStart(2, '0'),
        ).join('');

        storageKey = `vetcare:${document.body.dataset.user}:${fingerprint}`;

        let key = sessionStorage.getItem(storageKey);
        if (!key) {
            key = crypto.randomUUID();
            sessionStorage.setItem(storageKey, key);
        }

        const csrf = decodeURIComponent(
            document.cookie
                .split('; ')
                .find((v) => v.startsWith('csrftoken='))
                ?.split('=')
                .slice(1)
                .join('=') || '',
        );

        const result = await api(form.dataset.path, {
            method: form.dataset.method,
            body,
            headers: {
                ...(multipart ? {} : { 'Content-Type': 'application/json' }),
                'X-CSRFToken': csrf,
                'Idempotency-Key': key,
            },
        });

        sessionStorage.removeItem(storageKey);
        toast(result.message || 'Guardado correctamente.');

        if (
            /^(registrar\/cita\/|citas\/\d+\/editar\/|notificaciones\/\d+\/reintentar\/)/.test(
                form.dataset.path,
            )
        ) {
            processMailQueue().catch((error) =>
                toast(
                    `Los datos quedaron guardados. Revisa Notificaciones: ${error.message}`,
                    true,
                ),
            );
        }
        await success(result, form);
    } catch (error) {
        if (error.status && error.status < 500 && storageKey)
            sessionStorage.removeItem(storageKey);

        if (errorBox) errorBox.textContent = error.message;
        else toast(error.message, true);
    } finally {
        delete form.dataset.busy;
        buttons.forEach((b, i) => {
            b.disabled = false;
            b.innerHTML = labels[i];
        });
    }
});

// Gestiona cierres de di?logo y eliminaci?n de filas todav?a sin guardar.
document.addEventListener('click', (event) => {
    if (event.target.closest('[data-close]')) modal.close();

    if (event.target.closest('[data-pet-remove]')) {
        event.target.closest('.pet-card').remove();
        renumberPets();
    }

    if (event.target.closest('[data-service-remove]')) {
        event.target.closest('.service-row').remove();
        updateTotal();
    }
});

// Agrupa los datos editables de un propietario.
function ownerFields(c = {}) {
    return (
        field(
            'nombre',
            'Nombres *',
            'text',
            c.nombre,
            'required maxlength="50"',
        ) +
        field(
            'apellido',
            'Apellidos *',
            'text',
            c.apellido,
            'required maxlength="50"',
        ) +
        field(
            'documento',
            'Documento de identidad',
            'text',
            c.documento,
            'maxlength="30"',
        ) +
        field(
            'telefono',
            'Teléfono *',
            'tel',
            c.telefono,
            'required maxlength="20"',
        ) +
        field(
            'email',
            'Correo electrónico',
            'email',
            c.email,
            'maxlength="100"',
        ) +
        field(
            'direccion',
            'Dirección *',
            'text',
            c.direccion,
            'required maxlength="150"',
        )
    );
}

// Agrupa los campos de una mascota para alta o edici?n.
function petFields(m = {}, edit = false) {
    return (
        field(
            edit ? 'nombreMascota' : 'nombre',
            'Nombre de la mascota *',
            'text',
            m.nombre,
            'required maxlength="50"',
        ) +
        select(
            'especie',
            'Especie *',
            [
                ['', 'Selecciona'],
                ...['Perro', 'Gato', 'Ave', 'Conejo', 'Otro'].map((v) => [
                    v,
                    v,
                ]),
            ],
            m.especie,
            'required',
        ) +
        field('raza', 'Raza *', 'text', m.raza, 'required maxlength="50"') +
        select(
            'sexo',
            'Sexo',
            [
                ['', 'Sin registrar'],
                ['Hembra', 'Hembra'],
                ['Macho', 'Macho'],
            ],
            m.sexo,
        ) +
        field(
            'edad',
            'Edad (años) *',
            'number',
            m.edad ?? '',
            'min="0" max="100" step="1" required',
        ) +
        field(
            'peso',
            'Peso (kg) *',
            'number',
            m.peso ?? '',
            'min="0" max="999.99" step="0.01" required',
        ) +
        area('observaciones', 'Observaciones', m.observaciones)
    );
}

// Sincroniza n?meros y cantidad de fichas de pacientes.
function renumberPets() {
    document
        .querySelectorAll('#pets .pet-card')
        .forEach(
            (card, i) =>
                (card.querySelector('h3').textContent = `Mascota ${i + 1}`),
        );
    const n = document.querySelector('#pet-count');
    if (n) n.value = document.querySelectorAll('#pets .pet-card').length;
}

// A?ade una ficha respetando el m?ximo de pacientes por registro.
function addPet() {
    const container = document.querySelector('#pets');
    if (container.children.length >= 50) return;
    container.insertAdjacentHTML(
        'beforeend',
        `<div class="pet-card"><div class="panel-head"><h3></h3><button type="button" class="ghost" data-pet-remove>Quitar</button></div><div class="form-grid">${petFields()}</div></div>`,
    );
    renumberPets();
}

// Valida y registra una familia con sus mascotas en una operaci?n.
async function registrar() {
    app.innerHTML =
        title(
            'REGISTRO INTEGRAL',
            'Una familia, todas sus mascotas',
            'Registra al propietario y sus pacientes en una sola operación.',
        ) +
        `<form id="register"><section class="panel"><div class="panel-head"><h2>01 · Datos del propietario</h2><span class="badge">Cliente nuevo</span></div><div class="form-grid">${ownerFields()}</div><p class="helper">El documento es obligatorio para identificar al cliente. El correo es opcional.</p></section>

    <section class="panel"><div class="panel-head"><h2>02 · Sus mascotas</h2><button type="button" class="secondary" id="add-pet">＋ Agregar mascota</button></div><div class="count-control"><label>¿Cuántas mascotas?<input id="pet-count" type="number" min="1" max="50" value="1"></label><button type="button" class="secondary" id="set-count">Aplicar cantidad</button></div><div id="pets"></div>${submit('Registrar cliente y mascotas')}</section></form>`;

    document.querySelector('#register [name=documento]').required = true;

    addPet();
    document.querySelector('#add-pet').onclick = addPet;

    document.querySelector('#set-count').onclick = () => {
        const n = Number(document.querySelector('#pet-count').value);
        if (!Number.isInteger(n) || n < 1 || n > 50) {
            toast('Elige entre 1 y 50 mascotas.', true);
            return;
        }
        const c = document.querySelector('#pets');
        while (c.children.length < n) addPet();
        while (c.children.length > n) c.lastElementChild.remove();
        renumberPets();
    };

    bindForm(
        'register',
        'registrar/cliente-mascota/',
        (d, form) => {
            const top = {};
            form.querySelectorAll('section:first-child [name]').forEach(
                (i) => (top[i.name] = i.value),
            );

            const mascotas = [...form.querySelectorAll('.pet-card')].map(
                (card) =>
                    Object.fromEntries(
                        [...card.querySelectorAll('[name]')].map((i) => [
                            i.name,
                            i.value,
                        ]),
                    ),
            );

            return { ...top, mascotas };
        },
        () => registrar(),
    );
}

// Dibuja citas con propietario, profesional, horario y estado.
function appointmentRows(citas) {
    return citas
        .map(
            (c) =>
                `<tr><td><strong>${esc(c.mascota)}</strong><small>#C${c.id}</small></td><td>${esc(c.cliente)}</td><td>${esc(c.veterinario)}</td><td>${esc(c.fecha)}<small>${esc(c.hora)} · ${c.duracion_minutos} min</small></td><td>${esc(c.motivo)}</td><td>${badge(c.estado)} ${c.vencida ? badge('vencida') : ''}</td><td><button class="secondary small" data-cita="${c.id}">Ver detalle</button></td></tr>`,
        )
        .join('');
}

// Conecta los botones de detalle de las citas visibles.
function bindCitaButtons() {
    app.querySelectorAll('[data-cita]').forEach(
        (b) =>
            (b.onclick = () =>
                showCita(b.dataset.cita).catch((e) => toast(e.message, true))),
    );
}

// Consulta indicadores y citas pendientes del resumen.
async function dashboard(token) {
    const d = await api('dashboard/');
    if (token !== generation) return;

    const s = d.stats;

    app.innerHTML =
        title(
            'TU CLÍNICA, EN ORDEN',
            'Bienvenido a VetCare',
            'Una mirada al cuidado de tus pacientes y la actividad de tu clínica.',
            `<button onclick="location.hash='agendar'">＋ Agendar cita</button>`,
        ) +
        `<div class="stats">${[
            ['◷', 'Citas de hoy', s.hoy, 'Agenda del día'],
            ['♧', 'Clientes activos', s.clientes, 'Familias que confían en ti'],
            [
                '▦',
                'Citas pendientes',
                s.pendientes,
                'Por atender, de cualquier fecha',
            ],
            [
                '♡',
                'Vacunas por renovar',
                s.vacunas,
                'Fecha de vencimiento alcanzada',
            ],
        ]
            .map(
                ([icon, label, n, desc]) =>
                    `<article class="stat"><div class="stat-icon">${icon}</div><small>${label}</small><strong>${n}</strong><p>${desc}</p></article>`,
            )
            .join('')}</div>` +
        `<section class="panel"><div class="panel-head"><div><h2>Citas pendientes</h2><p>De la más cercana a la más lejana, por fecha y hora. Al finalizar pasan a Atendida.</p></div><button class="secondary small" onclick="location.hash='citas'">Toda la agenda ↗</button></div>${table(['Paciente', 'Propietario', 'Veterinario', 'Fecha y hora', 'Motivo', 'Estado', ''], appointmentRows(d.citas), 'Tu agenda está al día. No tienes citas pendientes.')}</section>`;

    const historic = document.createElement('p');
    historic.className = 'helper';
    historic.textContent = `Histórico: ${s.total} citas registradas.`;
    app.querySelector('.stats').after(historic);

    bindCitaButtons();
}

// Consulta la agenda y actualiza sus estados sin perder la paginaci?n.
async function citas(token) {
    let rows = [],
        next = 1,
        pagesLoaded = 0,
        busy = false;

    app.innerHTML =
        title(
            'AGENDA CLÍNICA',
            'Todas las citas',
            'Hoy y próximas primero, de la más cercana a la más lejana. Las pasadas quedan al final, de la más reciente a la más antigua. Al terminar pasan a Atendida.',
            `<button onclick="location.hash='agendar'">＋ Nueva cita</button>`,
        ) + '<section class="panel" id="appointments-list"></section>';

    // Solicita y presenta resultados de la secci?n con control de paginaci?n.
    async function load(refresh = false) {
        if (busy) return;
        busy = true;

        try {
            const count = refresh ? Math.max(1, pagesLoaded) : 1;

            let page = refresh ? 1 : next,
                updated = refresh ? [] : [...rows];

            for (let i = 0; i < count && page; i++) {
                const d = await api(`citas/?pagina=${page}`);
                if (token !== generation) return;

                updated.push(...d.citas);
                page = d.siguiente;
            }

            rows = updated;
            next = page;
            if (!refresh) pagesLoaded++;

            document.querySelector('#appointments-list').innerHTML =
                table(
                    [
                        'Paciente',
                        'Propietario',
                        'Veterinario',
                        'Fecha y hora',
                        'Motivo',
                        'Estado',
                        '',
                    ],
                    appointmentRows(rows),
                ) +
                (next
                    ? '<button class="secondary load-more" id="more-appointments">Cargar más citas</button>'
                    : '');

            bindCitaButtons();
            if (next)
                document.querySelector('#more-appointments').onclick = () =>
                    load().catch((e) => toast(e.message, true));
        } finally {
            busy = false;
        }
    }

    await load();
    if (token !== generation) return;

    pageRefreshTimer = setInterval(() => {
        if (!document.hidden && !modal.open)
            load(true).catch((e) => toast(e.message, true));
    }, 15000);
}

// Muestra los datos y notificaciones de una cita.
async function showCita(id) {
    const d = await api(`citas/${id}/`);
    const c = d.cita;
    openModal(
        'Detalle de cita',
        `<dl class="detail-grid">${Object.entries({
            Mascota: c.mascota,
            Propietario: c.cliente,
            Veterinario: c.veterinario,
            Fecha: c.fecha,
            Hora: c.hora,
            Estado: c.estado,
            Motivo: c.motivo,
            Observaciones: c.observaciones || 'Sin observaciones',
        })
            .map(([k, v]) => `<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`)
            .join(
                '',
            )}</dl><h3>Notificaciones</h3>${d.notificaciones.map((n) => badge(n.estado)).join(' ') || '<p class="muted">Sin notificaciones registradas.</p>'}<div class="form-actions"><button id="edit-cita">Editar / cambiar estado</button></div>`,
    );
    document.querySelector('#edit-cita').onclick = () => {
        modal.close();
        appointmentForm(c).catch((e) => toast(e.message, true));
    };
}

// Prepara el propietario, paciente, profesional y horario para crear o editar una cita.
async function appointmentForm(c = {}) {
    const d = await api('cargar-datos-agenda/');
    vetCache = d.veterinarios;

    app.innerHTML =
        title(
            'CUIDADO SIN CONFUSIONES',
            c.id ? 'Editar cita' : 'Agendar una cita',
            'Primero el propietario, después su mascota y el horario de atención.',
        ) +
        `<form id="appointment" class="panel"><h3>01 · Selecciona el propietario</h3><div class="owner-search"><label>Buscar propietario<input id="owner-search" placeholder="Selecciona o escribe nombre, documento o teléfono" autocomplete="off"></label><div id="owner-results" class="suggestions" hidden></div></div><input type="hidden" name="cliente_id" value="${c.cliente_id || ''}"><p class="helper" id="owner-selected">${esc(c.cliente || 'Ningún propietario seleccionado.')}</p><div class="form-grid" style="margin-top:24px">${select('mascota', '02 · Mascota *', [['', 'Selecciona primero un propietario']], c.mascota_id, 'required')}${select('veterinario', 'Veterinario *', [['', 'Selecciona'], ...vetCache.map((v) => [v.id, `${v.nombre} ${v.apellido} · ${v.especialidad}`])], c.veterinario_id, 'required')}${field('fecha', 'Fecha *', 'date', c.fecha || today(), 'required')}${field('hora', 'Hora *', 'time', c.hora, 'required')}${field('duracion_minutos', 'Duración (minutos) *', 'number', c.duracion_minutos || 30, 'min="5" max="480" required')}${select(
            'estado',
            'Estado *',
            (c.id
                ? ['Programada', 'Atendida', 'Cancelada']
                : ['Programada']
            ).map((v) => [v, v]),
            c.estado || 'Programada',
            'required',
        )}${area('motivo', 'Motivo de consulta *', c.motivo, 'required maxlength="200"')}${area('observaciones', 'Observaciones', c.observaciones)}</div>${submit(c.id ? 'Guardar cambios' : 'Registrar cita')}</form>`;

    let seq = 0;
    // Carga s?lo las mascotas del propietario seleccionado e ignora respuestas antiguas.
    async function chooseOwner(id, label, petId = '') {
        const stamp = ++seq;
        document.querySelector('#appointment [name=cliente_id]').value = id;

        document.querySelector('#owner-selected').textContent = label;
        document.querySelector('#owner-results').innerHTML = '';

        const selector = document.querySelector('#appointment [name=mascota]');
        selector.innerHTML = '<option value="">Cargando mascotas…</option>';
        selector.disabled = true;

        const pets = await api(`clientes/${id}/mascotas/`);
        if (stamp !== seq || !selector.isConnected) return;

        selector.innerHTML =
            '<option value="">Selecciona una mascota</option>' +
            pets.mascotas
                .map(
                    (m) =>
                        `<option value="${m.id}">${esc(m.nombre)} · ${esc(m.especie)} · ${esc(m.raza)} (#${m.id})</option>`,
                )
                .join('');
        selector.disabled = false;
        selector.value = petId;
    }

    bindOwnerSearch(
        document.querySelector('#owner-search'),
        document.querySelector('#owner-results'),
        (owner) => chooseOwner(owner.id, `${owner.nombre} ${owner.apellido}`),
        () => {
            ++seq;

            document.querySelector('#appointment [name=cliente_id]').value = '';
            document.querySelector('#appointment [name=mascota]').innerHTML =
                '<option value="">Selecciona primero un propietario</option>';
            document.querySelector('#owner-selected').textContent =
                'Ningún propietario seleccionado.';
        },
    );

    if (c.cliente_id) await chooseOwner(c.cliente_id, c.cliente, c.mascota_id);

    bindForm(
        'appointment',
        c.id ? `citas/${c.id}/editar/` : 'registrar/cita/',
        (d) => d,
        () => {
            if (location.hash === '#dashboard') navigate();
            else location.hash = 'dashboard';
        },
    );
}

// Combina selecci?n exacta de propietario con b?squeda libre de pacientes.
async function consultar(token) {
    app.innerHTML =
        title(
            'FAMILIAS Y PACIENTES',
            'Clientes y mascotas',
            'Encuentra un paciente, consulta su ficha o añade una mascota a su familia.',
        ) +
        `<section class="panel"><div class="search-row"><div class="owner-search"><label>Buscar<input id="patient-search" placeholder="Selecciona propietario o busca cliente, documento, mascota, teléfono o correo" autocomplete="off"></label><div id="patient-owner-results" class="suggestions" hidden></div></div><button id="search-patients">Buscar</button><button class="secondary" id="search-owners">Ver propietarios</button></div><div id="patients-table" class="loading">Cargando pacientes…</div></section>`;

    let nextPatients = 1,
        selectedOwner = '',
        loadSequence = 0;

    // Solicita y presenta resultados de la secci?n con control de paginaci?n.
    async function load(append = false) {
        const stamp = ++loadSequence,
            q = document.querySelector('#patient-search').value;
        const d = await api(
            `mascotas/?q=${encodeURIComponent(q)}&cliente_id=${selectedOwner}&pagina=${append ? nextPatients : 1}`,
        );
        if (token !== generation || stamp !== loadSequence) return;
        petCache = append ? [...petCache, ...d.mascotas] : d.mascotas;
        nextPatients = d.siguiente;
        const box = document.querySelector('#patients-table');
        if (!box) return;

        box.innerHTML =
            table(
                [
                    'Paciente',
                    'Propietario',
                    'Contacto',
                    'Especie / raza',
                    'Acciones',
                ],
                petCache
                    .map(
                        (m) =>
                            `<tr><td><strong>${esc(m.nombre)}</strong><small>#${m.id}</small></td><td>${esc(m.cliente)}</td><td>${esc(m.telefono)}<small>${esc(m.email)}</small></td><td>${esc(m.especie)}<small>${esc(m.raza)}</small></td><td><div class="actions"><button class="small secondary" data-pet="${m.id}">Ficha / editar</button></div></td></tr>`,
                    )
                    .join(''),
            ) +
            (nextPatients
                ? '<button class="secondary load-more" id="more-patients">Cargar más pacientes</button>'
                : '');

        if (nextPatients)
            document.querySelector('#more-patients').onclick = () =>
                load(true).catch((e) => toast(e.message, true));

        box.querySelectorAll('[data-pet]').forEach(
            (b) =>
                (b.onclick = () =>
                    editPet(b.dataset.pet).catch((e) =>
                        toast(e.message, true),
                    )),
        );
    }

    document.querySelector('#search-patients').onclick = () =>
        load().catch((e) => toast(e.message, true));

    bindOwnerSearch(
        document.querySelector('#patient-search'),
        document.querySelector('#patient-owner-results'),
        (owner) => {
            selectedOwner = owner.id;
            return load();
        },
        () => {
            selectedOwner = '';
            ++loadSequence;
        },
    );

    document
        .querySelector('#patient-search')
        .addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.defaultPrevented) {
                event.preventDefault();
                load().catch((e) => toast(e.message, true));
            }
        });

    document.querySelector('#search-owners').onclick = async () => {
        try {
            const d = await api(
                `clientes/?q=${encodeURIComponent(document.querySelector('#patient-search').value)}`,
            );
            openModal(
                'Propietarios registrados',
                table(
                    ['Nombre', 'Documento', 'Teléfono', ''],
                    d.clientes
                        .map(
                            (c) =>
                                `<tr><td>${esc(c.nombre)} ${esc(c.apellido)}</td><td>${esc(c.documento)}</td><td>${esc(c.telefono)}</td><td><button class="small secondary" data-owner-edit="${c.id}">Editar</button><button class="small" data-add="${c.id}">＋ Mascota</button></td></tr>`,
                        )
                        .join(''),
                ),
            );
            modal
                .querySelectorAll('[data-add]')
                .forEach(
                    (b) => (b.onclick = () => addExistingPet(b.dataset.add)),
                );
            modal
                .querySelectorAll('[data-owner-edit]')
                .forEach(
                    (b) =>
                        (b.onclick = () =>
                            editOwner(
                                d.clientes.find(
                                    (c) => String(c.id) === b.dataset.ownerEdit,
                                ),
                            )),
                );
        } catch (e) {
            toast(e.message, true);
        }
    };

    await load();
}

// Registra otro paciente para un cliente existente.
function addExistingPet(id) {
    openModal(
        'Agregar mascota a este propietario',
        `<form id="extra-pet"><div class="form-grid">${petFields()}</div>${submit('Registrar mascota')}</form>`,
    );
    bindForm(
        'extra-pet',
        `clientes/${id}/agregar-mascota/`,
        (d) => d,
        () => {
            modal.close();
            navigate();
        },
    );
}

// Edita propietario y mascota conservando sus relaciones.
async function editPet(id) {
    const d = await api(`detalle-mascota/${id}/`);
    const m = d.mascota,
        c = d.cliente;

    openModal(
        'Ficha de cliente y mascota',
        `<form id="edit-pet"><input type="hidden" name="mascotaId" value="${m.id}"><input type="hidden" name="clienteId" value="${c.id}"><h3>Propietario</h3><div class="form-grid">${ownerFields(c)}${select(
            'estado',
            'Estado del propietario',
            [
                ['Activo', 'Activo'],
                ['Inactivo', 'Inactivo'],
            ],
            c.estado,
        )}</div><h3 style="margin-top:25px">Paciente #${m.id}</h3><div class="form-grid">${petFields(m, true)}</div>${submit('Actualizar registro')}</form><div class="form-actions"><button class="secondary" id="add-existing">＋ Otra mascota</button><button class="danger" id="delete-pet">Eliminar mascota</button></div>`,
    );

    bindForm(
        'edit-pet',
        'editar-registro/',
        (d) => d,
        () => {
            modal.close();
            navigate();
        },
    );
    document.querySelector('#add-existing').onclick = () =>
        addExistingPet(c.id);

    document.querySelector('#delete-pet').onclick = () => {
        if (
            !confirm(
                `¿Eliminar a ${m.nombre}? Solo se permite si no tiene historial clínico.`,
            )
        )
            return;
        openModal(
            'Confirmar eliminación',
            `<form id="delete-confirm"><p>Se eliminará la mascota <strong>${esc(m.nombre)}</strong>. Su propietario se conservará.</p>${submit('Confirmar eliminación')}</form>`,
        );
        bindForm(
            'delete-confirm',
            `eliminar-registro/${m.id}/`,
            () => ({}),
            () => {
                modal.close();
                navigate();
            },
            'DELETE',
        );
    };
}

// Lista y administra profesionales de la cl?nica.
async function veterinarios(token) {
    const d = await api('cargar-datos-agenda/');
    if (token !== generation) return;
    vetCache = d.veterinarios;
    app.innerHTML =
        title(
            'EQUIPO CLÍNICO',
            'Nuestros veterinarios',
            'Mantén actualizados los profesionales y sus especialidades.',
            `<button id="new-vet">＋ Registrar veterinario</button>`,
        ) +
        `<section class="panel">${table(['Profesional', 'Especialidad', 'Teléfono', ''], vetCache.map((v) => `<tr><td><strong>${esc(v.nombre)} ${esc(v.apellido)}</strong></td><td>${esc(v.especialidad)}</td><td>${esc(v.telefono)}</td><td><button class="small secondary" data-vet="${v.id}">Editar</button></td></tr>`).join(''))}</section>`;

    // Prepara el formulario del veterinario y su eliminaci?n protegida.
    function edit(v = {}) {
        openModal(
            'Datos del veterinario',
            `<form id="vet-form"><input type="hidden" name="id" value="${v.id || ''}"><div class="form-grid">${field('nombre', 'Nombres *', 'text', v.nombre, 'required maxlength="50"')}${field('apellido', 'Apellidos *', 'text', v.apellido, 'required maxlength="50"')}${field('telefono', 'Teléfono *', 'tel', v.telefono, 'required maxlength="20"')}${field('especialidad', 'Especialidad *', 'text', v.especialidad, 'required maxlength="100"')}</div>${submit()}</form>`,
        );
        bindForm(
            'vet-form',
            'veterinarios/guardar/',
            (d) => d,
            () => {
                modal.close();
                navigate();
            },
        );
        if (v.id) {
            document
                .querySelector('#modal-content')
                .insertAdjacentHTML(
                    'beforeend',
                    `<form id="delete-vet"><p class="helper">Solo se elimina un profesional sin citas registradas.</p>${submit('Eliminar veterinario sin citas')}</form>`,
                );
            bindForm(
                'delete-vet',
                `veterinarios/${v.id}/`,
                () => ({}),
                () => {
                    modal.close();
                    navigate();
                },
                'DELETE',
            );
        }
    }

    document.querySelector('#new-vet').onclick = () => edit();
    app.querySelectorAll('[data-vet]').forEach(
        (b) =>
            (b.onclick = () =>
                edit(vetCache.find((v) => String(v.id) === b.dataset.vet))),
    );
}

// Selecciona el paciente cuyo historial se consultar?.
async function vacunacion(token) {
    const d = await api('mascotas-selector/');
    if (token !== generation) return;
    petCache = d.mascotas;

    app.innerHTML =
        title(
            'CUIDADO CONTINUO',
            'Salud e historial',
            'Vacunas, tratamientos y seguimiento por paciente.',
        ) +
        `<section class="panel">${select('paciente', 'Selecciona un paciente', [['', 'Selecciona'], ...petCache.map((m) => [m.id, `${m.nombre} · ${m.cliente} (#${m.id})`])])}</section><div id="health-content"></div>`;

    document.querySelector('[name=paciente]').onchange = (event) =>
        loadHealth(event.target.value).catch((e) => toast(e.message, true));
}

// Carga vacunas, tratamientos y citas del paciente seleccionado.
async function loadHealth(id) {
    const box = document.querySelector('#health-content');
    if (!id) {
        box.innerHTML = '';
        return;
    }
    box.innerHTML = '<div class="loading">Cargando historial…</div>';

    const [v, t, c] = await Promise.all([
        api(`vacunas-mascota/${id}/`),
        api(`tratamientos-mascota/${id}/`),
        api(`citas-mascota/${id}/`),
    ]);

    if (document.querySelector('[name=paciente]')?.value !== String(id)) return;

    box.innerHTML = `<section class="panel"><div class="panel-head"><h2>Vacunación</h2><button id="new-vaccine">＋ Registrar vacuna</button></div>${table(['Vacuna', 'Aplicación', 'Vencimiento', 'Lote', 'Estado'], v.vacunas.map((v) => `<tr><td>${esc(v.nombre)}</td><td>${v.fecha_aplicacion}</td><td>${v.fecha_vencimiento}</td><td>${esc(v.lote)}</td><td>${badge(v.dias_para_vencer < 0 ? 'vencida' : 'Vigente')}</td></tr>`).join(''))}</section><section class="panel"><div class="panel-head"><h2>Tratamientos</h2><button id="new-treatment">＋ Registrar tratamiento</button></div>${table(['Descripción', 'Medicamento', 'Dosis', 'Duración', 'Inicio / cita'], t.tratamientos.map((t) => `<tr><td>${esc(t.descripcion)}</td><td>${esc(t.medicamento)}</td><td>${esc(t.dosis)}</td><td>${esc(t.duracion)}</td><td>${t.fecha_inicio}<small>${esc(t.cita_motivo)}</small></td></tr>`).join(''))}</section>`;

    document.querySelector('#new-vaccine').onclick = () => {
        openModal(
            'Registrar vacuna',
            `<form id="vaccine"><input type="hidden" name="mascota_id" value="${id}"><div class="form-grid">${field('nombre_vacuna', 'Vacuna *', 'text', '', 'required maxlength="100"')}${field('lote', 'Lote *', 'text', '', 'required maxlength="50"')}${field('fecha_aplicacion', 'Aplicación *', 'date', today(), 'required')}${field('fecha_vencimiento', 'Vencimiento *', 'date', '', 'required')}</div>${submit('Registrar vacuna')}</form>`,
        );
        bindForm(
            'vaccine',
            'registrar-vacuna/',
            (d) => d,
            () => {
                modal.close();
                loadHealth(id);
            },
        );
    };

    document.querySelector('#new-treatment').onclick = () => {
        openModal(
            'Registrar tratamiento',
            `<form id="treatment"><div class="form-grid">${select('cita_id', 'Cita del paciente *', [['', 'Selecciona'], ...c.citas.map((c) => [c.id, `${c.fecha} · ${c.hora} · ${c.motivo}`])], '', 'required')}${field('fecha_inicio', 'Inicio *', 'date', today(), 'required')}${field('descripcion', 'Descripción *', 'text', '', 'required maxlength="200"')}${field('medicamento', 'Medicamento *', 'text', '', 'required maxlength="100"')}${field('dosis', 'Dosis *', 'text', '', 'required maxlength="50"')}${field('duracion', 'Duración *', 'text', '', 'required maxlength="50"')}</div>${submit('Registrar tratamiento')}</form>`,
        );
        bindForm(
            'treatment',
            'registrar-tratamiento/',
            (d) => d,
            () => {
                modal.close();
                loadHealth(id);
            },
        );
    };
}

// Presenta totales y documentos con sus filtros.
async function reportes(token) {
    const [r, f] = await Promise.all([
        api('resumen-facturas/'),
        api('listar-facturas/?pagina=1'),
    ]);
    if (token !== generation) return;
    const s = r.resumen;
    let invoices = f.facturas,
        nextInvoices = f.siguiente;

    app.innerHTML =
        title(
            'FINANZAS DE TU CLÍNICA',
            'Facturas y reportes',
            'Documentos de gestión interna y seguimiento de pagos.',
            `<button id="new-invoice">＋ Nueva factura</button>`,
        ) +
        `<div class="stats"><article class="stat"><small>Ingresos cobrados</small><strong style="font-size:24px">${cop(s.total_ingresos)}</strong></article><article class="stat"><small>Por cobrar</small><strong style="font-size:24px">${cop(s.total_pendiente)}</strong></article><article class="stat"><small>Facturas registradas</small><strong>${s.total_facturas}</strong></article><article class="stat"><small>Facturas pagadas</small><strong>${s.facturas_pagadas}</strong></article></div><section class="panel"><div class="panel-head"><h2>Registro de facturas</h2>${select('filtro', 'Estado', [['', 'Todos'], ...['Pendiente', 'Pagada', 'Cancelada'].map((v) => [v, v])])}</div><div id="invoices-table"></div><p class="helper">Estos documentos no constituyen facturas electrónicas autorizadas por la DIAN.</p></section>`;

    // Filtra y pagina facturas conservando las filas anteriores al cargar m?s.
    async function loadInvoices(append = false) {
        const state = document.querySelector('[name=filtro]').value;
        const d = await api(
            `listar-facturas/?pagina=${append ? nextInvoices : 1}&estado=${encodeURIComponent(state)}`,
        );
        if (token !== generation) return;
        invoices = append ? [...invoices, ...d.facturas] : d.facturas;
        nextInvoices = d.siguiente;
        rows();
    }

    // Actualiza la tabla de facturas y sus acciones.
    function rows() {
        document.querySelector('#invoices-table').innerHTML =
            table(
                [
                    'Factura',
                    'Emisión',
                    'Cliente',
                    'Concepto',
                    'Total',
                    'Estado',
                    '',
                ],
                invoices
                    .map(
                        (f) =>
                            `<tr><td><strong>F${String(f.id).padStart(6, '0')}</strong></td><td>${f.fecha}</td><td>${esc(f.cliente)}</td><td>${esc(f.cita_motivo)}</td><td>${cop(f.monto)}</td><td>${badge(f.estado)}</td><td><div class="actions"><a class="badge" href="${f.pdf_url}">↓ PDF</a><button class="small secondary" data-invoice="${f.id}">Detalle</button></div></td></tr>`,
                    )
                    .join(''),
            ) +
            (nextInvoices
                ? '<button class="secondary load-more" id="more-invoices">Cargar más facturas</button>'
                : '');
        document
            .querySelectorAll('[data-invoice]')
            .forEach(
                (b) =>
                    (b.onclick = () =>
                        showInvoice(b.dataset.invoice).catch((e) =>
                            toast(e.message, true),
                        )),
            );
        if (nextInvoices)
            document.querySelector('#more-invoices').onclick = () =>
                loadInvoices(true).catch((e) => toast(e.message, true));
    }

    rows();
    document.querySelector('[name=filtro]').onchange = () =>
        loadInvoices().catch((e) => toast(e.message, true));
    document.querySelector('#new-invoice').onclick = () =>
        newInvoice().catch((e) => toast(e.message, true));
}

// A?ade una l?nea de servicio a la factura.
function addService() {
    document
        .querySelector('#services')
        .insertAdjacentHTML(
            'beforeend',
            `<div class="service-row">${field('servicio', 'Servicio *', 'text', '', 'required maxlength="200"')}${field('cantidad', 'Cantidad *', 'number', '1', 'min="1" step="1" max="10000" required')}${field('precio_unitario', 'Precio COP *', 'number', '', 'min="0" step="0.01" required')}<button type="button" class="ghost" data-service-remove aria-label="Quitar servicio">×</button></div>`,
        );
}

// Muestra la estimaci?n de subtotal, descuentos e impuestos.
function updateTotal() {
    const form = document.querySelector('#invoice-form');
    if (!form) return;
    let total = 0;
    form.querySelectorAll('.service-row').forEach(
        (row) =>
            (total +=
                Number(row.querySelector('[name=cantidad]').value) *
                Number(row.querySelector('[name=precio_unitario]').value)),
    );
    total -= Number(form.querySelector('[name=descuento]').value);
    total += Number(form.querySelector('[name=impuesto]').value);
    document.querySelector('#invoice-total').textContent = cop(total);
}

// Reutiliza las tres opciones v?lidas de m?todo de pago.
function paymentMethodField(value = 'Transferencia') {
    return select(
        'metodo_pago',
        'Método de pago *',
        ['Transferencia', 'Efectivo', 'Tarjeta'].map((v) => [v, v]),
        value,
        'required',
    );
}

// Registra una factura con sus servicios, cliente y cita.
async function newInvoice() {
    const d = await api('datos-factura/');
    invoiceAppointments = d.citas;

    openModal(
        'Nueva factura',
        `<form id="invoice-form"><div class="form-grid">${select('cita_id', 'Cita / cliente / paciente *', [['', 'Selecciona'], ...d.citas.map((c) => [c.id, `${c.fecha} · ${c.hora} · ${c.cliente_nombre} · ${c.mascota} (#C${c.id})`])], '', 'required')}${select(
            'estado_pago',
            'Estado de pago',
            [
                ['Pendiente', 'Pendiente'],
                ['Pagada', 'Pagada'],
            ],
        )}</div><div id="services"></div><button type="button" class="secondary small" id="add-service">＋ Agregar servicio</button><div class="form-grid" style="margin-top:22px">${field('descuento', 'Descuento (COP)', 'number', '0', 'min="0" step="0.01" required')}${field('impuesto', 'Impuesto registrado (COP)', 'number', '0', 'min="0" step="0.01" required')}${paymentMethodField()}</div><div id="invoice-total" class="invoice-summary"></div><p class="helper">Los importes se validan y calculan en el servidor. Documento de gestión interna.</p>${submit('Registrar factura')}</form>`,
    );

    addService();
    updateTotal();
    document.querySelector('#add-service').onclick = addService;
    document.querySelector('#invoice-form').oninput = updateTotal;

    bindForm(
        'invoice-form',
        'registrar-factura/',
        (data, form) => {
            const c = invoiceAppointments.find(
                (c) => String(c.id) === data.cita_id,
            );

            if (!c) throw new Error('Selecciona la cita.');

            const servicios = [...form.querySelectorAll('.service-row')].map(
                (row) =>
                    Object.fromEntries(
                        [...row.querySelectorAll('[name]')].map((i) => [
                            i.name,
                            i.value,
                        ]),
                    ),
            );

            return {
                cita_id: c.id,
                cliente_id: c.cliente_id,
                servicios,
                descuento: data.descuento,
                impuesto: data.impuesto,
                metodo_pago: data.metodo_pago,
                estado_pago: data.estado_pago,
            };
        },
        (result) => {
            openModal(
                'Factura registrada',
                `<p>Se guardó la factura <strong>F${String(result.id).padStart(6, '0')}</strong> por ${cop(result.monto_total)}.</p><a class="badge" href="${result.pdf_url}">↓ Descargar factura PDF</a><p class="helper">También podrás descargarla desde el listado.</p>`,
            );
            navigate();
        },
    );
}

// Consulta el desglose, descarga PDF y actualiza pago.
async function showInvoice(id) {
    const { detalle: d } = await api(`detalle-factura/${id}/`);
    openModal(
        `Factura F${String(d.id).padStart(6, '0')}`,
        `<p><strong>${esc(d.cliente_nombre)}</strong> · ${esc(d.mascota_nombre)}</p>${table(['Servicio', 'Cant.', 'Precio', 'Total'], d.servicios.map((s) => `<tr><td>${esc(s.servicio)}</td><td>${s.cantidad}</td><td>${cop(s.precio_unitario)}</td><td>${cop(s.total)}</td></tr>`).join(''), 'Factura histórica sin desglose de servicios.')}<p class="invoice-summary">Total: ${cop(d.monto_total)}</p><a class="badge" href="${d.pdf_url}">↓ Descargar factura PDF</a><form id="invoice-state" style="margin-top:24px"><input type="hidden" name="factura_id" value="${d.id}">${select(
            'estado_pago',
            'Actualizar estado',
            ['Pendiente', 'Pagada', 'Cancelada'].map((v) => [v, v]),
            d.estado_pago,
        )}${paymentMethodField(d.metodo_pago)}${submit('Actualizar estado')}</form>`,
    );
    bindForm(
        'invoice-state',
        'actualizar-estado-factura/',
        (d) => d,
        () => {
            modal.close();
            navigate();
        },
    );
}

// Procesa pendientes sin un worker local y muestra errores de la configuración desplegada.
async function correos(token) {
    const d = await api('notificaciones/');
    if (token !== generation) return;
    app.innerHTML =
        title(
            'COMUNICACIÓN CON LAS FAMILIAS',
            'Notificaciones por correo',
            'Los correos se envían en una petición separada después de guardar la cita.',
        ) +
        `<section class="panel"><div class="panel-head"><h2>Últimas notificaciones</h2><div class="actions"><button id="process-mail" ${!d.correo?.configurada || !d.pendientes ? 'disabled' : ''}>Procesar pendientes</button><button class="secondary" id="refresh-mail">Actualizar</button></div></div><p class="helper" id="mail-status" role="status">${esc(d.correo?.diagnostico || '')}</p>${table(['Cita', 'Creada', 'Estado', 'Intentos', 'Diagnóstico', ''], d.notificaciones.map((n) => `<tr><td>#C${n.cita_id}</td><td>${esc(n.creada)}</td><td>${badge(n.estado)}</td><td>${n.intentos}</td><td>${esc(n.error || '—')}</td><td>${n.estado === 'Fallida' ? `<form id="retry-${n.id}">${submit('Reintentar')}</form>` : ''}</td></tr>`).join(''))}<p class="helper">Los mensajes “Sin correo” y “Demostración” no se envían. Los fallidos pueden reintentarse después de corregir la configuración.</p></section>`;
    document.querySelector('#refresh-mail').onclick = navigate;
    async function process() {
        const button = document.querySelector('#process-mail');
        button.disabled = true;
        button.textContent = 'Procesando…';
        try {
            await processMailQueue();
            if (token === generation) await navigate();
        } catch (error) {
            if (token === generation) {
                document.querySelector('#mail-status').textContent = error.message;
            }
        } finally {
            if (button.isConnected) {
                button.disabled = false;
                button.textContent = 'Procesar pendientes';
            }
        }
    }
    document.querySelector('#process-mail').onclick = process;
    d.notificaciones
        .filter((n) => n.estado === 'Fallida')
        .forEach((n) =>
            bindForm(
                `retry-${n.id}`,
                `notificaciones/${n.id}/reintentar/`,
                () => ({}),
                navigate,
            ),
        );
    pageRefreshTimer = setInterval(() => {
        if (!document.hidden && !mailProcessing && !modal.open) navigate();
    }, 15000);
    if (d.correo?.configurada && d.pendientes) process();
}

const pages = {
    dashboard,
    registrar,
    agendar: () => appointmentForm(),
    consultar,
    citas,
    veterinarios,
    vacunacion,
    reportes,
    correos,
};

// Cambia de pesta?a, cancela temporizadores y descarta respuestas obsoletas.
async function navigate() {
    clearInterval(pageRefreshTimer);
    ownerSearchCleanup();
    const page = location.hash.slice(1) || 'dashboard';
    const fn = pages[page] || dashboard;
    const token = ++generation;
    document.querySelectorAll('[data-nav]').forEach((a) => {
        a.classList.toggle('active', a.dataset.nav === page);
        a.setAttribute(
            'aria-current',
            a.dataset.nav === page ? 'page' : 'false',
        );
    });
    app.innerHTML = '<div class="loading">Cargando información…</div>';
    try {
        await fn(token);
    } catch (e) {
        if (token === generation) {
            app.innerHTML =
                '<section class="panel"><h2>No se pudo cargar esta sección</h2><p class="muted"></p><button onclick="navigate()">Volver a intentar</button></section>';
            app.querySelector('p').textContent = e.message;
        }
    }
}

window.addEventListener('hashchange', navigate);

window.addEventListener('online', () =>
    toast('Conexión restablecida. Puedes volver a intentar.'),
);

navigate();
