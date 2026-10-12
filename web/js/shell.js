/* Estructura de la interfaz: paneles laterales, splitters, navegación por escenarios y
   subescenarios, contexto (edificio/año/mes) y atajos de teclado. Misma mecánica que las
   apps OU (ag_ou_eplus_dashboard): ciclos de visibilidad por bits y plegado de un lado. */
(function () {
  'use strict';
  const EN = window.EN;
  const h = EN.h;
  const $ = (id) => document.getElementById(id);

  // ------------------------------------------------------------------ estado

  const CLAVE = 'pgiEnergiaUI';
  const DEF = {
    l1: true, l2: true, r1: false, w1: 230, w2: 250, w3: 420,
    esc: 'panel', sub: {},
    codigo: null, anio: null, mes: 1,
    params: { precioElec: 0.18, precioGas: 0.07, factorElec: 0.18, factorGas: 0.20 },
  };
  const E = (EN.E = {});

  EN.cargarEstado = function () {
    let guardado = {};
    try { guardado = JSON.parse(localStorage.getItem(CLAVE) || '{}'); } catch (e) { /* sin almacenamiento */ }
    Object.assign(E, DEF, guardado);
    E.params = Object.assign({}, DEF.params, guardado.params);
    E.sub = Object.assign({}, guardado.sub);
  };

  let pendiente = null;
  EN.guardar = function () {
    clearTimeout(pendiente);
    pendiente = setTimeout(() => {
      try { localStorage.setItem(CLAVE, JSON.stringify(E)); } catch (e) { /* sin almacenamiento */ }
    }, 150);
  };

  // ----------------------------------------------------------------- paneles

  const PANELES = {
    l1: { panel: 'l1-panel', split: 'l1-splitter', boton: 'l1-fold-btn', ancho: 'w1', min: 170, max: 380 },
    l2: { panel: 'l2-panel', split: 'l2-splitter', boton: 'l2-fold-btn', ancho: 'w2', min: 170, max: 420 },
    r1: { panel: 'r1-panel', split: 'r1-splitter', boton: 'r1-fold-btn', ancho: 'w3', min: 260, max: 600, lado: 'der' },
  };

  EN.setPanel = function (id, visible, guardar = true) {
    const p = PANELES[id];
    E[id] = visible;
    $(p.panel).classList.toggle('hidden', !visible);
    $(p.split).classList.toggle('folded', !visible);
    // La flecha apunta hacia donde se esconde el panel: izquierda para los de la izquierda y derecha para el de la derecha.
    const hacia = p.lado === 'der' ? ['▸', '◂'] : ['◂', '▸'];
    $(p.boton).textContent = visible ? hacia[0] : hacia[1];
    if (guardar) EN.guardar();
  };

  function hacerSplitter(id) {
    const p = PANELES[id];
    const split = $(p.split);
    const panel = $(p.panel);
    panel.style.width = `${E[p.ancho]}px`;

    split.addEventListener('mousedown', (ev) => {
      if (ev.target.id === p.boton || !E[id]) return;
      ev.preventDefault();
      const x0 = ev.clientX;
      const w0 = panel.getBoundingClientRect().width;
      split.classList.add('dragging');
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'col-resize';
      const mover = (e) => {
        const desplazamiento = p.lado === 'der' ? x0 - e.clientX : e.clientX - x0;
        const w = Math.min(p.max, Math.max(p.min, w0 + desplazamiento));
        panel.style.width = `${w}px`;
        E[p.ancho] = w;
      };
      const soltar = () => {
        document.removeEventListener('mousemove', mover);
        document.removeEventListener('mouseup', soltar);
        split.classList.remove('dragging');
        document.body.style.userSelect = '';
        document.body.style.cursor = '';
        EN.guardar();
      };
      document.addEventListener('mousemove', mover);
      document.addEventListener('mouseup', soltar);
    });

    $(p.boton).addEventListener('click', (ev) => {
      ev.stopPropagation();
      EN.setPanel(id, !E[id]);
    });
  }

  // Ciclo de los paneles de la izquierda [escenarios, subescenarios]: 00 → 10 → 11 → 01 → 00
  // (la misma secuencia que usa OU con tablas + pasos). Se calcula siempre desde el estado real.
  const CICLO_IZQUIERDA = [[0, 0], [1, 0], [1, 1], [0, 1]];

  EN.ciclarIzquierda = function () {
    const actual = [E.l1, E.l2].map((v) => (v ? '1' : '0')).join('');
    const i = CICLO_IZQUIERDA.findIndex((s) => s.join('') === actual);
    const sig = CICLO_IZQUIERDA[(i + 1) % CICLO_IZQUIERDA.length];
    EN.setPanel('l1', sig[0] === 1, false);
    EN.setPanel('l2', sig[1] === 1, false);
    EN.guardar();
    EN.toast(`Paneles: ${actual} → ${sig.join('')} (escenarios · subescenarios)`);
  };

  EN.plegarIzquierda = function () {
    EN.setPanel('l1', false, false);
    EN.setPanel('l2', false, false);
    EN.guardar();
    EN.toast('Paneles izquierda: todos plegados');
  };

  // Panel de la derecha (detalle): con un solo panel el ciclo es 0 ↔ 1; Ctrl+Shift+→ lo pliega.
  EN.ciclarDerecha = function () {
    const antes = E.r1 ? '1' : '0';
    EN.setPanel('r1', !E.r1);
    EN.toast(`Paneles derecha: ${antes} → ${E.r1 ? '1' : '0'} (detalle)`);
  };

  EN.plegarDerecha = function () {
    EN.setPanel('r1', false);
    EN.toast('Paneles derecha: todos plegados');
  };

  const HINT_DETALLE = 'Elige un elemento en el canvas para ver aquí su detalle.';

  EN.detalle = {
    /** Muestra `nodo` en el panel derecho (y lo abre si estaba plegado). */
    abrir(titulo, nodo) {
      $('r1-title').textContent = titulo;
      $('r1-body').replaceChildren(nodo);
      if (!E.r1) EN.setPanel('r1', true);
    },
    /** Vacía el panel al cambiar de vista, sin cambiar si está abierto o plegado. */
    limpiar() {
      $('r1-title').textContent = 'Detalle';
      $('r1-body').replaceChildren(h('div', { class: 'detalle-vacio', text: HINT_DETALLE }));
    },
  };

  // -------------------------------------------------------------- navegación

  const escenarioActual = () => EN.ESCENARIOS.find((e) => e.id === E.esc) || EN.ESCENARIOS[0];

  EN.montarNavegacion = function () {
    const lista = $('scenarios-list');
    lista.replaceChildren();
    EN.ESCENARIOS.forEach((esc, i) => {
      lista.appendChild(h('div', {
        class: 'nav-item', role: 'button', tabindex: '0', dataset: { esc: esc.id },
        title: `${esc.titulo} (Alt+${i + 1})`,
        onclick: () => EN.irA(esc.id),
        onkeydown: (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); EN.irA(esc.id); } },
      }, h('span', { class: 'nav-icono' }, EN.icono(esc.icono, 16)), h('span', { text: esc.titulo })));
    });
  };

  function pintarSubescenarios(esc) {
    $('l2-title').textContent = esc.titulo;
    const lista = $('subs-list');
    lista.replaceChildren();
    let grupo = null;
    esc.subs.forEach((sub) => {
      if (sub.grupo && sub.grupo !== grupo) {
        grupo = sub.grupo;
        lista.appendChild(h('div', { class: 'nav-grupo', text: grupo }));
      }
      lista.appendChild(h('div', {
        class: 'nav-item', role: 'button', tabindex: '0', dataset: { sub: sub.id }, title: sub.titulo,
        onclick: () => EN.irA(esc.id, sub.id),
        onkeydown: (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); EN.irA(esc.id, sub.id); } },
      }, h('span', { text: sub.titulo })));
    });
  }

  let ficha = 0;

  async function renderVista(sub) {
    const mia = ++ficha;
    EN.limpiarGraficos();
    EN.detalle.limpiar();
    EN.comandosVista = null;
    EN.paleta.abortar();
    const canvas = $('canvas');
    canvas.replaceChildren(h('div', { class: 'cargando', text: 'Cargando…' }));
    let nodo;
    try {
      nodo = await sub.render(EN.contexto());
    } catch (e) {
      nodo = EN.aviso(e.message || String(e), 'error');
    }
    if (mia !== ficha) return; // llegó tarde: ya se pidió otra vista
    canvas.replaceChildren(nodo || '');
  }

  EN.irA = function (escId, subId) {
    const esc = EN.ESCENARIOS.find((e) => e.id === escId) || EN.ESCENARIOS[0];
    const sub = esc.subs.find((s) => s.id === (subId || E.sub[esc.id])) || esc.subs[0];
    const cambioEsc = E.esc !== esc.id || !$('subs-list').children.length;
    E.esc = esc.id;
    E.sub[esc.id] = sub.id;
    EN.guardar();
    try { history.replaceState(null, '', `${location.pathname}${location.search}#${esc.id}/${sub.id}`); } catch (e) { /* sin historial */ }

    if (cambioEsc) pintarSubescenarios(esc);
    document.querySelectorAll('#scenarios-list .nav-item').forEach((n) => n.classList.toggle('activo', n.dataset.esc === esc.id));
    document.querySelectorAll('#subs-list .nav-item').forEach((n) => {
      const activo = n.dataset.sub === sub.id;
      n.classList.toggle('activo', activo);
      if (activo) n.scrollIntoView({ block: 'nearest' });
    });
    $('crumb').replaceChildren(
      h('span', { class: 'crumb-icono' }, EN.icono(esc.icono, 15)), ` ${esc.titulo}`, h('span', { class: 'sep', text: '›' }),
      sub.grupo ? `${sub.grupo} ` : '', sub.grupo ? h('span', { class: 'sep', text: '›' }) : '', sub.titulo);
    renderVista(sub);
  };

  EN.refrescar = () => EN.irA(E.esc, E.sub[E.esc]);

  function moverSub(delta) {
    const esc = escenarioActual();
    const i = esc.subs.findIndex((s) => s.id === E.sub[esc.id]);
    const j = Math.min(esc.subs.length - 1, Math.max(0, (i < 0 ? 0 : i) + delta));
    if (j !== i) EN.irA(esc.id, esc.subs[j].id);
  }

  function moverEscenario(delta) {
    const i = EN.ESCENARIOS.findIndex((e) => e.id === E.esc);
    const j = Math.min(EN.ESCENARIOS.length - 1, Math.max(0, i + delta));
    if (j !== i) EN.irA(EN.ESCENARIOS[j].id);
  }

  // ---------------------------------------------------------------- contexto

  EN.contexto = function () {
    const ed = (EN.edificios || []).find((e) => e.codigo_proyecto === E.codigo) || null;
    return { codigo: ed ? ed.codigo_proyecto : null, edificio: ed, anio: E.anio, mes: E.mes, params: E.params, cfg: EN.cfg };
  };

  function textoContexto() {
    const ed = EN.contexto().edificio;
    if (!ed) return 'Sin edificio activo';
    return `${ed.codigo_proyecto} · ${ed.nombre} · ${EN.nombreMes(E.mes)} ${E.anio}`;
  }

  function pintarTextoContexto() {
    $('top-bar-context').textContent = textoContexto();
    $('canvas-ctx').textContent = textoContexto();
  }

  let fichaInfo = 0;

  async function pintarInfoContexto() {
    const mia = ++fichaInfo;
    const info = $('ctx-info');
    const ed = EN.contexto().edificio;
    if (!ed) {
      info.replaceChildren('Crea un edificio activo para empezar (Edificios › Crear).');
      return;
    }
    const superficie = h('div', { text: `Superficie: ${EN.num(ed.superficie_m2)} m²` });
    info.replaceChildren(superficie);
    try {
      const d = await EN.datos(`/api/simulaciones?${EN.qs({ codigo: ed.codigo_proyecto })}`);
      if (mia !== fichaInfo) return; // se pidió otra actualización mientras cargaba
      const activa = d.simulaciones.find((s) => s.activa);
      info.replaceChildren(superficie, h('div', {
        class: activa ? 'ok' : 'aviso-txt',
        text: activa ? `Sim. activa: ${activa.nombre_simulacion}` : 'Sin simulación activa',
      }));
    } catch (e) { /* la información extra no es imprescindible */ }
  }

  function rellenarSelectores() {
    const sel = $('ctx-edificio');
    sel.replaceChildren();
    if (!EN.edificios.length) sel.appendChild(h('option', { value: '', text: '— sin edificios —' }));
    EN.edificios.forEach((e) => sel.appendChild(h('option', { value: e.codigo_proyecto, text: `${e.codigo_proyecto} - ${e.nombre}` })));
    sel.value = E.codigo || '';
  }

  EN.recargarEdificios = async function () {
    const d = await EN.api('/api/edificios?todos=1');
    EN.edificiosTodos = d.edificios;
    EN.edificios = d.edificios.filter((e) => e.estado === 'ACTIVO');
    if (!EN.edificios.some((e) => e.codigo_proyecto === E.codigo)) {
      E.codigo = EN.edificios.length ? EN.edificios[0].codigo_proyecto : null;
      EN.guardar();
    }
    rellenarSelectores();
    pintarTextoContexto();
    pintarInfoContexto();
  };

  EN.montarContexto = function () {
    const mes = $('ctx-mes');
    EN.cfg.meses.forEach((m) => mes.appendChild(h('option', { value: m.num, text: `${String(m.num).padStart(2, '0')} - ${m.nombre}` })));
    mes.value = E.mes;
    $('ctx-anio').value = E.anio;
    rellenarSelectores();

    const alCambiar = () => {
      EN.guardar();
      pintarTextoContexto();
      pintarInfoContexto();
      EN.refrescar();
    };
    $('ctx-edificio').addEventListener('change', (e) => { E.codigo = e.target.value || null; e.target.blur(); alCambiar(); });
    mes.addEventListener('change', (e) => { E.mes = Number(e.target.value); e.target.blur(); alCambiar(); });
    $('ctx-anio').addEventListener('change', (e) => {
      const v = Math.round(Number(e.target.value));
      if (v >= 2000 && v <= 2100) { E.anio = v; alCambiar(); } else e.target.value = E.anio;
    });
    pintarTextoContexto();
    pintarInfoContexto();
  };

  /** Tras crear, importar o activar algo: vuelve a pedir los datos y repinta. */
  EN.alCambiarDatos = async function () {
    EN.invalidar();
    await EN.recargarEdificios();
  };

  // ------------------------------------------------------------------ paleta

  /** Comandos que existen en cualquier vista: ir a un escenario o subescenario y manejar los paneles. */
  function comandosGlobales() {
    const ir = [];
    EN.ESCENARIOS.forEach((esc) => esc.subs.forEach((sub) => ir.push({
      id: `ir:${esc.id}/${sub.id}`, titulo: `${esc.titulo} › ${sub.grupo ? `${sub.grupo} · ` : ''}${sub.titulo}`, grupo: 'Ir a',
      run: () => EN.irA(esc.id, sub.id),
    })));
    return [
      { id: 'paneles_izquierda', titulo: '/paneles_izquierda', desc: 'Cicla los paneles de la izquierda (Ctrl+←)', grupo: 'Paneles', run: () => EN.ciclarIzquierda() },
      { id: 'plegar_paneles', titulo: '/plegar_paneles', desc: 'Pliega los paneles de la izquierda y el de detalle', grupo: 'Paneles', run: () => { EN.plegarIzquierda(); EN.setPanel('r1', false); } },
      { id: 'panel_detalle', titulo: '/panel_detalle', desc: 'Abre o cierra el panel de detalle de la derecha (Ctrl+→)', grupo: 'Paneles', run: () => EN.ciclarDerecha() },
      {
        id: 'recargar_datos', titulo: '/recargar_datos', desc: 'Vuelve a pedir los datos al servidor y repinta la vista', grupo: 'Datos',
        run: async () => { EN.invalidar(); await EN.recargarEdificios(); EN.refrescar(); },
      },
    ].concat(ir);
  }

  /** Ctrl+/: la paleta sustituye al canvas, se filtra a pantalla completa y el comando elegido se aplica
      sobre el canvas que había antes. Primero los comandos de la vista (EN.comandosVista), luego los generales. */
  EN.abrirPaleta = async function () {
    if (EN.paleta.abierta()) return;
    const esc = escenarioActual();
    const sub = esc.subs.find((s) => s.id === E.sub[esc.id]) || esc.subs[0];
    const delVista = typeof EN.comandosVista === 'function' ? EN.comandosVista() : [];
    const todos = delVista.concat(comandosGlobales());
    const id = await EN.paleta.lista({
      titulo: 'Comandos', contexto: `${esc.titulo} › ${sub.titulo}`, placeholder: 'Escribe para filtrar: un comando de la vista o a dónde ir…',
      items: todos.map((c) => ({ id: c.id, titulo: c.titulo, desc: c.desc, grupo: c.grupo })),
    });
    const elegido = todos.find((c) => c.id === id);
    if (elegido) await elegido.run();
  };

  // ------------------------------------------------------------------ teclado

  const esTexto = (el) => el && (el.tagName === 'TEXTAREA' || (el.tagName === 'INPUT' && ['text', 'number', 'search'].includes(el.type)));
  const esEdicion = (el) => el && (el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable
    || (el.tagName === 'INPUT' && !['checkbox', 'radio', 'button', 'file', 'submit'].includes(el.type)));

  function alPulsarTecla(e) {
    const activo = document.activeElement;

    // Con la paleta de comandos abierta (ocupa el canvas), el teclado es suyo.
    if (document.querySelector('.paleta-lienzo')) return;

    // Ctrl+/: paleta de comandos (los de la vista actual y, debajo, ir a cualquier escenario).
    if (e.ctrlKey && !e.altKey && !e.metaKey && e.key === '/') {
      e.preventDefault();
      EN.abrirPaleta();
      return;
    }

    if (e.key === 'Escape' && activo && activo !== document.body) { activo.blur(); return; }

    // Ctrl+←/→: paneles. Con un campo de texto con foco se deja pasar el atajo nativo (cursor por palabra).
    if (e.ctrlKey && !e.altKey && !e.metaKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
      if (esTexto(activo)) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      if (e.key === 'ArrowLeft') { if (e.shiftKey) EN.plegarIzquierda(); else EN.ciclarIzquierda(); }
      else if (e.shiftKey) EN.plegarDerecha();
      else EN.ciclarDerecha();
      return;
    }

    // Ctrl+↑/↓: escenario anterior/siguiente.
    if (e.ctrlKey && !e.altKey && !e.shiftKey && !e.metaKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
      if (activo && activo.tagName === 'TEXTAREA') return;
      e.preventDefault();
      moverEscenario(e.key === 'ArrowDown' ? 1 : -1);
      return;
    }

    // ↑/↓: subescenario anterior/siguiente (si no se está editando un campo).
    if (!e.ctrlKey && !e.altKey && !e.shiftKey && !e.metaKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
      if (esEdicion(activo)) return;
      e.preventDefault();
      moverSub(e.key === 'ArrowDown' ? 1 : -1);
      return;
    }

    // Alt+1…9 y Alt+0 (el décimo): escenario directo.
    if (e.altKey && !e.ctrlKey && !e.metaKey && /^[0-9]$/.test(e.key)) {
      const esc = EN.ESCENARIOS[(Number(e.key) || 10) - 1];
      if (esc) { e.preventDefault(); EN.irA(esc.id); }
    }
  }

  EN.montarShell = function () {
    hacerSplitter('l1');
    hacerSplitter('l2');
    hacerSplitter('r1');
    EN.setPanel('l1', E.l1, false);
    EN.setPanel('l2', E.l2, false);
    EN.setPanel('r1', E.r1, false);
    $('r1-cerrar').addEventListener('click', () => EN.setPanel('r1', false));
    EN.detalle.limpiar();
    document.addEventListener('keydown', alPulsarTecla, true);
  };
})();
