// Cat?logo y encuesta de adopci?n para visitantes.
'use strict';

const escapeText = (v) =>
    String(v ?? '').replace(
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

const cards = document.querySelector('#adoption-cards'),
    dialog = document.querySelector('#application');

let pets = [],
    nextPage = null,
    catalogSequence = 0;

// Presenta un aviso p?blico sin datos internos.
function message(text) {
    const box = document.querySelector('#public-toast');
    box.textContent = text;
    box.style.display = 'block';
    setTimeout(() => (box.style.display = 'none'), 7000);
}

// Consulta la API p?blica y transforma errores en mensajes comprensibles.
async function request(path, options = {}) {
    const r = await fetch('/adopciones/api/' + path, {
        credentials: 'same-origin',
        ...options,
    });
    let d;
    try {
        d = await r.json();
    } catch {
        throw new Error(
            'No se pudo leer la respuesta. Conservamos tus datos; intenta de nuevo.',
        );
    }
    if (!r.ok)
        throw new Error(d.message || 'No se pudo completar la solicitud.');
    return d;
}

// Busca y pagina mascotas disponibles.
async function load(more = false) {
    const seq = ++catalogSequence;
    const form = document.querySelector('#catalog-search'),
        params = new URLSearchParams(new FormData(form));
    params.set('pagina', more ? nextPage : 1);
    try {
        const d = await request('catalogo/?' + params);
        if (seq !== catalogSequence) return;
        pets = more ? [...pets, ...d.mascotas] : d.mascotas;
        nextPage = d.siguiente;
        cards.innerHTML =
            pets
                .map(
                    (p) =>
                        `<article class="adoption-card"><div class="adoption-photo">${p.fotografia ? `<img src="${p.fotografia}" alt="${escapeText(p.nombre)}" loading="lazy" decoding="async" width="400" height="280">` : '🐾'}<span class="badge">${escapeText(p.estado)}</span></div><div class="adoption-body"><h3>${escapeText(p.nombre)}</h3><div class="pet-meta">${escapeText(p.especie)} · ${escapeText(p.raza || 'Raza no indicada')} · ${escapeText(p.edad_aproximada)}</div><p>${escapeText(p.descripcion.slice(0, 170))}</p><button data-adopt="${p.id}" ${p.estado !== 'Disponible' ? 'disabled' : ''}>${p.estado === 'Disponible' ? 'Realizar encuesta' : 'En proceso de revisión'}</button></div></article>`,
                )
                .join('') ||
            '<div class="panel empty full"><span>🐾</span><h3>Pronto habrá nuevas historias.</h3><p>No hay mascotas disponibles con estos filtros.</p></div>';
        document.querySelector('#catalog-more').hidden = !nextPage;
        cards
            .querySelectorAll('[data-adopt]')
            .forEach(
                (b) =>
                    (b.onclick = () =>
                        start(
                            pets.find((p) => p.id === Number(b.dataset.adopt)),
                        ).catch((e) => message(e.message))),
            );
    } catch (e) {
        message(e.message);
    }
}

document.querySelector('#catalog-search').onsubmit = (e) => {
    e.preventDefault();
    load();
};
document.querySelector('#catalog-more').onclick = () => load(true);
document.querySelector('#application-close').onclick = () => dialog.close();

// Construye los datos personales requeridos de la solicitud.
function input(name, label, type = 'text', extra = '') {
    return `<label>${label}<input name="${name}" type="${type}" ${extra} required></label>`;
}

// Prepara los pasos de la encuesta para la mascota elegida.
async function start(p) {
    const q = await request('cuestionario/');
    const content = document.querySelector('#application-content');
    let step = 0,
        busy = false;
    const n = q.criterios.length + 1;

    content.innerHTML = `<div class="step-count" id="step-count"></div><div class="questionnaire-progress"><div id="question-progress"></div></div><form id="adopt-form"><section class="questionnaire-step" data-step="0"><h3>Un hogar para ${escapeText(p.nombre)}</h3><p class="helper">${escapeText(p.personalidad)} · Salud: ${escapeText(p.salud)} · Vacunación: ${escapeText(p.vacunacion)} · Necesidades: ${escapeText(p.necesidades || 'Sin necesidades especiales indicadas')}.</p><p>Estos datos solo serán visibles para el equipo encargado. La encuesta no autoriza una entrega por sí sola.</p><div class="form-grid">${input('nombre', 'Nombre completo', 'text', 'maxlength="150" autocomplete="name"')}${input('documento', 'Documento de identificación', 'text', 'maxlength="30"')}${input('edad', 'Edad (años)', 'number', 'min="18" max="120"')}${input('telefono', 'Teléfono', 'tel', 'maxlength="30"')}${input('email', 'Correo electrónico', 'email', 'maxlength="254"')}${input('direccion', 'Dirección', 'text', 'maxlength="200"')}${input('ocupacion', 'Ocupación', 'text', 'maxlength="100"')}${input('presupuesto_cop', 'Presupuesto mensual para cuidado (COP)', 'number', 'min="0" max="2147483647" step="1"')}<label>Tipo de vivienda<select name="tipo_vivienda" required><option>Casa</option><option>Apartamento</option><option>Otra vivienda con condiciones adecuadas</option></select></label><label>Tenencia de vivienda<select name="tenencia_vivienda" required><option>Propia</option><option>Familiar</option><option>Arrendada</option></select></label><label>Ingreso mensual aproximado (opcional)<select name="ingreso_aproximado"><option value="">Prefiero no indicarlo</option><option>Menos de $1.000.000 COP</option><option>Entre $1.000.000 y $2.000.000 COP</option><option>Entre $2.000.001 y $4.000.000 COP</option><option>Más de $4.000.000 COP</option><option>Recursos compartidos o apoyo familiar</option></select></label></div><p class="helper">El ingreso, trabajar, ser principiante o vivir en apartamento no producen rechazo automático. Evaluamos tu plan real de cuidado.</p><label class="answer-option"><input type="checkbox" name="consentimiento" required>Autorizo al equipo VetCare a usar estos datos para evaluar y dar seguimiento a esta solicitud de adopción.</label></section>${q.criterios.map((c, i) => `<section class="questionnaire-step" data-step="${i + 1}" hidden><h3>${i + 1}. ${escapeText(c.nombre)}</h3><p class="helper">Responde según tu situación actual y el apoyo con el que cuentas. Peso del criterio: ${c.peso} puntos.</p>${c.preguntas.map((p) => `<fieldset class="question-block"><legend>${escapeText(p.texto)}</legend>${p.opciones.map((o) => `<label class="answer-option"><input type="radio" name="question-${p.id}" value="${o.id}" required>${escapeText(o.texto)}</label>`).join('')}</fieldset>`).join('')}</section>`).join('')}<div id="adoption-error" class="form-error" role="alert"></div><div class="questionnaire-actions"><button type="button" class="secondary" id="previous">Anterior</button><button type="button" id="next">Continuar →</button><button type="submit" id="send-application" hidden>Enviar evaluación</button></div></form>`;

    const form = document.querySelector('#adopt-form');
    form.noValidate = true;

    // Actualiza el paso visible y sus controles de avance.
    function show() {
        content
            .querySelectorAll('.questionnaire-step')
            .forEach((node, i) => (node.hidden = i !== step));
        document.querySelector('#step-count').textContent =
            `Paso ${step + 1} de ${n} · ${escapeText(p.nombre)}`;
        document.querySelector('#question-progress').style.transform =
            `scaleX(${(step + 1) / n})`;
        document.querySelector('#previous').disabled = step === 0;
        document.querySelector('#next').hidden = step === n - 1;
        document.querySelector('#send-application').hidden = step !== n - 1;
        dialog.scrollTop = 0;
    }

    // Valida los campos del paso actual antes de continuar.
    function valid() {
        const current = content.querySelector(`[data-step="${step}"]`);
        for (const item of current.querySelectorAll('input,select')) {
            if (!item.reportValidity()) return false;
        }
        return true;
    }

    document.querySelector('#previous').onclick = () => {
        if (!busy) {
            step--;
            show();
        }
    };
    document.querySelector('#next').onclick = () => {
        if (!busy && valid()) {
            step++;
            show();
        }
    };

    form.onsubmit = async (event) => {
        event.preventDefault();
        if (busy || !valid()) return;
        if (step < n - 1) {
            step++;
            show();
            return;
        }
        busy = true;
        const buttons = [...form.querySelectorAll('button')];
        buttons.forEach((b) => (b.disabled = true));
        const send = document.querySelector('#send-application');
        send.textContent = 'Evaluando y guardando…';
        document.querySelector('#adoption-error').textContent = '';

        try {
            const data = Object.fromEntries(new FormData(form));
            const respuestas = {};
            Object.keys(data)
                .filter((k) => k.startsWith('question-'))
                .forEach((k) => {
                    respuestas[k.slice(9)] = data[k];
                    delete data[k];
                });
            data.consentimiento = !!data.consentimiento;
            const payload = JSON.stringify({
                solicitante: data,
                respuestas,
                cuestionario: q.id,
            });
            const digest = await crypto.subtle.digest(
                'SHA-256',
                new TextEncoder().encode(payload),
            );
            const sk =
                'adoption:' +
                p.id +
                ':' +
                Array.from(new Uint8Array(digest), (b) =>
                    b.toString(16).padStart(2, '0'),
                ).join('');
            let key = sessionStorage.getItem(sk);
            if (!key) {
                key = crypto.randomUUID();
                sessionStorage.setItem(sk, key);
            }
            const csrf = decodeURIComponent(
                document.cookie
                    .split('; ')
                    .find((s) => s.startsWith('csrftoken='))
                    ?.split('=')
                    .slice(1)
                    .join('=') || '',
            );
            const result = await request(`mascotas/${p.id}/solicitar/`, {
                method: 'POST',
                body: payload,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf,
                    'Idempotency-Key': key,
                },
            });
            location.href = result.resultado.url;
        } catch (e) {
            document.querySelector('#adoption-error').textContent = e.message;
            busy = false;
            buttons.forEach((b) => (b.disabled = false));
            send.textContent = 'Enviar evaluación';
            show();
        }
    };
    show();
    dialog.showModal();
}

// Carga el cat?logo y abre la encuesta indicada en la direcci?n.
async function initialize() {
    await load();

    const selected = new URLSearchParams(location.search).get('mascota');

    if (selected) {
        if (!/^[1-9][0-9]*$/.test(selected)) {
            message(
                'Selecciona una mascota disponible para realizar la encuesta.',
            );
            return;
        }

        try {
            const d = await request('mascotas/' + selected + '/');
            await start(d.mascota);
        } catch (error) {
            message(error.message);
        }
    }
}

initialize();
