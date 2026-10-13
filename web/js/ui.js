/* Utilidades de interfaz: DOM, formatos, tablas, gráficos, formularios y API.
   Todo cuelga del espacio de nombres EN (window.EN). Sin dependencias salvo Plotly. */
(function () {
  'use strict';
  const EN = (window.EN = window.EN || {});

  // ------------------------------------------------------------------ DOM

  /** h('div', {class:'x', onclick: fn}, hijo1, [hijo2, hijo3], 'texto') */
  EN.h = function h(tag, attrs, ...hijos) {
    const el = document.createElement(tag);
    const props = {};
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === undefined || v === null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k === 'dataset') Object.assign(el.dataset, v);
      else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else if (['value', 'checked', 'disabled', 'selected', 'multiple', 'readOnly'].includes(k)) props[k] = v;
      else el.setAttribute(k, v === true ? '' : v);
    }
    const añadir = (hijo) => {
      if (hijo === null || hijo === undefined || hijo === false) return;
      if (Array.isArray(hijo)) hijo.forEach(añadir);
      else el.appendChild(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
    };
    hijos.forEach(añadir);
    Object.assign(el, props); // value de un <select> solo vale con las <option> ya puestas
    return el;
  };
  const h = EN.h;

  /** Como replaceChildren, pero ignorando null/undefined/false (el nativo los convertiría en el texto "null"). */
  EN.llenar = function (el, ...hijos) {
    el.replaceChildren(...hijos.flat().filter((x) => x !== null && x !== undefined && x !== false));
    return el;
  };

  // ---------------------------------------------------------------- iconos

  /** Iconos de Lucide (MIT, https://lucide.dev) tomados de iconbuddy
      (https://files.svgcdn.io/lucide/<nombre>.svg). Solo el interior del <svg>: el tamaño y el color
      los pone la app (stroke="currentColor"), igual que OU_ICONOS en las apps OU. Un icono por concepto. */
  EN.ICONOS = {
    'layout-dashboard': '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    'building-2': '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Zm0-10H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2M10 6h4m-4 4h4m-4 4h4m-4 4h4"/>',
    'chart-line': '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="m19 9l-5 5l-4-4l-3 3"/>',
    'gauge': '<path d="m12 14l4-4M3.34 19a10 10 0 1 1 17.32 0"/>',
    'scale': '<path d="m16 16l3-8l3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1ZM2 16l3-8l3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Zm5 5h10M12 3v18M3 7h2c2 0 5-1 7-2c2 1 5 2 7 2h2"/>',
    'file-text': '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><path d="M14 2v6h6m-4 5H8m8 4H8m2-8H8"/>',
    'euro': '<path d="M4 10h12M4 14h9m6-8a7.7 7.7 0 0 0-5.2-2A7.9 7.9 0 0 0 6 12c0 4.4 3.5 8 7.8 8c2 0 3.8-.8 5.2-2"/>',
    'leaf': '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8c0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
    'check': '<path d="M20 6L9 17l-5-5"/>',
    'triangle-alert': '<path d="m21.73 18l-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3M12 9v4m0 4h.01"/>',
    'sliders-horizontal': '<path d="M21 4h-7m-4 0H3m18 8h-9m-4 0H3m18 8h-5m-4 0H3M14 2v4m-6 4v4m8 4v4"/>',
  };

  EN.icono = function (nombre, tam = 16) {
    const interior = EN.ICONOS[nombre];
    if (!interior) return document.createTextNode('');
    const NS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('width', String(tam));
    svg.setAttribute('height', String(tam));
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true');
    svg.classList.add('ou-icono');
    const tmp = document.createElementNS(NS, 'g');
    tmp.innerHTML = interior; // constantes de este fichero, no datos del usuario
    while (tmp.firstChild) svg.appendChild(tmp.firstChild);
    return svg;
  };

  // -------------------------------------------------------------- formatos

  const formatos = {};
  EN.num = function (v, dec = 0) {
    if (v === null || v === undefined || Number.isNaN(v)) return '—';
    const f = formatos[dec] || (formatos[dec] = new Intl.NumberFormat('es-ES', { minimumFractionDigits: dec, maximumFractionDigits: dec }));
    return f.format(v);
  };
  EN.pct = (v, dec = 2) => (v === null || v === undefined ? '—' : `${EN.num(v, dec)} %`);
  EN.kwh = (v) => (v === null || v === undefined ? '—' : `${EN.num(v, 0)} kWh`);

  EN.nombreMes = function (n) {
    const m = ((EN.cfg && EN.cfg.meses) || []).find((x) => x.num === Number(n));
    return m ? m.nombre : String(n);
  };
  const mesEtiqueta = (v) => `${String(v).padStart(2, '0')} · ${EN.nombreMes(v)}`;

  /** Encabezado y formato de cada columna conocida (t = título, d = decimales, fn = formato propio). */
  EN.COLUMNAS = {
    id: { t: 'ID', raw: true },
    codigo_proyecto: { t: 'Código' }, nombre: { t: 'Nombre' }, cliente: { t: 'Cliente' },
    ubicacion: { t: 'Ubicación' }, uso: { t: 'Uso' }, categoria_edificio: { t: 'Categoría edificio' },
    unidad_referencia: { t: 'Unidad referencia' }, valor_unidad_referencia: { t: 'Valor referencia', d: 0 },
    habitaciones: { t: 'Habitaciones', d: 0 }, puestos_trabajo: { t: 'Puestos', d: 0 }, camas: { t: 'Camas', d: 0 },
    horario_uso: { t: 'Horario de uso' }, sistema_climatizacion: { t: 'Sistema climatización' },
    estado: { t: 'Estado' }, observaciones: { t: 'Observaciones' },
    superficie_m2: { t: 'Superficie (m²)', d: 0 },
    anio: { t: 'Año', raw: true }, mes: { t: 'Mes', fn: mesEtiqueta }, categoria: { t: 'Categoría' },
    consumo_kwh: { t: 'Consumo (kWh)', d: 0 }, simulado_kwh: { t: 'Simulado (kWh)', d: 0 },
    real_kwh: { t: 'Real BMS (kWh)', d: 0 }, desviacion_kwh: { t: 'Desviación (kWh)', d: 0 },
    desviacion_pct: { t: 'Desviación (%)', d: 2 },
    electricidad_kwh: { t: 'Electricidad (kWh)', d: 0 }, gas_kwh: { t: 'Gas (kWh)', d: 0 },
    coste_electricidad_eur: { t: 'Electricidad (€)', d: 2 }, coste_gas_eur: { t: 'Gas (€)', d: 2 },
    coste_total_eur: { t: 'Coste total (€)', d: 2 },
    co2_electricidad_kg: { t: 'Electricidad (kgCO₂)', d: 0 }, co2_gas_kg: { t: 'Gas (kgCO₂)', d: 0 },
    co2_total_kg: { t: 'CO₂ total (kgCO₂)', d: 0 },
    indicador_especifico: { t: 'Indicador específico', d: 2 }, unidad_indicador: { t: 'Unidad indicador' },
    nombre_simulacion: { t: 'Simulación' }, descripcion: { t: 'Descripción' },
    activa: { t: 'Activa', nodo: (v) => (v ? EN.icono('check', 14) : null) }, fecha_creacion: { t: 'Creada' },
    nombre_importacion: { t: 'Importación' }, nombre_original_bms: { t: 'Nombre en el BMS' },
    simulacion_id: { t: 'Simulación', raw: true }, consumo_bms_id: { t: 'Importación', raw: true },
  };
  const etiquetaColumna = (c) => (EN.COLUMNAS[c] && EN.COLUMNAS[c].t) || (c.charAt(0).toUpperCase() + c.slice(1).replace(/_/g, ' '));

  // ---------------------------------------------------------------- tablas

  function clasePct(v) {
    const a = Math.abs(v);
    return a <= 10 ? 'pct-ok' : a <= 20 ? 'pct-warn' : 'pct-mal';
  }

  // El semáforo de alertas llega de Python como "🟢 Correcto": se dibuja un punto en vez del emoji.
  const SEMAFORO = { '🟢': 'ok', '🟡': 'warn', '🔴': 'mal' };

  function celda(columna, valor, decimales) {
    const col = EN.COLUMNAS[columna] || {};
    let texto = '';
    let clase = '';
    if (col.nodo) return h('td', { class: col.clase !== undefined ? col.clase : 'icono-celda' }, col.nodo(valor));
    if (columna === 'estado' && typeof valor === 'string') {
      const m = /^(🟢|🟡|🔴)\s*(.*)$/u.exec(valor);
      if (m) return h('td', {}, h('span', { class: `punto ${SEMAFORO[m[1]]}`, 'aria-hidden': 'true' }), m[2]);
    }
    if (valor === null && columna === 'desviacion_pct') return h('td', { class: 'num detalle', text: 's/ sim.', title: 'Hay consumo real pero no consumo simulado' });
    if (valor === null || valor === undefined) texto = '';
    else if (col.fn) texto = col.fn(valor);
    else if (typeof valor === 'number') {
      const dec = col.d !== undefined ? col.d : decimales !== undefined ? decimales : Number.isInteger(valor) ? 0 : 2;
      texto = col.raw ? String(valor) : EN.num(valor, dec);
      clase = 'num';
      if (columna === 'desviacion_pct') clase += ' ' + clasePct(valor);
    } else texto = String(valor);
    return h('td', { class: clase, text: texto });
  }

  /** filas: lista de objetos. o: {columnas, alClic(fila), seleccion(fila), vacio, enFlujo} */
  EN.tabla = function (filas, o = {}) {
    filas = filas || [];
    if (!filas.length) return EN.aviso(o.vacio || 'Sin datos.');
    const cols = o.columnas || Object.keys(filas[0]);
    const numericas = new Set(cols.filter((c) => filas.some((f) => typeof f[c] === 'number') && !(EN.COLUMNAS[c] || {}).fn));
    const thead = h('thead', {}, h('tr', {}, cols.map((c) => h('th', { class: numericas.has(c) ? 'num' : '', text: etiquetaColumna(c) }))));
    const tbody = h('tbody');
    filas.forEach((fila) => {
      const tr = h('tr', { class: o.seleccion && o.seleccion(fila) ? 'sel' : '' }, cols.map((c) => celda(c, fila[c], o.decimales)));
      if (o.alClic) tr.addEventListener('click', () => o.alClic(fila, tr));
      tbody.appendChild(tr);
    });
    return h('div', { class: 'tabla-wrap' + (o.enFlujo ? ' en-flujo' : '') },
      h('table', { class: 'datos' + (o.alClic ? ' clicable' : '') }, thead, tbody));
  };

  // -------------------------------------------------------------- gráficos

  const graficos = [];

  /** Dibuja una figura Plotly (JSON de Python) ocupando todo su contenedor. */
  EN.grafico = function (fig, vacio) {
    if (!fig) return EN.aviso(vacio || 'No hay datos para dibujar.');
    const cont = h('div', { class: 'grafico' });
    let dibujado = false;
    const pintar = () => {
      if (dibujado || !cont.isConnected || !window.Plotly) return;
      dibujado = true;
      const layout = Object.assign({}, fig.layout, {
        autosize: true,
        paper_bgcolor: '#ffffff',
        plot_bgcolor: '#ffffff',
        font: { family: '"Segoe UI", system-ui, sans-serif', size: 13 },
      });
      delete layout.height;
      delete layout.width;
      window.Plotly.newPlot(cont, fig.data, layout, { responsive: true, displaylogo: false });
      const ro = new ResizeObserver(() => { if (cont.isConnected) window.Plotly.Plots.resize(cont); });
      ro.observe(cont);
      graficos.push({ cont, ro });
    };
    // Se dibuja en cuanto el contenedor está en la página: por fotograma o, si no llega (pestaña oculta,
    // navegador sin ventana), por temporizador. `dibujado` evita dibujarlo dos veces.
    requestAnimationFrame(() => requestAnimationFrame(pintar));
    setTimeout(pintar, 60);
    return cont;
  };

  EN.limpiarGraficos = function () {
    graficos.splice(0).forEach((g) => {
      g.ro.disconnect();
      try { window.Plotly.purge(g.cont); } catch (e) { /* ya no estaba dibujado */ }
    });
  };

  // ------------------------------------------------------------ componentes

  EN.aviso = (mensaje, tono) => h('div', { class: 'empty-hint ' + (tono || '') }, mensaje);

  /** Listado a ancho completo de dos columnas (título · valor). Sirve para resúmenes y para formularios.
      secciones: [{titulo, filas: [{t, v | nodo, d, tono}]}]. `nodo` es un elemento (p. ej. un campo
      editable); `tono` (ok | warn | mal) pone delante un punto de gravedad; `d` es un detalle en gris. */
  EN.lista = function (secciones) {
    const cuerpo = h('tbody');
    secciones.forEach((s) => {
      if (s.titulo) cuerpo.appendChild(h('tr', { class: 'seccion' }, h('th', { colspan: '2', text: s.titulo })));
      s.filas.forEach((f) => {
        cuerpo.appendChild(h('tr', {},
          h('td', { class: 'c1', text: f.t }),
          h('td', { class: 'c2' },
            f.tono ? h('span', { class: `punto ${f.tono}`, 'aria-hidden': 'true' }) : null,
            f.nodo || f.v,
            f.d ? h('span', { class: 'detalle', text: ` · ${f.d}` }) : null)));
      });
    });
    return h('div', { class: 'lista-wrap' }, h('table', { class: 'lista' }, cuerpo));
  };

  /** Zona para arrastrar archivos o elegirlos con un clic. alAnadir(File[]) recibe los archivos. */
  EN.zonaArchivos = function ({ texto, accept, multiple, alAnadir }) {
    const entrada = h('input', { type: 'file', accept, multiple: !!multiple, hidden: true });
    const zona = h('div', { class: 'zona-archivos', role: 'button', tabindex: '0' },
      h('span', { text: texto }), h('span', { class: 'detalle', text: 'o pulsa para elegirlos' }), entrada);
    const entregar = (lista) => { const archivos = [...lista]; if (archivos.length) alAnadir(archivos); };
    zona.addEventListener('click', () => entrada.click());
    zona.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); entrada.click(); } });
    entrada.addEventListener('change', () => { entregar(entrada.files); entrada.value = ''; });
    ['dragenter', 'dragover'].forEach((tipo) => zona.addEventListener(tipo, (e) => { e.preventDefault(); zona.classList.add('encima'); }));
    ['dragleave', 'drop'].forEach((tipo) => zona.addEventListener(tipo, () => zona.classList.remove('encima')));
    // Lo soltado sobre la zona lo atiende la zona; no llega al reparto general de la ventana (shell.js).
    zona.addEventListener('drop', (e) => { e.preventDefault(); e.stopPropagation(); entregar(e.dataTransfer.files); });
    return zona;
  };

  /** Semáforo de una desviación porcentual para colorear un KPI. */
  EN.tonoDesviacion = (pct) => {
    if (pct === null || pct === undefined) return '';
    const a = Math.abs(pct);
    return a <= 10 ? 'ok' : a <= 20 ? 'warn' : 'mal';
  };

  // ------------------------------------------------------------ formularios

  /** c: {name, t, tipo (text|number|select|textarea|checkbox|file), valor, opciones, paso, min, max, ph, accept, multiple, filas} */
  EN.campo = function (c) {
    const tipo = c.tipo || 'text';
    let input;
    if (tipo === 'select') {
      input = h('select', { name: c.name }, (c.opciones || []).map((o) => {
        const v = typeof o === 'object' ? o.v : o;
        const t = typeof o === 'object' ? o.t : o;
        return h('option', { value: v, text: t });
      }));
      if (c.valor !== undefined && c.valor !== null) input.value = String(c.valor);
    } else if (tipo === 'textarea') {
      input = h('textarea', { name: c.name, rows: c.filas || 3 });
      input.value = c.valor || '';
    } else if (tipo === 'checkbox') {
      input = h('input', { type: 'checkbox', name: c.name, checked: !!c.valor });
    } else if (tipo === 'file') {
      input = h('input', { type: 'file', name: c.name, accept: c.accept, multiple: !!c.multiple });
    } else {
      input = h('input', { type: tipo, name: c.name, value: c.valor === undefined || c.valor === null ? '' : String(c.valor), step: c.paso, min: c.min, max: c.max, placeholder: c.ph, autocomplete: 'off' });
    }
    const el = h('label', { class: 'campo' + (tipo === 'checkbox' ? ' check' : '') },
      tipo === 'checkbox' ? [input, h('span', { text: c.t })] : [h('span', { text: c.t }), input]);
    return { el, input, t: c.t };
  };

  /** Lee los valores de todos los controles con `name` dentro de un contenedor (los file se saltan). */
  EN.valores = function (raiz) {
    const salida = {};
    raiz.querySelectorAll('[name]').forEach((c) => {
      if (c.type === 'file') return;
      if (c.type === 'checkbox') salida[c.name] = c.checked;
      else if (c.type === 'radio') { if (c.checked) salida[c.name] = c.value; }
      else salida[c.name] = c.value;
    });
    return salida;
  };

  // -------------------------------------------------------------------- API

  EN.api = async function (url, o = {}) {
    const init = { method: o.method || 'GET' };
    if (o.json !== undefined) {
      init.headers = { 'Content-Type': 'application/json' };
      init.body = JSON.stringify(o.json);
    } else if (o.form) init.body = o.form;
    let respuesta;
    try {
      respuesta = await fetch(url, init);
    } catch (e) {
      throw new Error('No se pudo conectar con el servidor. ¿Sigue en marcha?');
    }
    let datos = {};
    try { datos = await respuesta.json(); } catch (e) { /* cuerpo vacío */ }
    if (!respuesta.ok) throw new Error(datos.error || `Error ${respuesta.status}`);
    return datos;
  };

  const memo = new Map();
  /** GET con memoria: la misma URL no se pide dos veces hasta que algo cambie (EN.invalidar). */
  EN.datos = function (url) {
    if (!memo.has(url)) memo.set(url, EN.api(url).catch((e) => { memo.delete(url); throw e; }));
    return memo.get(url);
  };
  EN.invalidar = () => memo.clear();

  /** Modo constructor: de momento abierto a todos. Cuando haya usuarios, solo administradores. */
  EN.esAdmin = () => true;

  // Selecciones que sobreviven mientras se navega (no se guardan en disco).
  EN.sel = { edificio: null, sim: null, bms: null, categorias: null, alertas: null };

  EN.qs = function (obj) {
    const p = new URLSearchParams();
    Object.entries(obj).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') p.set(k, v); });
    return p.toString();
  };

  // ------------------------------------------------------ ayudas para las vistas

  /** Vista a pantalla completa: `arriba` (barra opcional) y `cuerpo` que ocupa el resto. */
  EN.vista = (arriba, cuerpo, scroll) => h('div', { class: 'vista' }, arriba || null,
    h('div', { class: 'cuerpo' + (scroll ? ' scroll' : '') }, cuerpo));

  EN.sinEdificio = () => EN.aviso('No hay edificios activos. Crea uno en Edificios › Crear.');

  EN.consulta = (ctx, extra) => EN.qs(Object.assign({ codigo: ctx.codigo, anio: ctx.anio, mes: ctx.mes }, extra || {}));

  /** Pide /api/<ruta> con el contexto; si el servidor responde con un aviso, lo muestra en el canvas. */
  EN.conDatos = (ruta, extra, construir) => async (ctx) => {
    if (!ctx.codigo) return EN.sinEdificio();
    const d = await EN.datos(`/api/${ruta}?${EN.consulta(ctx, typeof extra === 'function' ? extra(ctx) : extra)}`);
    if (d.aviso) return EN.aviso(d.aviso, 'warn');
    return construir(d, ctx);
  };

  // ------------------------------------------------- paleta de comandos (Ctrl+/)
  // La paleta SUSTITUYE al canvas mientras está abierta (nada de ventanas emergentes): se filtra a pantalla
  // completa y, al elegir o cancelar, vuelve el canvas anterior tal cual y el comando se aplica sobre él.
  // Las preguntas de un comando (tipo de gráfico, color, nombre…) usan el mismo lienzo, una tras otra.

  /** Minúsculas y sin tildes, para que «anadir» encuentre «añadir». */
  const sinTildes = (t) => String(t).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

  const lienzo = { guardado: null, activas: 0, pendientes: new Set() };

  function tomarLienzo(nodo) {
    const canvas = document.getElementById('canvas');
    if (!lienzo.guardado) lienzo.guardado = [...canvas.childNodes];
    canvas.replaceChildren(nodo);
  }

  function devolverLienzo() {
    if (!lienzo.guardado) return;
    document.getElementById('canvas').replaceChildren(...lienzo.guardado);
    lienzo.guardado = null;
  }

  function crearPaleta(titulo, contexto) {
    const input = h('input', { type: 'text', class: 'paleta-input', autocomplete: 'off', spellcheck: 'false' });
    const lista = h('div', { class: 'paleta-lista scroll-area' });
    const pie = h('div', { class: 'paleta-pie' });
    const nodo = h('div', { class: 'paleta-lienzo', role: 'dialog', 'aria-label': titulo },
      h('div', { class: 'paleta-cab' }, h('span', { class: 'paleta-titulo', text: titulo }), contexto ? h('span', { class: 'detalle', text: contexto }) : null),
      input, lista, pie);
    lienzo.activas += 1;
    tomarLienzo(nodo);
    input.focus();
    return { nodo, input, lista, pie };
  }

  /** Cierra una paleta. El canvas anterior vuelve en cuanto no queda ninguna (si el comando encadena otra
      pregunta, la abre antes de que salte el temporizador y el canvas no llega a parpadear). */
  function cerrarPaleta(p, terminar) {
    p.nodo.remove();
    lienzo.pendientes.delete(terminar);
    lienzo.activas = Math.max(0, lienzo.activas - 1);
    setTimeout(() => { if (lienzo.activas === 0) devolverLienzo(); }, 0);
  }

  EN.paleta = {
    /** Se cambió de vista con la paleta abierta: se cancela todo y no se restaura un canvas que ya no existe. */
    abortar() {
      lienzo.guardado = null;
      [...lienzo.pendientes].forEach((t) => t(null));
      lienzo.activas = 0;
    },

    abierta: () => lienzo.activas > 0,

    /** items: [{id, titulo, desc, grupo}]. Devuelve el id elegido (o la lista de ids marcados si `multiple`); null si se cancela. */
    lista({ titulo, contexto, items, multiple = false, valores = [], placeholder = 'Escribe para filtrar…' }) {
      return new Promise((resolve) => {
        const p = crearPaleta(titulo, contexto);
        p.input.placeholder = placeholder;
        const marcados = new Set(valores);
        let activo = 0;
        let visibles = items;
        const terminar = (valor) => { cerrarPaleta(p, terminar); resolve(valor); };
        lienzo.pendientes.add(terminar);

        const elegir = (indice) => {
          const it = visibles[indice];
          if (!it) return;
          if (!multiple) { terminar(it.id); return; }
          if (marcados.has(it.id)) marcados.delete(it.id); else marcados.add(it.id);
          pintar();
        };

        function pintar() {
          const q = sinTildes(p.input.value.trim());
          visibles = items.filter((i) => !q || sinTildes(`${i.titulo} ${i.desc || ''} ${i.grupo || ''}`).includes(q));
          activo = Math.min(activo, Math.max(0, visibles.length - 1));
          const nodos = [];
          let grupo = null;
          visibles.forEach((it, i) => {
            if (it.grupo && it.grupo !== grupo) { grupo = it.grupo; nodos.push(h('div', { class: 'paleta-grupo', text: grupo })); }
            nodos.push(h('div', {
              class: 'paleta-item' + (i === activo ? ' activo' : ''),
              onclick: () => { activo = i; elegir(i); },
            },
            multiple ? h('input', { type: 'checkbox', checked: marcados.has(it.id), tabindex: '-1' }) : null,
            h('span', { class: 'paleta-t', text: it.titulo }),
            it.desc ? h('span', { class: 'detalle', text: it.desc }) : null));
          });
          if (!visibles.length) nodos.push(h('div', { class: 'paleta-vacia', text: 'Nada coincide.' }));
          EN.llenar(p.lista, nodos);
          const el = p.lista.querySelector('.paleta-item.activo');
          if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
        }

        EN.llenar(p.pie, h('span', { class: 'paleta-ayuda', text: multiple ? '↑↓ moverse · Enter marca · Ctrl+Enter aplica · Esc vuelve' : '↑↓ moverse · Enter elige · Esc vuelve' }),
          multiple ? h('button', { class: 'btn-primary btn-mini', type: 'button', text: 'Aplicar', onclick: () => terminar([...marcados]) }) : null,
          h('button', { class: 'btn-secondary btn-mini', type: 'button', text: 'Volver', onclick: () => terminar(null) }));
        p.input.addEventListener('input', () => { activo = 0; pintar(); });
        p.input.addEventListener('keydown', (e) => {
          if (e.key === 'ArrowDown') { e.preventDefault(); activo = Math.min(visibles.length - 1, activo + 1); pintar(); }
          else if (e.key === 'ArrowUp') { e.preventDefault(); activo = Math.max(0, activo - 1); pintar(); }
          else if (e.key === 'PageDown') { e.preventDefault(); activo = Math.min(visibles.length - 1, activo + 8); pintar(); }
          else if (e.key === 'PageUp') { e.preventDefault(); activo = Math.max(0, activo - 8); pintar(); }
          else if (e.key === 'Enter') { e.preventDefault(); if (multiple && e.ctrlKey) terminar([...marcados]); else elegir(activo); }
          else if (e.key === 'Escape' || (e.ctrlKey && e.key === '/')) { e.preventDefault(); terminar(null); }
        });
        pintar();
      });
    },

    /** Pide una línea de texto. Devuelve el texto (o null si se cancela). */
    texto({ titulo, contexto, valor = '', placeholder = '' }) {
      return new Promise((resolve) => {
        const p = crearPaleta(titulo, contexto);
        p.input.value = valor;
        p.input.placeholder = placeholder;
        p.input.select();
        const terminar = (v) => { cerrarPaleta(p, terminar); resolve(v); };
        lienzo.pendientes.add(terminar);
        EN.llenar(p.lista, h('div', { class: 'paleta-vacia', text: 'Escribe el texto y pulsa Enter.' }));
        EN.llenar(p.pie, h('span', { class: 'paleta-ayuda', text: 'Enter acepta · Esc vuelve' }),
          h('button', { class: 'btn-primary btn-mini', type: 'button', text: 'Aceptar', onclick: () => terminar(p.input.value.trim()) }),
          h('button', { class: 'btn-secondary btn-mini', type: 'button', text: 'Volver', onclick: () => terminar(null) }));
        p.input.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') { e.preventDefault(); terminar(p.input.value.trim()); }
          else if (e.key === 'Escape' || (e.ctrlKey && e.key === '/')) { e.preventDefault(); terminar(null); }
        });
      });
    },
  };

  // ------------------------------------------------------------------ toast

  let temporizador = null;
  EN.toast = function (mensaje, ms = 2200) {
    const t = document.getElementById('toast');
    t.textContent = mensaje;
    t.hidden = false;
    clearTimeout(temporizador);
    temporizador = setTimeout(() => { t.hidden = true; }, ms);
  };
})();
