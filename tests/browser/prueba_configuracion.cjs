const { chromium } = require(process.env.VETCARE_PLAYWRIGHT_MODULE),
    assert = require('node:assert/strict');
(async () => {
    const browser = await chromium.launch({
        executablePath:
            'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
        headless: true,
    });
    const context = await browser.newContext({
            baseURL: 'http://127.0.0.1:8001',
            viewport: { width: 1440, height: 1000 },
        }),
        page = await context.newPage(),
        errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.setDefaultTimeout(60000);
    await page.goto('/');
    await page.locator('[name=username]').fill('wsgi-test-admin');
    await page.locator('[name=password]').fill('Fixture-only-for-tests-2026');
    await page
        .getByRole('button', { name: 'Iniciar sesión', exact: false })
        .click();
    await page.getByRole('heading', { name: 'Bienvenido a VetCare' }).waitFor();
    await page.locator('[data-nav=configuracion]').click();
    await page.getByRole('heading', { name: 'Cuentas del equipo' }).waitFor();
    await page.locator('#new-account').click();
    const name = 'browser-account-' + Date.now();
    await page.locator('#account-form [name=username]').fill(name);
    await page
        .locator('#account-form [name=password]')
        .fill('Synthetic-browser-only-2026');
    await page
        .getByRole('button', { name: 'Guardar cuenta', exact: true })
        .click();
    await page.getByText(name, { exact: true }).waitFor();
    await page.screenshot({
        path: 'docs/evidencias/wsgi-configuracion.png',
        fullPage: true,
    });
    await page.locator('[data-nav=adopciones]').click();
    await page.locator('#weights').click();
    await page.locator('[name=publicar]').selectOption('false');
    await page
        .getByRole('button', { name: 'Crear versión', exact: true })
        .click();
    await page.locator('#modal').waitFor({ state: 'hidden' });
    await page.locator('[data-nav=configuracion]').click();
    await page.locator('[data-version]').first().click();
    await page.locator('[data-question]').first().click();
    await page
        .locator('#question-form [name=texto]')
        .fill('Pregunta revisada desde la interfaz de pruebas');
    await page
        .getByRole('button', { name: 'Guardar pregunta', exact: true })
        .click();
    await page
        .getByText('Pregunta revisada desde la interfaz de pruebas', {
            exact: true,
        })
        .waitFor();
    await page
        .getByRole('button', { name: 'Publicar borrador', exact: true })
        .click();
    await page.locator('#modal').waitFor({ state: 'hidden' });
    await page.locator('[data-nav=vacunacion]').click();
    await page.locator('[name=paciente]').selectOption({ index: 1 });
    await page.locator('#new-vaccine').click();
    await page.locator('[name=nombre_vacuna]').fill('Vacuna navegador');
    await page.locator('[name=lote]').fill('TEST');
    await page.locator('[name=fecha_vencimiento]').fill('2028-01-01');
    await page
        .getByRole('button', { name: 'Registrar vacuna', exact: true })
        .click();
    await page.getByText('Vacuna navegador', { exact: true }).waitFor();
    assert.deepEqual(errors, []);
    console.log(
        'Navegador: login real del usuario sintético, cuentas, borrador, edición, publicación y vacuna: OK.',
    );
    await browser.close();
})().catch((e) => {
    console.error(e);
    process.exit(1);
});
