// Prepara la sesión y carga los módulos JavaScript que necesita cada pantalla.
'use strict';
window.vetcare = {
    csrf: () =>
        decodeURIComponent(
            document.cookie
                .split('; ')
                .find((c) => c.startsWith('csrftoken='))
                ?.slice(10) || '',
        ),
};
(async () => {
    const screen = document.body.dataset.screen;
    // Carga los módulos de la pantalla en el orden de sus dependencias.
    function load(path) {
        return new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src = '/static/' + path;
            s.onload = resolve;
            s.onerror = () =>
                reject(new Error('No se pudo cargar la interfaz.'));
            document.body.append(s);
        });
    }
    const response = await fetch('/api/session', {
        credentials: 'same-origin',
    });
    if (!response.ok)
        throw new Error(
            'No se pudo iniciar la sesión. Comprueba MySQL y recarga.',
        );
    const { user } = await response.json();
    window.vetcare.user = user;
    document
        .querySelectorAll('[name=csrf_token]')
        .forEach((i) => (i.value = vetcare.csrf()));
    if (screen === 'dashboard') {
        if (!user) {
            location.replace('/');
            return;
        }
        document.body.dataset.user = user.id;
        document
            .querySelectorAll('[data-user-name]')
            .forEach((n) => (n.textContent = user.name));
        document
            .querySelectorAll('[data-avatar]')
            .forEach(
                (n) => (n.textContent = user.name.slice(0, 1).toUpperCase()),
            );
        await load('js/owner-search.js');
        await load('js/clinic.js');
        await load('js/adoptions-admin.js');
        await load('js/configuration.js');
        await load('js/interface.js');
    } else if (screen === 'catalog') {
        await load('js/adoptions-public.js');
    } else if (screen === 'login') {
        const form = document.querySelector('form'),
            button = form.querySelector('button'),
            error = form.querySelector('[role=alert]');
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            if (button.disabled) return;
            const label = button.textContent;
            button.disabled = true;
            button.textContent = 'Iniciando sesión…';
            error.hidden = true;
            try {
                const r = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': vetcare.csrf(),
                    },
                    body: JSON.stringify(
                        Object.fromEntries(new FormData(form)),
                    ),
                });
                const d = await r.json();
                if (!r.ok) throw new Error(d.message);
                location.assign(d.redirect);
            } catch (e) {
                error.hidden = false;
                error.textContent = e.message;
                button.disabled = false;
                button.textContent = label;
            }
        });
        button.disabled = false;
    } else if (screen === 'result') {
        const code = location.pathname.split('/').filter(Boolean).pop(),
            r = await fetch(
                '/adopciones/api/solicitud/' + encodeURIComponent(code) + '/',
            );
        const d = await r.json();
        if (!r.ok) throw new Error(d.message);
        const s = d.resultado,
            ring = document.querySelector('.score-ring');
        ring.classList.add(s.color);
        ring.style.setProperty('--target', s.porcentaje);
        ring.querySelector('strong').textContent = s.porcentaje + ' %';
        document.querySelector('h1').textContent = s.aprobada
            ? '¡Tu evaluación está aprobada!'
            : 'Gracias por querer dar un hogar.';
        document.querySelector('[data-explanation]').textContent = s.aprobada
            ? 'Alcanzaste el mínimo del 67 %. El equipo revisará las condiciones de bienestar antes de autorizar la entrega.'
            : 'Tu evaluación todavía no alcanza el 67 %. Prepara un mejor plan de cuidado con estas recomendaciones.';
        document.querySelector('[data-state]').textContent = s.estado;
        document.querySelector('.review-warning').hidden = !s.revisar;
        s.recomendaciones.forEach((tip) => {
            const p = document.createElement('p');
            p.className = 'recommendation';
            p.textContent = '♡ ' + tip;
            document.querySelector('[data-tips]').append(p);
        });
    }
})().catch((error) => {
    const box = document.querySelector(
        '#app,.login-error,#adoption-cards,[data-explanation]',
    );
    if (box) {
        box.textContent = error.message;
        box.hidden = false;
    }
});
window.addEventListener('pageshow', (e) => {
    if (e.persisted) location.reload();
});
