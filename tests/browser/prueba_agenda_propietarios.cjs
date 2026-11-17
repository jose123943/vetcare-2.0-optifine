/* Usa únicamente el servidor y la base aislados de las pruebas. */
const { chromium } = require(process.env.VETCARE_PLAYWRIGHT_MODULE);
const fs = require('fs'),
    os = require('os'),
    path = require('path'),
    { execFileSync } = require('child_process');
const assert = require('node:assert/strict');
const { randomUUID } = require('crypto');
(async () => {
    const browser = await chromium.launch({
        executablePath:
            'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
        headless: true,
    });
    try {
        const context = await browser.newContext({
            baseURL: 'http://127.0.0.1:8001',
            viewport: { width: 1440, height: 1000 },
        });
        context.setDefaultTimeout(60000);
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
        page.on('pageerror', (error) => errors.push(error.message));
        await page.goto('/inicio/#consultar');
        const search = page.locator('#patient-search');
        await search.click();
        const menu = page.locator('#patient-owner-results');
        await menu.locator('[data-owner]').first().waitFor();
        assert.ok((await menu.locator('[data-owner]').count()) >= 5);
        await search.press('ArrowUp');
        assert.equal(
            await search.getAttribute('aria-activedescendant'),
            await menu.locator('[data-owner]').last().getAttribute('id'),
        );
        await search.press('Escape');
        assert.ok(await menu.isHidden());
        await search.evaluate((input) => input.blur());
        await search.click();
        await menu.locator('[data-owner]').first().waitFor();
        const ownerId = await menu
            .locator('[data-owner]')
            .first()
            .getAttribute('data-owner');
        await search.press('ArrowDown');
        await search.press('Enter');
        const expected = await (
            await context.request.get(`/api/clientes/${ownerId}/mascotas`)
        ).json();
        await page.waitForFunction(
            (count) =>
                document.querySelectorAll('#patients-table [data-pet]')
                    .length === count,
            expected.mascotas.length,
        );
        await search.fill(expected.mascotas[0].nombre);
        await page.locator('#search-patients').click();
        await page
            .getByText(expected.mascotas[0].nombre, { exact: true })
            .first()
            .waitFor();
        const veterinarian = await (
            await context.request.post('/api/veterinarios', {
                headers: {
                    'X-CSRFToken': cookie.csrf,
                    'Idempotency-Key': randomUUID(),
                },
                data: {
                    nombre: 'Navegador',
                    apellido: 'Agenda',
                    telefono: '0000000000',
                    especialidad: 'Demostración',
                },
            })
        ).json();
        assert.ok(veterinarian.id);
        await page.locator('[data-nav=agendar]').click();
        const ownerSearch = page.locator('#owner-search');
        await ownerSearch.click();
        await page.locator('#owner-results [data-owner]').first().waitFor();
        const owners = await (
            await context.request.get('/api/clientes')
        ).json();
        const owner = owners.clientes.find((row) => String(row.id) === ownerId);
        await ownerSearch.fill(owner.documento);
        await page.waitForFunction(
            () =>
                document.querySelectorAll('#owner-results [data-owner]')
                    .length === 1,
        );
        await ownerSearch.press('ArrowDown');
        await ownerSearch.press('Enter');
        await page.waitForFunction(
            (count) =>
                document.querySelectorAll('[name=mascota] option').length ===
                count + 1,
            expected.mascotas.length,
        );
        assert.deepEqual(
            await page.locator('[name=estado] option').allTextContents(),
            ['Programada'],
        );
        await page
            .locator('[name=mascota]')
            .selectOption(String(expected.mascotas[0].id));
        await page
            .locator('[name=veterinario]')
            .selectOption(String(veterinarian.id));
        await page.locator('[name=fecha]').fill('2027-07-15');
        await page.locator('[name=hora]').fill('08:00');
        const reason = 'Agenda de navegador ' + Date.now();
        await page.locator('[name=motivo]').fill(reason);
        const responsePromise = page.waitForResponse(
            (response) =>
                response.url().endsWith('/registrar/cita/') &&
                response.request().method() === 'POST',
        );
        await page
            .getByRole('button', { name: 'Registrar cita', exact: true })
            .click();
        const created = await (await responsePromise).json();
        assert.equal(created.cita.estado, 'Programada');
        await page.locator('[data-nav=reportes]').click();
        await page.locator('#new-invoice').click();
        const payment = page.locator('#invoice-form select[name=metodo_pago]');
        await payment.waitFor();
        assert.deepEqual(await payment.locator('option').allTextContents(), [
            'Transferencia',
            'Efectivo',
            'Tarjeta',
        ]);
        await page
            .locator('[name=cita_id]')
            .selectOption(String(created.cita.id));
        await page.locator('[name=servicio]').fill('Control de demostración');
        await page.locator('[name=precio_unitario]').fill('45000');
        await payment.selectOption('Efectivo');
        await page
            .getByRole('button', { name: 'Registrar factura', exact: true })
            .click();
        await page
            .getByRole('heading', { name: 'Factura registrada', exact: true })
            .waitFor();
        const download = page.getByRole('link', {
            name: 'Descargar factura PDF',
        });
        const pdf = await context.request.get(
            await download.getAttribute('href'),
        );
        assert.ok((await pdf.body()).subarray(0, 4).toString() === '%PDF');
        await page.locator('[data-close]').click();
        await page.locator('[data-invoice]').first().click();
        await page
            .locator('#invoice-state select[name=metodo_pago]')
            .selectOption('Tarjeta');
        await page
            .getByRole('button', { name: 'Actualizar estado', exact: true })
            .click();
        await page.locator('#modal').waitFor({ state: 'hidden' });
        await page.locator('[data-invoice]').first().click();
        assert.equal(
            await page
                .locator('#invoice-state select[name=metodo_pago]')
                .inputValue(),
            'Tarjeta',
        );
        await page.locator('[data-close]').click();
        await page.locator('[data-nav=citas]').click();
        const row = page
            .locator('#appointments-list tbody tr')
            .filter({ hasText: reason });
        await row.locator('.Programada').waitFor();
        const script =
            "import json,tempfile,sys;from pathlib import Path;from datetime import datetime,timedelta;from zoneinfo import ZoneInfo;from vetcare.config import Config;from vetcare.db import Database;info=json.loads((Path(tempfile.gettempdir())/'vetcare_browser_active_database.json').read_text());d=Database(Config.load(database=info['database'],testing=True));c=d.connect();q=c.cursor();q.execute('UPDATE cita SET fecha=%s,hora=%s WHERE id_cita=%s',((datetime.now(ZoneInfo('America/Bogota'))-timedelta(days=1)).date(),'00:00:00',int(sys.argv[1])));q.close();c.close();d.close()";
        execFileSync(
            path.resolve('.venv-wsgi/Scripts/python.exe'),
            ['-c', script, String(created.cita.id)],
            { cwd: process.cwd(), stdio: 'pipe' },
        );
        await row.locator('.Atendida').waitFor({ timeout: 45000 });
        await page.locator('[data-nav=consultar]').click();
        await page.setViewportSize({ width: 390, height: 844 });
        await page.locator('#patient-search').click();
        await page
            .locator('#patient-owner-results [data-owner]')
            .first()
            .waitFor();
        await page.waitForFunction(
            () => document.documentElement.scrollWidth <= innerWidth,
        );
        await page.screenshot({
            path: 'docs/evidencias/propietarios-desplegable-movil.png',
            fullPage: true,
        });
        assert.deepEqual(errors, []);
        console.log(
            'OK: propietarios al abrir y por documento, selección por teclado, búsqueda libre de mascota, estado Programada, tres métodos de pago y PDF, cambio de método, Atendida sin recargar y móvil.',
        );
    } finally {
        await browser.close();
    }
})().catch((error) => {
    console.error(error);
    process.exit(1);
});
