// Comprueba altas, cambios, eliminaciones protegidas y fotografías en el navegador de pruebas.
const { chromium } = require(process.env.VETCARE_PLAYWRIGHT_MODULE),
    fs = require('fs'),
    path = require('path'),
    os = require('os'),
    assert = require('node:assert/strict');

// Abre Edge con datos de prueba y conserva los errores para comprobar el recorrido.
(async () => {
    // Ejecuta el navegador sin abrir ventanas para el usuario.
    const browser = await chromium.launch({
        executablePath:
            'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
        headless: true,
    });

    const context = await browser.newContext({
            baseURL: 'http://127.0.0.1:8001',
        }),
        page = await context.newPage(),
        errors = [],
        fixture = JSON.parse(
            fs.readFileSync(
                path.join(os.tmpdir(), 'vetcare_browser_cookie.json'),
                'utf8',
            ),
        );

    await context.addCookies([
        {
            name: 'vetcare_sid',
            value: fixture.sessionid,
            domain: '127.0.0.1',
            path: '/',
        },
        {
            name: 'csrftoken',
            value: fixture.csrf,
            domain: '127.0.0.1',
            path: '/',
        },
    ]);

    page.on('pageerror', (e) => errors.push(e.message));
    page.setDefaultTimeout(60000);

    await page.goto('/inicio/#consultar');
    await page.locator('#search-owners').click();
    await page.locator('[data-owner-edit]').first().click();

    await page
        .locator('#owner-edit [name=direccion]')
        .fill('Dirección editada de prueba');
    await page
        .getByRole('button', { name: 'Guardar propietario', exact: true })
        .click();
    await page.locator('#modal').waitFor({ state: 'hidden' });

    await page.locator('#search-owners').click();
    await page.locator('[data-owner-edit]').first().click();
    await page
        .getByRole('button', { name: 'Eliminar cliente sin historiales' })
        .click();
    await page
        .locator('#owner-delete .form-error')
        .filter({ hasText: 'mascotas o facturas' })
        .waitFor();
    await page.locator('[data-close]').click();

    const token = Date.now().toString();

    // Envía los cambios de prueba con los mismos controles de seguridad que la interfaz.
    async function write(url, data, method = 'POST') {
        const r = await context.request.fetch(url, {
            method,
            data,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': fixture.csrf,
                'Idempotency-Key': crypto.randomUUID(),
            },
        });
        assert.equal(r.status(), 200);
        return r.json();
    }

    const f = await write('/api/clientes', {
        nombre: 'Sin pacientes',
        apellido: 'Prueba',
        documento: token,
        telefono: '3000000000',
        email: '',
        direccion: 'Prueba',
        mascotas: [
            {
                nombre: 'Temporal',
                especie: 'Gato',
                raza: 'Criollo',
                sexo: 'Hembra',
                edad: 1,
                peso: '3',
                observaciones: '',
            },
        ],
    });

    const animals = await (
        await context.request.get(`/api/clientes/${f.cliente_id}/mascotas`)
    ).json();
    await write(`/api/mascotas/${animals.mascotas[0].id}`, {}, 'DELETE');

    await page.locator('#patient-search').fill(token);
    await page.locator('#search-owners').click();
    await page.locator('[data-owner-edit]').first().click();
    await page
        .getByRole('button', { name: 'Eliminar cliente sin historiales' })
        .click();
    await page.locator('#modal').waitFor({ state: 'hidden' });
    assert.equal(
        (await context.request.get(`/api/clientes/${f.cliente_id}`)).status(),
        404,
    );

    await page.locator('[data-nav=veterinarios]').click();
    await page.locator('#new-vet').click();
    await page.locator('#vet-form [name=nombre]').fill('Profesional ' + token);
    await page.locator('#vet-form [name=apellido]').fill('Prueba');
    await page.locator('#vet-form [name=telefono]').fill('3000000000');
    await page.locator('#vet-form [name=especialidad]').fill('General');
    await page.getByRole('button', { name: 'Guardar', exact: true }).click();
    await page.locator('#modal').waitFor({ state: 'hidden' });

    const row = page.locator('tr').filter({ hasText: 'Profesional ' + token });
    await row.getByRole('button', { name: 'Editar', exact: true }).click();
    await page.locator('#vet-form [name=especialidad]').fill('Revisada');
    await page.getByRole('button', { name: 'Guardar', exact: true }).click();
    await page.locator('#modal').waitFor({ state: 'hidden' });

    await row.getByRole('button', { name: 'Editar', exact: true }).click();
    await page
        .getByRole('button', { name: 'Eliminar veterinario sin citas' })
        .click();
    await page.locator('#modal').waitFor({ state: 'hidden' });
    await row.waitFor({ state: 'detached' });

    await page.locator('[data-nav=adopciones]').click();
    await page.locator('#new-adoption-pet').click();
    const rescue = 'Adopción navegador ' + token;

    for (const [name, value] of Object.entries({
        nombre: rescue,
        edad_aproximada: '2 años',
        peso: '4',
        descripcion: 'Historia sintética',
        personalidad: 'Tranquila',
        salud: 'Revisión de prueba',
        vacunacion: 'Al día',
    }))
        await page.locator(`#adoption-pet-form [name=${name}]`).fill(value);

    await page
        .getByRole('button', { name: 'Guardar mascota', exact: true })
        .click();
    await page
        .locator('#adoption-photo [name=fotografia]')
        .setInputFiles(path.resolve('frontend/assets/images/huella.png'));
    await page
        .getByRole('button', { name: 'Subir fotografía', exact: true })
        .click();
    await page.locator('#modal').waitFor({ state: 'hidden' });
    await page.getByRole('heading', { name: rescue, exact: true }).waitFor();
    await page.screenshot({
        path: 'docs/evidencias/wsgi-mascota-adopcion.png',
        fullPage: true,
    });

    assert.deepEqual(errors, []);
    // Resume el resultado del recorrido para facilitar la revisión.
    console.log(
        'Navegador: editar/eliminar cliente con protección de historiales, alta/edición/baja de veterinario y alta de mascota en adopción con foto: OK.',
    );
    await browser.close();
})().catch((e) => {
    console.error(e);
    process.exit(1);
});
