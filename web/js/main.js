/* Arranque de la interfaz: lee la configuración y los edificios, monta los paneles y abre el
   último escenario usado.

   Enlaces profundos (útiles para marcadores y capturas):
     #comparativa/mes-barras          escenario y subescenario
     ?anio=2026&mes=3&codigo=EDIF-1   contexto
     ?paneles=01                      paneles izquierdos visibles [escenarios][subescenarios] */
(async function () {
  'use strict';
  const EN = window.EN;

  try {
    EN.cargarEstado();

    const params = new URLSearchParams(location.search);
    const entero = (v) => (v !== null && /^\d+$/.test(v) ? Number(v) : null);
    const paneles = params.get('paneles');
    if (paneles && /^[01]{2,3}$/.test(paneles)) {
      EN.E.l1 = paneles[0] === '1';
      EN.E.l2 = paneles[1] === '1';
      if (paneles.length === 3) EN.E.r1 = paneles[2] === '1';
    }
    if (entero(params.get('anio'))) EN.E.anio = entero(params.get('anio'));
    if (entero(params.get('mes')) >= 1 && entero(params.get('mes')) <= 12) EN.E.mes = entero(params.get('mes'));
    if (params.get('codigo')) EN.E.codigo = params.get('codigo');

    EN.montarShell();
    EN.montarNavegacion();

    EN.cfg = await EN.api('/api/config');
    if (!EN.E.anio) EN.E.anio = EN.cfg.anio_actual;
    await EN.recargarEdificios();
    EN.montarContexto();

    const [escHash, subHash] = decodeURIComponent(location.hash.replace(/^#/, '')).split('/');
    EN.irA(escHash || EN.E.esc, subHash || EN.E.sub[escHash || EN.E.esc]);
  } catch (e) {
    document.getElementById('canvas').replaceChildren(EN.aviso(e.message || String(e), 'error'));
  }
})();
