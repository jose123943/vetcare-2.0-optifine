/* Sólo contra el servidor de pruebas y sus cookies temporales. */
const {chromium}=require(process.env.VETCARE_PLAYWRIGHT_MODULE);
const fs=require('fs'),os=require('os'),path=require('path');
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  try {
    const context=await browser.newContext({baseURL:'http://127.0.0.1:8001',viewport:{width:1440,height:1000}});
    context.setDefaultTimeout(60000);
    const cookie=JSON.parse(fs.readFileSync(path.join(os.tmpdir(),'vetcare_browser_cookie.json'),'utf8'));
    await context.addCookies([
      {name:'vetcare_sid',value:cookie.sessionid,domain:'127.0.0.1',path:'/'},
      {name:'csrftoken',value:cookie.csrf,domain:'127.0.0.1',path:'/'}
    ]);
    const page=await context.newPage(),errors=[];
    context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)));
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('/');
    assert.equal(new URL(page.url()).pathname,'/inicio/');
    await page.goto('/inicio/#adopciones');
    await page.locator('#open-adoption-survey').waitFor();
    const buttons=page.locator('[data-survey-pet]');
    await buttons.first().waitFor();
    assert.ok(await buttons.count()>=5);
    const selected=await buttons.first().getAttribute('data-survey-pet');
    const name=await buttons.first().locator('xpath=ancestor::article').locator('h3').innerText();
    await page.screenshot({path:'docs/demo-adopciones-encuesta.png',fullPage:true});
    const [survey]=await Promise.all([context.waitForEvent('page'),buttons.first().click()]);
    await survey.locator('#adopt-form').waitFor();
    assert.equal(new URL(survey.url()).searchParams.get('mascota'),selected);
    assert.equal(await survey.locator('#adopt-form h3').first().innerText(),'Un hogar para '+name);
    await survey.screenshot({path:'docs/demo-encuesta-directa.png',fullPage:true});
    await survey.locator('[name=nombre]').fill('Solicitante sintético del botón');
    await survey.locator('[name=documento]').fill('DEMO-BROWSER-'+Date.now());
    await survey.locator('[name=edad]').fill('30');
    await survey.locator('[name=telefono]').fill('0000000000');
    await survey.locator('[name=email]').fill('browser@vetcare.example.invalid');
    await survey.locator('[name=direccion]').fill('Dirección ficticia');
    await survey.locator('[name=ocupacion]').fill('Demostración');
    await survey.locator('[name=presupuesto_cop]').fill('200000');
    await survey.locator('[name=consentimiento]').check();
    await survey.locator('#next').click();
    for(let step=1;step<=8;step++){
      const section=survey.locator(`[data-step="${step}"]`);
      await section.waitFor({state:'visible'});
      const questions=section.locator('fieldset');
      for(let n=0;n<await questions.count();n++)await questions.nth(n).locator('input').first().check();
      if(step<8)await survey.locator('#next').click();
    }
    await survey.locator('#send-application').click();
    await survey.waitForURL('**/adopciones/solicitud/**');
    await survey.getByText('¡Tu evaluación está aprobada!',{exact:true}).waitFor();
    await page.reload();
    await page.locator('#open-adoption-survey').waitFor();
    await page.setViewportSize({width:390,height:844});
    await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.getByRole('button',{name:'Cerrar sesión',exact:false}).click();
    await page.getByRole('button',{name:'Iniciar sesión'}).waitFor();
    const protectedRoute=await context.request.get('/api/clientes');
    assert.equal(protectedRoute.status(),401);
    assert.deepEqual(errors,[]);
    console.log('OK: sesión al navegar y recargar, encuesta directa desde adopciones, 21 respuestas, resultado, móvil y cierre de sesión.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exit(1);});
