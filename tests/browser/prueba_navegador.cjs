// Recorre el registro clínico, la agenda, la factura PDF y el cierre de sesión.

const { chromium } = require(process.env.VETCARE_PLAYWRIGHT_MODULE);

const fs = require('fs'),
    os = require('os'),
    path = require('path');

const assert = require('node:assert/strict');

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
        viewport: { width: 1440, height: 1000 },
    });

    const cookie = JSON.parse(
        fs.readFileSync(
            path.join(os.tmpdir(), 'vetcare_browser_cookie.json'),
            'utf8',
        ),
    );

    await context.addCookies([
        {
            name: 'vetcare_sid',
            value: cookie.sessionid,
            domain: '127.0.0.1',
            path: '/',
        },
        {
            name: 'csrftoken',
            value: cookie.csrf,
            domain: '127.0.0.1',
            path: '/',
        },
    ]);

    const page = await context.newPage(),
        errors = [];
    page.on('pageerror', (e) => errors.push(e.message));

    page.setDefaultTimeout(60000);

    await page.goto('http://127.0.0.1:8001/inicio/');
    await page.getByRole('heading', { name: 'Bienvenido a VetCare' }).waitFor();

    await page.screenshot({
        path: 'docs/evidencias/dashboard-escritorio.png',
        fullPage: true,
    });

    await page.locator('[data-nav=registrar]').click();
    await page.locator('#register').waitFor();

    const familyId = Date.now().toString();

    await page
        .locator('#register section:first-child [name=nombre]')
        .fill('Familia');

    await page.locator('[name=apellido]').fill('Navegador');
    await page.locator('[name=documento]').fill(familyId);

    await page.locator('[name=telefono]').fill('3000000000');
    await page.locator('[name=direccion]').fill('Datos sintéticos');
    await page.locator('[name=email]').fill('test@example.invalid');

    await page.locator('#pet-count').fill('3');
    await page.locator('#set-count').click();

    const cards = page.locator('.pet-card');
    assert.equal(await cards.count(), 3);

    for (let i = 0; i < 3; i++) {
        const card = cards.nth(i);
        await card.locator('[name=nombre]').fill('Rocky ' + i);
        await card.locator('[name=especie]').selectOption('Perro');
        await card.locator('[name=raza]').fill('Criollo');
        await card.locator('[name=edad]').fill('2');
        await card.locator('[name=peso]').fill('4.50');
    }

    await page.screenshot({
        path: 'docs/evidencias/registro-multiples-mascotas.png',
        fullPage: true,
    });

    await page
        .getByRole('button', { name: 'Registrar cliente y mascotas' })
        .click();
    await page
        .getByText('Cliente y 3 mascota(s) registrados.', { exact: true })
        .waitFor();

    await page.locator('[data-nav=agendar]').click();
    await page.locator('#owner-search').fill(familyId);

    await page.locator('[data-owner]').first().click();
    await page
        .locator('[name=mascota] option')
        .nth(1)
        .waitFor({ state: 'attached' });

    assert.equal(await page.locator('[name=mascota] option').count(), 4);


    await page.locator('[name=mascota]').selectOption({ index: 1 });
    await page.locator('[name=veterinario]').selectOption({
        index: (await page.locator('[name=veterinario] option').count()) - 1,
    });
    await page.locator('[name=fecha]').fill('2027-02-15');
    await page.locator('[name=hora]').fill('07:00');
    await page.locator('[name=motivo]').fill('Consulta de prueba en navegador');

    await page
        .getByRole('button', { name: 'Registrar cita', exact: true })
        .click();
    await page
        .getByRole('heading', { name: 'Citas pendientes', exact: true })
        .waitFor();
    await page
        .getByText('Consulta de prueba en navegador', { exact: true })
        .first()
        .waitFor();

    await page.locator('[data-nav=reportes]').click();
    await page.locator('#new-invoice').click();
    await page.locator('[name=cita_id]').selectOption({ index: 1 });

    await page.locator('[name=servicio]').fill('Consulta');
    await page.locator('[name=precio_unitario]').fill('40000');
    await page.locator('#add-service').click();
    await page.locator('[name=servicio]').nth(1).fill('Vacuna');
    await page.locator('[name=precio_unitario]').nth(1).fill('35000');

    await page
        .getByRole('button', { name: 'Registrar factura', exact: true })
        .click();
    await page
        .getByRole('heading', { name: 'Factura registrada', exact: true })
        .waitFor();

    const download = page.getByRole('link', { name: 'Descargar factura PDF' });
    const pdf = await context.request.get(await download.getAttribute('href'));
    assert.equal(pdf.status(), 200);
    const pdfBody = await pdf.body();
    assert.ok(pdfBody.subarray(0, 4).toString() === '%PDF');
    fs.writeFileSync('docs/evidencias/factura-ejemplo-pruebas.pdf', pdfBody);

    await page.locator('[data-close]').click();
    await page.locator('[data-nav=dashboard]').click();
    await page
        .getByRole('heading', { name: 'Citas pendientes', exact: true })
        .waitFor();

    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForFunction(
        () => document.documentElement.scrollWidth <= innerWidth,
    );
    await page.screenshot({
        path: 'docs/evidencias/dashboard-movil.png',
        fullPage: true,
    });
    await page.waitForFunction(
        () => document.documentElement.scrollWidth <= innerWidth,
    );
    assert.ok(
        await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
        ),
    );

    await page
        .getByRole('button', { name: 'Cerrar sesión', exact: false })
        .click();
    await page.getByRole('button', { name: 'Iniciar sesión' }).waitFor();

    await page.goto('http://127.0.0.1:8001/inicio/');
    assert.equal(new URL(page.url()).pathname, '/');

    assert.deepEqual(errors, []);
    // Resume el resultado del recorrido para facilitar la revisión.
    console.log(
        'Navegador: registro de 3 mascotas, agenda, factura PDF, móvil y cierre de sesión: OK.',
    );

    await browser.close();
})().catch((e) => {
    console.error(e);
    process.exit(1);
});
