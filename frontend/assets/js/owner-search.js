// Comparte el buscador de propietarios entre la consulta de pacientes y la agenda.
'use strict';
let ownerSearchCleanup = () => {};
// Conecta un desplegable accesible, búsqueda libre y selección de propietario.
function bindOwnerSearch(input, box, onSelect, onInput = () => {}) {
    ownerSearchCleanup();
    const controller = new AbortController(),
        options = { signal: controller.signal };
    let sequence = 0,
        timer,
        owners = [],
        active = -1;
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-controls', box.id);
    input.setAttribute('aria-expanded', 'false');
    box.setAttribute('role', 'listbox');
    box.setAttribute('aria-label', 'Propietarios registrados');
    box.hidden = true;
    // Cierra la lista y limpia su selección accesible.
    function hide() {
        box.hidden = true;
        input.setAttribute('aria-expanded', 'false');
        input.removeAttribute('aria-activedescendant');
        active = -1;
    }
    // Mueve el foco virtual de las opciones con el teclado.
    function highlight(index) {
        active = index;
        box.querySelectorAll('[data-owner]').forEach((button, i) =>
            button.setAttribute('aria-selected', String(i === index)),
        );
        const button = box.querySelectorAll('[data-owner]')[index];
        if (button) {
            input.setAttribute('aria-activedescendant', button.id);
            button.scrollIntoView({ block: 'nearest' });
        }
    }
    // Aplica un propietario e invalida búsquedas pendientes.
    async function choose(index) {
        const owner = owners[index];
        if (!owner) return;
        ++sequence;
        hide();
        input.value = `${owner.nombre} ${owner.apellido}`;
        try {
            await onSelect(owner);
        } catch (error) {
            toast(error.message, true);
        }
    }
    // Consulta propietarios e ignora respuestas que llegan fuera de orden.
    async function search() {
        const stamp = ++sequence;
        try {
            const result = await api(
                `clientes/?q=${encodeURIComponent(input.value)}`,
            );
            if (
                stamp !== sequence ||
                !input.isConnected ||
                document.activeElement !== input
            )
                return;
            owners = result.clientes;
            active = -1;
            box.innerHTML =
                owners
                    .map(
                        (o, i) =>
                            `<button type="button" role="option" tabindex="-1" aria-selected="false" id="${box.id}-${o.id}" data-owner="${o.id}" data-index="${i}"><strong>${esc(o.nombre)} ${esc(o.apellido)}</strong><small>Doc. ${esc(o.documento || 'Sin registrar')} · ${esc(o.telefono)} · #${o.id}</small></button>`,
                    )
                    .join('') ||
                '<p class="helper">No hay propietarios con esa búsqueda.</p>';
            box.hidden = false;
            input.setAttribute('aria-expanded', 'true');
            box.querySelectorAll('[data-index]').forEach((button) => {
                button.onpointerdown = (event) => event.preventDefault();
                button.onclick = () => choose(Number(button.dataset.index));
            });
        } catch (error) {
            if (stamp === sequence && input.isConnected)
                toast(error.message, true);
        }
    }
    input.addEventListener('focus', search, options);
    input.addEventListener(
        'input',
        () => {
            clearTimeout(timer);
            ++sequence;
            hide();
            onInput();
            timer = setTimeout(search, 200);
        },
        options,
    );
    input.addEventListener(
        'keydown',
        (event) => {
            if (event.key === 'Escape') {
                clearTimeout(timer);
                ++sequence;
                hide();
                return;
            }
            if (
                (event.key === 'ArrowDown' || event.key === 'ArrowUp') &&
                !box.hidden &&
                owners.length
            ) {
                event.preventDefault();
                highlight(
                    active < 0
                        ? event.key === 'ArrowDown'
                            ? 0
                            : owners.length - 1
                        : (active +
                              (event.key === 'ArrowDown'
                                  ? 1
                                  : owners.length - 1) +
                              owners.length) %
                              owners.length,
                );
            }
            if (event.key === 'Enter' && !box.hidden && active >= 0) {
                event.preventDefault();
                choose(active);
            }
        },
        options,
    );
    input.addEventListener(
        'blur',
        () => {
            ++sequence;
            hide();
        },
        options,
    );
    ownerSearchCleanup = () => {
        clearTimeout(timer);
        ++sequence;
        controller.abort();
        hide();
    };
}
