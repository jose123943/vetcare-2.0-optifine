// Presentaci?n del men? e indicadores; no modifica datos cl?nicos.
'use strict';
document
    .querySelector('#sidebar-toggle')
    ?.addEventListener('click', (event) => {
        const compact = document.body.classList.toggle('sidebar-compact');
        event.currentTarget.setAttribute('aria-expanded', String(!compact));
    });
const animateNumbers = new MutationObserver((records) => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    for (const record of records)
        for (const node of record.addedNodes) {
            if (node.nodeType !== 1) continue;
            node.querySelectorAll('.stat strong').forEach((item) => {
                if (item.dataset.counted || !/^\d+$/.test(item.textContent))
                    return;
                item.dataset.counted = 'true';
                const target = Number(item.textContent);
                if (target > 100000) return;
                const start = performance.now();
                // Anima un indicador sin cambiar su valor final ni forzar movimiento reducido.
                function tick(now) {
                    const progress = Math.min((now - start) / 450, 1);
                    item.textContent = String(
                        Math.round(target * (1 - Math.pow(1 - progress, 3))),
                    );
                    if (progress < 1) requestAnimationFrame(tick);
                }
                requestAnimationFrame(tick);
            });
        }
});
animateNumbers.observe(document.querySelector('#app'), { childList: true });
