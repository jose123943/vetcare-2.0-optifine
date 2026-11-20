// Permite administrar propietarios, cuentas del equipo y versiones de la encuesta.
'use strict';
// Mantiene datos del propietario y protege su historial al eliminar.
function editOwner(c) {
    openModal(
        'Datos del propietario',
        `<form id="owner-edit"><div class="form-grid">${ownerFields(c)}${select(
            'estado',
            'Estado',
            [
                ['Activo', 'Activo'],
                ['Inactivo', 'Inactivo'],
            ],
            c.estado,
        )}</div>${submit('Guardar propietario')}</form><form id="owner-delete"><p class="helper">Solo se elimina un cliente sin mascotas ni facturas. Para conservar su historial puedes marcarlo como inactivo.</p>${submit('Eliminar cliente sin historiales')}</form>`,
    );
    bindForm(
        'owner-edit',
        `/api/clientes/${c.id}`,
        (d) => d,
        () => {
            modal.close();
            navigate();
        },
        'PUT',
    );
    bindForm(
        'owner-delete',
        `/api/clientes/${c.id}`,
        () => ({}),
        () => {
            modal.close();
            navigate();
        },
        'DELETE',
    );
}
// Carga cuestionarios y cuentas según los permisos del usuario.
async function configuration(token) {
    app.innerHTML =
        title(
            'ADMINISTRACIÓN',
            'Configuración',
            'Cuentas de acceso y versiones de la evaluación de adopciones.',
        ) +
        '<section class="panel"><h2>Cuestionarios</h2><p>Las versiones utilizadas conservan sus preguntas y resultados. Crea un borrador desde Gestión de adopciones → Criterios y pesos.</p><div id="versions"></div></section>' +
        (vetcare.user.is_superuser
            ? '<section class="panel"><div class="panel-head"><h2>Cuentas del equipo</h2><button id="new-account">Nueva cuenta</button></div><div id="accounts"></div></section>'
            : '');
    const newAccount = document.querySelector('#new-account');
    if (newAccount) newAccount.onclick = () => editAccount();
    const q = await api('/adopciones/api/admin/cuestionarios/');
    if (token !== generation) return;
    document.querySelector('#versions').innerHTML = table(
        ['Versión', 'Publicación', ''],
        q.cuestionarios
            .map(
                (v) =>
                    `<tr><td>${esc(v.nombre)}</td><td>${badge(v.activa ? 'Activa' : 'Inactiva / borrador')}</td><td><button class="secondary small" data-version="${v.id}">Ver preguntas</button></td></tr>`,
            )
            .join(''),
    );
    document
        .querySelectorAll('[data-version]')
        .forEach(
            (b) =>
                (b.onclick = () =>
                    viewVersion(b.dataset.version).catch((e) =>
                        toast(e.message, true),
                    )),
        );
    app.insertAdjacentHTML(
        'beforeend',
        '<section class="panel"><h2>Antecedentes conservados</h2><p>Consulta registros de adopción anteriores al catálogo actual sin modificar sus evaluaciones originales.</p><button class="secondary" id="historical-adoptions">Consultar historial previo</button><div id="historical-records"></div></section>',
    );
    document.querySelector('#historical-adoptions').onclick = () =>
        historicalAdoptions().catch((e) => toast(e.message, true));
    if (!vetcare.user.is_superuser) return;
    const d = await api('/api/admin/usuarios');
    if (token !== generation) return;
    document.querySelector('#accounts').innerHTML = table(
        ['Usuario', 'Nombre', 'Acceso', ''],
        d.usuarios
            .map(
                (u) =>
                    `<tr><td>${esc(u.username)}</td><td>${esc(u.first_name + ' ' + u.last_name)}</td><td>${badge(u.is_active ? (u.is_superuser ? 'Superadministrador' : u.is_staff ? 'Administración' : 'Sin acceso') : 'Inactivo')}</td><td><button class="secondary small" data-account="${u.id}">Editar</button></td></tr>`,
            )
            .join(''),
    );
    document.querySelector('#new-account').onclick = () => editAccount();
    document
        .querySelectorAll('[data-account]')
        .forEach(
            (b) =>
                (b.onclick = () =>
                    editAccount(
                        d.usuarios.find(
                            (u) => u.id === Number(b.dataset.account),
                        ),
                    )),
        );
}
// Consulta antecedentes sin recalcular puntuaciones antiguas.
async function historicalAdoptions() {
    const d = await api('/api/admin/historico/adopciones');
    document.querySelector('#historical-records').innerHTML = table(
        ['Registro', 'Mascota', 'Estado', 'Fecha', ''],
        d.adopciones
            .map(
                (a) =>
                    `<tr><td>#${a.id}</td><td>${esc(a.mascota)}</td><td>${badge(a.estado)}</td><td>${esc(a.fecha_registro)}</td><td><button class="secondary small" data-history="${a.id}">Ver detalle</button></td></tr>`,
            )
            .join(''),
    );
    document.querySelectorAll('[data-history]').forEach(
        (b) =>
            (b.onclick = async () => {
                try {
                    const r = await api(
                            '/api/admin/historico/adopciones/' +
                                b.dataset.history,
                        ),
                        a = r.adopcion;
                    openModal(
                        'Antecedente #' + a.id,
                        `<p>${esc(a.motivo)}</p><p>${esc(a.observaciones)}</p><p>${esc(a.observaciones_adopcion)}</p>${table(['Evaluación', 'Versión original', 'Puntuación', 'Resultado'], r.evaluaciones.map((e) => `<tr><td>#${e.id}</td><td>${esc(e.version)}</td><td>${e.puntaje} %</td><td>${badge(e.aprobada ? 'Aprobada' : 'No aprobada')}</td></tr>`).join(''))}<p class="helper">Los resultados históricos se muestran tal como fueron registrados. No se recalculan con la encuesta actual.</p>`,
                    );
                } catch (e) {
                    toast(e.message, true);
                }
            }),
    );
}
// Crea o modifica cuentas y sus permisos administrativos.
function editAccount(u = {}) {
    openModal(
        u.id ? 'Editar cuenta' : 'Nueva cuenta',
        `<form id="account-form"><div class="form-grid">${field('username', 'Usuario *', 'text', u.username, 'required maxlength="150"')}${field('first_name', 'Nombres', 'text', u.first_name)}${field('last_name', 'Apellidos', 'text', u.last_name)}${field('email', 'Correo', 'email', u.email)}${field('password', u.id ? 'Nueva contraseña (vacío conserva la actual)' : 'Contraseña *', 'password', '', 'minlength="12" autocomplete="new-password" ' + (u.id ? '' : 'required'))}${select(
            'is_active',
            'Cuenta activa',
            [
                ['true', 'Sí'],
                ['false', 'No'],
            ],
            String(u.id ? !!u.is_active : true),
        )}${select(
            'is_staff',
            'Acceso administrativo',
            [
                ['true', 'Sí'],
                ['false', 'No'],
            ],
            String(u.id ? !!u.is_staff : true),
        )}${select(
            'is_superuser',
            'Gestiona otras cuentas',
            [
                ['false', 'No'],
                ['true', 'Sí'],
            ],
            String(!!u.is_superuser),
        )}</div>${submit('Guardar cuenta')}</form>`,
    );
    bindForm(
        'account-form',
        '/api/admin/usuarios' + (u.id ? '/' + u.id : ''),
        (d) => ({
            ...d,
            is_active: d.is_active === 'true',
            is_staff: d.is_staff === 'true',
            is_superuser: d.is_superuser === 'true',
        }),
        () => {
            modal.close();
            navigate();
        },
        u.id ? 'PUT' : 'POST',
    );
}
// Muestra criterios, preguntas y publicación de una versión.
async function viewVersion(id) {
    const { cuestionario: q } = await api(
        `/adopciones/api/admin/cuestionarios/${id}/`,
    );
    openModal(
        q.nombre,
        `<p>${q.activa ? 'Versión activa: solo lectura.' : 'Los borradores sin solicitudes se pueden editar y publicar.'}</p><div class="admin-questions">${q.criterios.map((c) => `<h3>${esc(c.nombre)} · ${c.peso} %</h3>${c.preguntas.map((p) => `<article><p><strong>${esc(p.texto)}</strong></p><ul>${p.opciones.map((o) => `<li>${esc(o.texto)} · ${o.valor}/100 ${o.alerta ? '⚑ ' + esc(o.alerta) : ''}</li>`).join('')}</ul>${!q.activa ? `<button class="secondary small" data-question="${p.id}">Editar pregunta</button>` : ''}</article>`).join('')}`).join('')}</div>${!q.activa ? `<form id="publish-version">${submit('Publicar borrador')}</form>` : ''}`,
    );
    document.querySelectorAll('[data-question]').forEach(
        (b) =>
            (b.onclick = () =>
                editQuestion(
                    q,
                    q.criterios
                        .flatMap((c) => c.preguntas)
                        .find((p) => p.id === Number(b.dataset.question)),
                )),
    );
    if (!q.activa)
        bindForm(
            'publish-version',
            `/adopciones/api/admin/cuestionarios/${id}/publicar/`,
            () => ({}),
            () => {
                modal.close();
                navigate();
            },
        );
}
// Modifica texto y opciones de un borrador sin afectar versiones usadas.
function editQuestion(q, p) {
    openModal(
        'Editar pregunta del borrador',
        `<form id="question-form">${area('texto', 'Pregunta *', p.texto, 'required maxlength="300"')}${p.opciones.map((o) => `<section class="panel">${field('text-' + o.id, 'Respuesta *', 'text', o.texto, 'required maxlength="300"')}${field('value-' + o.id, 'Valor de 0 a 100', 'number', o.valor, 'required min="0" max="100" step="1"')}${field('alert-' + o.id, 'Alerta de bienestar (opcional)', 'text', o.alerta, 'maxlength="200"')}</section>`).join('')}${submit('Guardar pregunta')}</form>`,
    );
    bindForm(
        'question-form',
        `/adopciones/api/admin/cuestionarios/${q.id}/`,
        (d) => ({
            pregunta_id: p.id,
            texto: d.texto,
            opciones: p.opciones.map((o) => ({
                id: o.id,
                texto: d['text-' + o.id],
                valor: d['value-' + o.id],
                alerta: d['alert-' + o.id],
            })),
        }),
        () => viewVersion(q.id),
        'PUT',
    );
}
pages.configuracion = configuration;
if (location.hash === '#configuracion') navigate();
