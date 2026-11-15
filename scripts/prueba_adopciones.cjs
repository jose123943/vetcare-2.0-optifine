const {chromium}=require(process.env.VETCARE_PLAYWRIGHT_MODULE);
const fs=require('fs'),os=require('os'),path=require('path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const ctx=await browser.newContext({baseURL:'http://127.0.0.1:8001',viewport:{width:1440,height:1000}}),page=await ctx.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/adopciones/');await page.locator('.adoption-card').first().waitFor();
 await page.screenshot({path:'docs/v2-catalogo-escritorio.png',fullPage:true});
 await page.setViewportSize({width:820,height:1180});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'docs/v2-catalogo-tableta.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'docs/v2-catalogo-movil.png',fullPage:true});
 await page.setViewportSize({width:1440,height:1000});await page.locator('[data-adopt]:enabled').first().click();
 await page.locator('#adopt-form [name=nombre]').fill('Solicitante navegador');await page.locator('[name=documento]').fill('BROWSER-'+Date.now());
 await page.locator('[name=edad]').fill('28');await page.locator('[name=telefono]').fill('3000000000');await page.locator('[name=email]').fill('test@example.invalid');
 await page.locator('[name=direccion]').fill('Dirección sintética');await page.locator('[name=ocupacion]').fill('Estudiante');await page.locator('[name=presupuesto_cop]').fill('200000');await page.locator('[name=consentimiento]').check();
 await page.locator('#next').click();
 for(let step=1;step<=8;step++){
   const section=page.locator(`[data-step="${step}"]`);await section.waitFor({state:'visible'});
   const blocks=section.locator('fieldset');for(let i=0;i<await blocks.count();i++)await blocks.nth(i).locator('input').first().check();
   if(step===2)await page.screenshot({path:'docs/v2-cuestionario.png',fullPage:true});
   if(step<8)await page.locator('#next').click();
 }
 await page.locator('#send-application').click();await page.waitForURL('**/adopciones/solicitud/**');
 await page.getByText('¡Tu evaluación está aprobada!',{exact:true}).waitFor();
 const resultUrl=page.url();await page.screenshot({path:'docs/v2-resultado.png',fullPage:true});
 const cookie=JSON.parse(fs.readFileSync(path.join(os.tmpdir(),'vetcare_browser_cookie.json'),'utf8'));
 await ctx.addCookies([{name:'vetcare_sid',value:cookie.sessionid,domain:'127.0.0.1',path:'/'},{name:'csrftoken',value:cookie.csrf,domain:'127.0.0.1',path:'/'}]);
 await page.goto('/inicio/#adopciones');await page.getByRole('heading',{name:'Gestión de adopciones',exact:true}).waitFor();
 await page.locator('[data-application]').first().click();await page.locator('#review-adoption').waitFor();
 await page.locator('[name=notas]').fill('Revisión sintética del plan de cuidado y seguridad.');await page.locator('[name=bienestar_verificado]').check();
 await page.getByRole('button',{name:'Confirmar revisión'}).click();await page.locator('#modal').waitFor({state:'hidden'});
 await page.locator('[data-application]').first().click();await page.locator('[name=accion]').selectOption('Entregar');await page.locator('[name=notas]').fill('Entrega de prueba supervisada.');await page.locator('[name=bienestar_verificado]').check();
 await page.getByRole('button',{name:'Confirmar revisión'}).click();await page.locator('#modal').waitFor({state:'hidden'});
 await page.getByText('Entregada',{exact:true}).first().waitFor();await page.screenshot({path:'docs/v2-gestion-entrega.png',fullPage:true});
 await page.locator('[data-nav=dashboard]').click();await page.getByRole('heading',{name:'Citas pendientes',exact:true}).waitFor();await page.screenshot({path:'docs/v2-dashboard.png',fullPage:true});
 await page.locator('#sidebar-toggle').click();assert.ok(await page.locator('body').evaluate(e=>e.classList.contains('sidebar-compact')));
 assert.deepEqual(errors,[]);console.log('Adopciones E2E: catálogo escritorio/tableta/móvil, encuesta, resultado, revisión, autorización y entrega: OK.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
