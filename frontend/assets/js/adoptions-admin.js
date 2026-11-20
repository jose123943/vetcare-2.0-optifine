// Permite al equipo gestionar mascotas en adopción, solicitudes y entregas.
'use strict';

let adoptionPets = [],
    applicationPage = 1,
    petPage = 1;

// Administra fichas, solicitudes y entregas desde el dashboard.
async function adoptionAdmin(token) {
    app.innerHTML =
        title(
            'VETCARE 2.0 · NUEVAS OPORTUNIDADES',
            'Gestión de adopciones',
            'Cada historia merece un hogar responsable.',
            `<a href="/adopciones/" target="_blank" rel="noopener" class="badge">Ver catálogo ↗</a><a id="open-adoption-survey" class="badge" href="/adopciones/#catalogo" target="_blank" rel="noopener">Realizar encuesta</a><button id="new-adoption-pet">＋ Nueva mascota</button>`,
        ) +
        `<section class="panel"><div class="panel-head"><h2>Compañeros en adopción</h2><button id="weights" class="secondary small">Criterios y pesos</button></div><div id="adoption-admin-pets" class="adoption-management-cards"></div><button id="more-adoption-pets" class="secondary small" hidden>Más mascotas</button></section><section class="panel"><div class="panel-head"><div><h2>Solicitudes e historial de entregas</h2><p>La evaluación aprobada no equivale a una entrega autorizada.</p></div>${select(
            'approved-filter',
            'Evaluación',
            [
                ['', 'Todas'],
                ['true', 'Aprobadas ≥ 67 %'],
                ['false', 'No aprobadas'],
            ],
        )}</div><div id="adoption-applications"></div><button id="more-applications" class="secondary small" hidden>Más solicitudes</button></section>`;

    let applications = [];
    adoptionPets = [];
    petPage = 1;
    applicationPage = 1;

    // Carga una página de mascotas y enlaza edición, fotos y encuesta.
    async function loadPets(append = false) {
        const d = await api(
            `/adopciones/api/admin/mascotas/?pagina=${append ? petPage : 1}`,
        );
        if (token !== generation) return;
        adoptionPets = append ? [...adoptionPets, ...d.mascotas] : d.mascotas;
        petPage = d.siguiente;
        document.querySelector('#more-adoption-pets').hidden = !petPage;
        document.querySelector('#adoption-admin-pets').innerHTML =
            adoptionPets
                .map(
                    (p) =>
                        `<article>${p.fotografia ? `<img loading="lazy" src="${p.fotografia}" alt="${esc(p.nombre)}">` : ''}<div class="panel-head"><h3>${esc(p.nombre)}</h3>${badge(p.estado)}</div><p class="muted">${esc(p.especie)} · ${esc(p.edad_aproximada)}</p><div class="actions">${p.estado === 'Disponible' ? `<a class="badge" data-survey-pet="${p.id}" href="/adopciones/?mascota=${p.id}#encuesta" target="_blank" rel="noopener">Realizar encuesta</a>` : ''}<button class="small secondary" data-adoption-edit="${p.id}">Editar</button><button class="small secondary" data-adoption-photo="${p.id}">Fotografía</button></div></article>`,
                )
                .join('') ||
            '<p class="muted">Registra la primera mascota disponible para adopción.</p>';
        document
            .querySelectorAll('[data-adoption-edit]')
            .forEach(
                (b) =>
                    (b.onclick = () =>
                        editAdoptionPet(
                            adoptionPets.find(
                                (p) => p.id === Number(b.dataset.adoptionEdit),
                            ),
                        )),
            );
        document
            .querySelectorAll('[data-adoption-photo]')
            .forEach(
                (b) =>
                    (b.onclick = () => adoptionPhoto(b.dataset.adoptionPhoto)),
            );
    }

    // Carga solicitudes según el filtro de evaluación.
    async function loadApplications(append = false) {
        const filter = document.querySelector('[name=approved-filter]').value;
        const d = await api(
            `/adopciones/api/admin/solicitudes/?pagina=${append ? applicationPage : 1}&aprobada=${filter}`,
        );
        if (token !== generation) return;
        applications = append
            ? [...applications, ...d.solicitudes]
            : d.solicitudes;
        applicationPage = d.siguiente;
        document.querySelector('#more-applications').hidden = !applicationPage;
        document.querySelector('#adoption-applications').innerHTML = table(
            [
                'Solicitante',
                'Mascota',
                'Puntuación',
                'Evaluación',
                'Entrega / revisión',
                '',
            ],
            applications
                .map(
                    (s) =>
                        `<tr><td><strong>${esc(s.nombre)}</strong><small>Doc. ${esc(s.documento)}</small></td><td>${esc(s.mascota)}</td><td><strong>${esc(s.porcentaje)} %</strong></td><td>${badge(s.aprobada ? 'Aprobada' : 'No aprobada')}${s.revisar ? '<small>⚑ Revisar bienestar</small>' : ''}</td><td>${badge(s.estado)}</td><td><button class="small secondary" data-application="${s.id}">Revisar</button></td></tr>`,
                )
                .join(''),
        );
        document
            .querySelectorAll('[data-application]')
            .forEach(
                (b) =>
                    (b.onclick = () =>
                        reviewApplication(b.dataset.application).catch((e) =>
                            toast(e.message, true),
                        )),
            );
    }

    document.querySelector('#new-adoption-pet').onclick = () =>
        editAdoptionPet();
    document.querySelector('#weights').onclick = () =>
        editWeights().catch((e) => toast(e.message, true));
    document.querySelector('#more-adoption-pets').onclick = () =>
        loadPets(true).catch((e) => toast(e.message, true));
    document.querySelector('#more-applications').onclick = () =>
        loadApplications(true).catch((e) => toast(e.message, true));
    document.querySelector('[name=approved-filter]').onchange = () =>
        loadApplications().catch((e) => toast(e.message, true));
    await Promise.all([loadPets(), loadApplications()]);
}

// Crea o edita una ficha pública de adopción.
function editAdoptionPet(p = {}) {
    openModal(
        p.id ? 'Editar mascota de adopción' : 'Registrar mascota de adopción',
        `<form id="adoption-pet-form"><input type="hidden" name="id" value="${p.id || ''}"><div class="form-grid">${field('nombre', 'Nombre *', 'text', p.nombre, 'required maxlength="80"')}${select(
            'especie',
            'Especie *',
            ['Perro', 'Gato', 'Ave', 'Conejo', 'Otro'].map((x) => [x, x]),
            p.especie || 'Perro',
            'required',
        )}${field('raza', 'Raza', 'text', p.raza, 'maxlength="80"')}${select(
            'sexo',
            'Sexo *',
            [
                ['Hembra', 'Hembra'],
                ['Macho', 'Macho'],
                ['Sin determinar', 'Sin determinar'],
            ],
            p.sexo,
            'required',
        )}${field('edad_aproximada', 'Edad aproximada *', 'text', p.edad_aproximada, 'required maxlength="60" placeholder="Ej. 2 años"')}${field('peso', 'Peso (kg) *', 'number', p.peso, 'min="0" max="9999.99" step="0.01" required')}${field('ingreso', 'Fecha de ingreso *', 'date', p.ingreso || today(), 'required')}${select(
            'esterilizada',
            '¿Está esterilizada?',
            [
                ['false', 'No'],
                ['true', 'Sí'],
            ],
            String(!!p.esterilizada),
        )}${select(
            'estado',
            'Disponibilidad',
            p.estado === 'Adoptada'
                ? [['Adoptada', 'Adoptada']]
                : p.estado === 'En proceso'
                  ? [['En proceso', 'En proceso']]
                  : [
                        ['Disponible', 'Disponible'],
                        ['No disponible', 'No disponible'],
                    ],
            p.estado || 'Disponible',
        )}${field('paciente', 'ID del paciente clínico (opcional)', 'number', p.paciente || '', 'min="1"')}${area('descripcion', 'Su historia *', p.descripcion, 'required')}${area('personalidad', 'Personalidad *', p.personalidad, 'required')}${area('salud', 'Estado de salud *', p.salud, 'required')}${area('vacunacion', 'Vacunación *', p.vacunacion, 'required')}${area('necesidades', 'Necesidades especiales', p.necesidades)}</div><p class="helper">La entrega se registra desde una solicitud autorizada. La fotografía se añade después de guardar.</p>${submit('Guardar mascota')}</form>`,
    );

    bindForm(
        'adoption-pet-form',
        '/adopciones/api/admin/mascotas/guardar/',
        (d) => ({ ...d, esterilizada: d.esterilizada === 'true' }),
        (result) => {
            navigate();
            adoptionPhoto(result.mascota.id);
        },
    );
}

// Sube una imagen que el servidor valida y optimiza.
function adoptionPhoto(id) {
    openModal(
        'Fotografía del catálogo',
        `<form id="adoption-photo" enctype="multipart/form-data"><label>Imagen de hasta 5 MB (se optimizará y eliminarán sus metadatos)<input type="file" name="fotografia" accept="image/jpeg,image/png,image/webp" required></label>${submit('Subir fotografía')}</form>`,
    );
    bindForm(
        'adoption-photo',
        `/adopciones/api/admin/mascotas/${id}/foto/`,
        (d) => d,
        () => {
            modal.close();
            navigate();
        },
    );
}

// Consulta respuestas y registra revisión, autorización, rechazo o entrega.
async function reviewApplication(id) {
    const d = await api(`/adopciones/api/admin/solicitudes/${id}/`),
        s = d.solicitud;

    openModal(
        'Evaluación y revisión de entrega',
        `<div class="panel-head"><h3>${esc(s.nombre)} · ${esc(s.mascota)}</h3><strong>${esc(s.porcentaje)} %</strong></div><dl class="detail-grid">${Object.entries(
            {
                Documento: s.documento,
                Edad: s.edad,
                Teléfono: s.telefono,
                Correo: s.email,
                Dirección: s.direccion,
                Ocupación: s.ocupacion,
                Vivienda: s.tipo_vivienda,
                Tenencia: s.tenencia_vivienda,
                'Ingreso orientativo': s.ingreso_aproximado || 'No indicado',
                'Presupuesto COP': cop(s.presupuesto_cop),
            },
        )
            .map(([k, v]) => `<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`)
            .join(
                '',
            )}</dl>${s.alertas.map((a) => `<p class="review-warning">⚑ ${esc(a)}</p>`).join('')}<details class="admin-questions"><summary>Respuestas originales y pesos utilizados</summary>${d.respuestas.map((r) => `<p><strong>${esc(r.pregunta)}</strong><br>${esc(r.respuesta)}<small> · ${esc(r.criterio)} (${r.peso} puntos)</small></p>`).join('')}</details><h3 style="margin-top:22px">Historial de revisión</h3>${d.revisiones.map((r) => `<p>${esc(r.accion)} · ${esc(r.fecha)} · Responsable #${r.responsable_id}<br>${esc(r.notas)}</p>`).join('') || '<p class="muted">Sin revisiones.</p>'}${
            !['Entregada', 'Rechazada'].includes(s.estado)
                ? `<form id="review-adoption" style="margin-top:25px">${select(
                      'accion',
                      'Acción',
                      s.aprobada
                          ? s.estado === 'Autorizada'
                              ? [
                                    [
                                        'Entregar',
                                        'Confirmar entrega definitiva',
                                    ],
                                    ['Rechazar', 'Rechazar y liberar reserva'],
                                ]
                              : [
                                    ['Autorizar', 'Autorizar para entrega'],
                                    ['Rechazar', 'Rechazar solicitud'],
                                ]
                          : [['Rechazar', 'Rechazar solicitud']],
                  )}${area('notas', 'Notas de revisión o datos de entrega *', '', 'required')}<label class="answer-option"><input type="checkbox" name="bienestar_verificado">He revisado las respuestas y las condiciones de bienestar, incluyendo las alertas indicadas.</label>${submit('Confirmar revisión')}</form>`
                : `<p>${badge(s.estado)}</p>`
        }`,
    );

    if (document.querySelector('#review-adoption'))
        bindForm(
            'review-adoption',
            `/adopciones/api/admin/solicitudes/${id}/revisar/`,
            (data, form) => ({
                ...data,
                bienestar_verificado: form.querySelector(
                    '[name=bienestar_verificado]',
                ).checked,
            }),
            () => {
                modal.close();
                navigate();
            },
        );
}

// Prepara una versión nueva del cuestionario con pesos que suman cien.
async function editWeights() {
    const q = await api('/adopciones/api/cuestionario/');
    openModal(
        'Criterios de evaluación',
        `<p>Los cambios crean una versión nueva. Las solicitudes previas conservan sus respuestas y puntuaciones originales. La aprobación sigue siendo desde el 67 %.</p><form id="adoption-weights"><div class="version-weights">${q.criterios.map((c) => field('weight-' + c.id, c.nombre, 'number', c.peso, 'min="1" max="100" required step="1"')).join('')}</div><p class="helper">La suma debe ser exactamente 100. Para editar preguntas y opciones, crea un borrador y abre la sección de Configuración.</p>${select(
            'publicar',
            'Publicación',
            [
                ['true', 'Publicar ahora con estos pesos'],
                ['false', 'Crear borrador para editar preguntas'],
            ],
        )}${submit('Crear versión')}</form><a href="#configuracion" onclick="modal.close()">Administrar preguntas y opciones ↗</a>`,
    );
    bindForm(
        'adoption-weights',
        '/adopciones/api/admin/cuestionario/pesos/',
        (data) => ({
            cuestionario: q.id,
            publicar: data.publicar === 'true',
            pesos: Object.fromEntries(
                q.criterios.map((c) => [c.id, data['weight-' + c.id]]),
            ),
        }),
        () => {
            modal.close();
            navigate();
        },
    );
}

pages.adopciones = adoptionAdmin;

if (location.hash === '#adopciones') navigate();
