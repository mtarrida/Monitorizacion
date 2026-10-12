/* Escenario Constructor: la tabla de trabajo (datos mensuales) y sus gráficos, con los mismos
   comandos que se usan en las tablas de EnergyPlus HTML++ (ocultar columnas, seleccionar o colorear
   filas, columnas matemáticas, totales, pasos reproducibles, paneles de escena…).
   El motor (tabla_motor.js) calcula la tabla a partir de una base y una lista de pasos; aquí vive
   solo la interfaz: modos de clic, barra de modo, paleta de comandos (Ctrl+/) y el panel de pasos.

   Modo constructor: de momento abierto a todos los usuarios; cuando haya usuarios será solo para
   administradores (ver EN.esAdmin en escenarios.js). */
(function () {
  'use strict';
  const EN = window.EN;
  const h = EN.h;
  const M = EN.motor;

  const CLAVE = 'pgiEnergiaConstructor2';
  const COLORES_FILA = [
    { id: '#fde2e6', titulo: 'Rojo suave' }, { id: '#fff3cd', titulo: 'Amarillo' }, { id: '#d9f2dc', titulo: 'Verde' },
    { id: '#dbeafe', titulo: 'Azul' }, { id: '#e5e7eb', titulo: 'Gris' },
  ];
  const GRAFICO_INICIAL = () => ({ id: 'g1', tipo: 'barras', orient: 'columnas', x: '', ys: ['simulado_kwh', 'real_kwh'], titulo: '' });

  // ------------------------------------------------------------------ estado

  const inicial = () => ({ base: 'largo', pasos: [], graficos: [GRAFICO_INICIAL()], guardados: [], filtroVisible: false, fit: null, contador: 1 });

  function leer() {
    let guardado = {};
    try { guardado = JSON.parse(localStorage.getItem(CLAVE) || '{}'); } catch (e) { guardado = {}; }
    const e = Object.assign(inicial(), guardado);
    // Enlace profundo: ?constructor={"base":"ancho_real","pasos":[...]} aplica ese estado al abrir la página.
    try {
      const enlace = new URLSearchParams(location.search).get('constructor');
      if (enlace) Object.assign(e, JSON.parse(enlace));
    } catch (x) { /* estado no válido: se ignora */ }
    if (!M.BASES[e.base]) e.base = 'largo';
    ['pasos', 'graficos', 'guardados'].forEach((k) => { if (!Array.isArray(e[k])) e[k] = []; });
    return e;
  }
  const estado = leer();
  const guardar = () => { try { localStorage.setItem(CLAVE, JSON.stringify(estado)); } catch (e) { /* sin almacenamiento */ } };

  // Estado de la sesión (no se guarda): datos, tabla calculada, modo activo y marcas.
  const rt = {
    datos: null, base: null, tabla: null, modo: null, marcasCol: new Set(), marcasFila: new Set(),
    filtros: {}, repintar: null, enTabla: false, pendiente: null, pasosVisibles: false, formula: null, cuerpo: null, columnasVisibles: [],
  };

  function recalcular() {
    rt.base = M.crearBase(rt.datos, estado.base);
    rt.tabla = M.aplicarPasos(rt.base, estado.pasos);
  }

  function cambio() {
    guardar();
    recalcular();
    if (rt.repintar) rt.repintar();
    actualizarPasos();
  }

  function anadirPaso(p) { estado.pasos.push(p); cambio(); }

  /** Columnas con su título original (el de la base), para describir pasos sin que un renombrado los confunda. */
  const columnasDescripcion = () => rt.tabla.columnas.map((c) => {
    const original = rt.base.columnas.find((x) => x.id === c.id);
    return original ? { id: c.id, titulo: original.titulo } : c;
  });

  const tituloColumna = (id) => { const c = rt.tabla.columnas.find((x) => x.id === id); return c ? c.titulo : id; };
  const columnasVisibles = () => rt.tabla.columnas.filter((c) => !c.oculta);

  function textoCelda(c, v) {
    if (v === null || v === undefined) return '';
    if (typeof v === 'boolean') return v ? 'TRUE' : 'FALSE';
    if (typeof v === 'number') return EN.num(v, c.dec !== undefined ? c.dec : Number.isInteger(v) ? 0 : 2);
    return String(v);
  }

  async function copiarTexto(texto, aviso) {
    try {
      await navigator.clipboard.writeText(texto);
      EN.toast(aviso || 'Copiado al portapapeles.');
    } catch (e) {
      EN.detalle.abrir('Texto para copiar', h('textarea', { class: 'texto-informe', readOnly: true, rows: 12, value: texto }));
      EN.toast('No se pudo copiar solo: selecciona el texto del panel derecho.');
    }
  }

  // ------------------------------------------------------------------- modos

  function iniciarModo(modo) {
    rt.marcasCol.clear();
    rt.marcasFila.clear();
    rt.modo = modo;
    if (rt.repintar) rt.repintar();
  }

  function terminarModo() {
    rt.modo = null;
    rt.formula = null;
    rt.marcasCol.clear();
    rt.marcasFila.clear();
    if (rt.repintar) rt.repintar();
  }

  function alternarMarca(conjunto, id) {
    if (conjunto.has(id)) conjunto.delete(id); else conjunto.add(id);
    rt.repintar();
  }

  const botonAplicar = (texto, fn) => ({ t: texto, fn, primario: true });

  const MODOS = {
    ocultar_columnas: () => ({
      id: 'ocultar_columnas', titulo: '/ocultar_columnas', texto: 'Pulsa una cabecera para ocultarla o mostrarla. Las ocultas se ven atenuadas mientras dure el modo.',
      mostrarOcultas: true, botones: [], alCabecera: (c) => anadirPaso({ p: 'alternar_columna', id: c.id }),
    }),
    seleccionar_columnas: () => ({
      id: 'seleccionar_columnas', titulo: '/seleccionar_columnas', texto: 'Marca las columnas que quieres CONSERVAR; al aplicar se oculta el resto.',
      botones: [botonAplicar('Aplicar', () => {
        if (!rt.marcasCol.size) { EN.toast('Marca al menos una columna.'); return; }
        anadirPaso({ p: 'seleccionar_columnas', conservar: [...rt.marcasCol] });
        terminarModo();
      })],
      alCabecera: (c) => alternarMarca(rt.marcasCol, c.id),
    }),
    seleccionar_filas: () => ({
      id: 'seleccionar_filas', titulo: '/seleccionar_filas', texto: 'Marca las filas que quieres CONSERVAR; al aplicar se oculta el resto.',
      botones: [botonAplicar('Aplicar', () => {
        if (!rt.marcasFila.size) { EN.toast('Marca al menos una fila.'); return; }
        anadirPaso({ p: 'seleccionar_filas', conservar: [...rt.marcasFila] });
        terminarModo();
      })],
      alFila: (f) => alternarMarca(rt.marcasFila, f.id),
    }),
    colorear_filas: () => ({
      id: 'colorear_filas', titulo: '/colorear_filas', texto: 'Marca filas y elige un color: se pintan todas y siguen visibles (no se oculta nada).',
      botones: [botonAplicar('Elegir color y aplicar', async () => {
        if (!rt.marcasFila.size) { EN.toast('Marca al menos una fila.'); return; }
        const items = COLORES_FILA.map((c) => ({ id: c.id, titulo: c.titulo, desc: c.id })).concat([{ id: '__otro', titulo: 'Otro color…', desc: 'un código #hex' }]);
        let color = await EN.paleta.lista({ titulo: 'Color de las filas', items });
        if (color === '__otro') color = await EN.paleta.texto({ titulo: 'Color en formato #rrggbb', valor: '#' });
        if (!color) return;
        if (!/^#[0-9a-fA-F]{6}$/.test(color)) { EN.toast('El color tiene que ser #rrggbb.'); return; }
        anadirPaso({ p: 'colorear_filas', filas: [...rt.marcasFila], color });
        terminarModo();
      })],
      alFila: (f) => alternarMarca(rt.marcasFila, f.id),
    }),
    mover_columnas_a_despues: () => {
      const modo = {
        id: 'mover_columnas_a_despues', titulo: '/mover_columnas_a_despues', texto: 'Pulsa la columna a mover y luego la columna detrás de la que quedará.',
        origen: null, botones: [],
        alCabecera: (c) => {
          if (!modo.origen) { modo.origen = c.id; rt.marcasCol.clear(); rt.marcasCol.add(c.id); rt.repintar(); return; }
          if (modo.origen === c.id) { modo.origen = null; rt.marcasCol.clear(); rt.repintar(); return; }
          const origen = modo.origen;
          modo.origen = null;
          rt.marcasCol.clear();
          anadirPaso({ p: 'mover_columna', id: origen, despues: c.id });
        },
      };
      return modo;
    },
    cabeceras_cambiar_nombre: () => ({
      id: 'cabeceras_cambiar_nombre', titulo: '/cabeceras_cambiar_nombre', texto: 'Pulsa una cabecera para renombrarla. Termina cuando acabes.', botones: [],
      alCabecera: async (c) => {
        const nuevo = await EN.paleta.texto({ titulo: `Nuevo nombre de «${c.titulo}»`, valor: c.titulo });
        if (nuevo) anadirPaso({ p: 'renombrar', id: c.id, titulo: nuevo });
      },
    }),
    modo_totales: () => ({
      id: 'modo_totales', titulo: '/modo_totales', texto: 'Pulsa las cabeceras numéricas que quieras sumar y aplica los totales (solo suma las filas visibles).',
      botones: [botonAplicar('Aplicar totales', () => {
        if (!rt.marcasCol.size) { EN.toast('Marca al menos una columna.'); return; }
        anadirPaso({ p: 'totales', ids: [...rt.marcasCol] });
        terminarModo();
      })],
      alCabecera: (c) => { if (c.tipo !== 'numero') { EN.toast('Solo se suman columnas numéricas.'); return; } alternarMarca(rt.marcasCol, c.id); },
    }),
    sustituir_en_columna: () => ({
      id: 'sustituir_en_columna', titulo: '/sustituir_en_columna', texto: 'Marca las columnas de texto y pulsa Continuar: te pediré los pares «texto a sustituir → texto nuevo».',
      botones: [botonAplicar('Continuar', async () => {
        if (!rt.marcasCol.size) { EN.toast('Marca al menos una columna.'); return; }
        const ids = [...rt.marcasCol];
        const pares = [];
        for (;;) {
          const de = await EN.paleta.texto({ titulo: `Texto a sustituir (vacío para terminar) · ${pares.length} par(es)`, valor: '' });
          if (!de) break;
          const a = await EN.paleta.texto({ titulo: `«${de}» → texto nuevo (puede quedar vacío)`, valor: '' });
          if (a === null) break;
          pares.push([de, a]);
        }
        if (!pares.length) return;
        anadirPaso({ p: 'sustituir', ids, pares });
        terminarModo();
      })],
      alCabecera: (c) => { if (c.tipo !== 'texto') { EN.toast('Solo se sustituye texto en columnas de texto.'); return; } alternarMarca(rt.marcasCol, c.id); },
    }),
    ordenar_filas: () => ({
      id: 'ordenar_filas', titulo: '/ordenar_filas', texto: 'Pulsa una cabecera para ordenar las filas; otro clic en la misma invierte el orden.', botones: [],
      alCabecera: (c) => {
        const ultimo = [...estado.pasos].reverse().find((p) => p.p === 'ordenar');
        const dir = ultimo && ultimo.id === c.id && ultimo.dir === 'asc' ? 'desc' : 'asc';
        anadirPaso({ p: 'ordenar', id: c.id, dir });
      },
    }),
    anadir_grafico_barras: () => ({
      id: 'anadir_grafico_barras', titulo: '/añadir_grafico_barras', texto: 'Pulsa las cabeceras de las columnas de origen y añade el gráfico de barras.',
      botones: [botonAplicar('Añadir gráfico', () => {
        if (!rt.marcasCol.size) { EN.toast('Marca al menos una columna numérica.'); return; }
        crearGrafico({ tipo: 'barras', orient: 'columnas', x: '', ys: [...rt.marcasCol], titulo: '' });
        terminarModo();
        EN.irA('constructor', 'graficos');
      })],
      alCabecera: (c) => { if (c.tipo !== 'numero') { EN.toast('Solo se dibujan columnas numéricas.'); return; } alternarMarca(rt.marcasCol, c.id); },
    }),
    columnas_matematicas: () => {
      rt.formula = { alias: {}, n: 0, texto: '', nombre: '', error: '' };
      return {
        id: 'columnas_matematicas', titulo: '/columnas_matematicas', botones: [],
        alCabecera: (c) => {
          const ya = Object.entries(rt.formula.alias).find(([, id]) => id === c.id);
          if (ya) { EN.toast(`${tituloColumna(c.id)} ya es ${ya[0]}.`); return; }
          rt.formula.n += 1;
          rt.formula.alias[`C${rt.formula.n}`] = c.id;
          rt.repintar();
        },
      };
    },
  };

  // ------------------------------------------------------------ barra de modo

  function nodoFormula() {
    const f = rt.formula;
    const chips = Object.entries(f.alias).map(([alias, id]) => h('span', {
      class: 'chip on', role: 'button', tabindex: '0', title: 'Quitar esta columna',
      onclick: () => { delete f.alias[alias]; rt.repintar(); },
    }, `${alias} = ${tituloColumna(id)}  ✕`));

    const entrada = h('input', { type: 'text', class: 'formula-input', value: f.texto, placeholder: '(C1+C2)*C3', autocomplete: 'off', spellcheck: 'false', 'aria-label': 'Fórmula' });
    const nombre = h('input', { type: 'text', class: 'formula-nombre', value: f.nombre, placeholder: 'Título de la columna nueva', autocomplete: 'off', 'aria-label': 'Título de la columna' });
    const aviso = h('span', { class: 'formula-aviso' });
    const previa = () => {
      f.texto = entrada.value;
      aviso.className = 'formula-aviso';
      if (!f.texto.trim()) { aviso.textContent = 'Pulsa las cabeceras para añadir columnas (C1, C2…) y escribe la fórmula.'; return; }
      try {
        const arbol = M.parsear(f.texto);
        const desconocidos = [...M.identificadores(arbol)].filter((n) => !f.alias[n]);
        if (desconocidos.length) throw new Error(`Alias sin columna: ${desconocidos.join(', ')}.`);
        const fila = rt.tabla.filas.find((x) => !x.oculta && !x.total);
        const valores = {};
        Object.entries(f.alias).forEach(([a, id]) => { valores[a] = fila && fila.v[id] !== undefined ? fila.v[id] : null; });
        const v = M.evaluarFormula(f.texto, valores);
        aviso.textContent = `Primera fila: ${v === null ? 'vacío' : typeof v === 'boolean' ? (v ? 'TRUE' : 'FALSE') : typeof v === 'number' ? EN.num(v, 2) : v}`;
      } catch (e) {
        aviso.className = 'formula-aviso mal';
        aviso.textContent = e.message;
      }
    };
    entrada.addEventListener('input', previa);
    nombre.addEventListener('input', () => { f.nombre = nombre.value; });

    const insertar = (texto) => {
      const i = entrada.selectionStart === null ? entrada.value.length : entrada.selectionStart;
      const j = entrada.selectionEnd === null ? i : entrada.selectionEnd;
      entrada.value = entrada.value.slice(0, i) + texto + entrada.value.slice(j);
      entrada.focus();
      const p = i + texto.length;
      entrada.setSelectionRange(p, p);
      previa();
    };
    const plantillas = ['+', '-', '*', '/', '(', ')', ',', '<', '<=', '>', '>=', '=', '<>', 'IF(', 'AND(', 'OR(', 'NOT(', 'ABS(', 'ROUND(', 'MIN(', 'MAX(', 'SUM(', 'AVG(']
      .map((t) => h('button', { class: 'btn-secondary btn-mini', type: 'button', text: t, onclick: () => insertar(t) }));

    const crear = () => {
      previa();
      if (aviso.classList.contains('mal') || !f.texto.trim()) { EN.toast('Revisa la fórmula antes de crear la columna.'); return; }
      anadirPaso({ p: 'formula', id: M.idColumnaNueva(estado.pasos), titulo: f.nombre.trim() || 'Resultado', formula: f.texto, alias: Object.assign({}, f.alias) });
      terminarModo();
    };

    previa();
    return h('div', { class: 'modo-barra formula-panel' },
      h('div', { class: 'formula-fila' }, h('strong', { text: '/columnas_matematicas' }), h('span', { text: 'Pulsa cabeceras de la tabla para usarlas como C1, C2… en la fórmula.' })),
      h('div', { class: 'formula-fila' }, chips.length ? chips : h('span', { class: 'detalle', text: 'Ninguna columna elegida todavía.' })),
      h('div', { class: 'formula-fila' }, entrada, nombre),
      h('div', { class: 'formula-fila' }, plantillas),
      h('div', { class: 'formula-fila' }, aviso,
        h('button', { class: 'btn-primary', type: 'button', text: 'Crear columna', onclick: crear }),
        h('button', { class: 'btn-secondary', type: 'button', text: 'Cancelar', onclick: terminarModo })));
  }

  function nodoBarraModo() {
    const m = rt.modo;
    if (!m) return null;
    if (m.id === 'columnas_matematicas') return nodoFormula();
    return h('div', { class: 'modo-barra' },
      h('strong', { text: m.titulo }), h('span', { class: 'modo-texto', text: m.texto }),
      (m.botones || []).map((b) => h('button', { class: b.primario ? 'btn-primary' : 'btn-secondary', type: 'button', text: b.t, onclick: b.fn })),
      h('button', { class: 'btn-secondary', type: 'button', text: (m.botones || []).length ? 'Cancelar' : 'Terminar', onclick: terminarModo }));
  }

  // ------------------------------------------------------------------- tabla

  function claseCabecera(c) {
    const m = rt.modo;
    const clases = [c.tipo === 'numero' ? 'num' : ''];
    if (m && m.alCabecera) clases.push('th-modo');
    if (rt.marcasCol.has(c.id)) clases.push('marcada');
    if (c.oculta) clases.push('oculta-modo');
    return clases.join(' ');
  }

  function filaTabla(f, columnas) {
    const clases = [];
    if (f.total) clases.push('fila-total');
    if (rt.marcasFila.has(f.id)) clases.push('marcada');
    if (rt.modo && rt.modo.alFila && !f.total) clases.push('fila-modo');
    const tr = h('tr', { class: clases.join(' ') }, columnas.map((c) => (c.oculta
      ? h('td', { class: 'oculta-modo' })
      : h('td', { class: c.tipo === 'numero' ? 'num' : '', text: textoCelda(c, f.v[c.id]) }))));
    if (f.color) tr.style.background = f.color;
    if (rt.modo && rt.modo.alFila && !f.total) tr.addEventListener('click', () => rt.modo.alFila(f));
    return tr;
  }

  function pintarCuerpo() {
    const columnas = rt.columnasVisibles;
    const pasa = (f) => columnas.every((c) => {
      const q = (rt.filtros[c.id] || '').trim().toLowerCase();
      return !q || textoCelda(c, f.v[c.id]).toLowerCase().includes(q);
    });
    const filas = rt.tabla.filas.filter((f) => !f.oculta && (f.total || pasa(f)));
    EN.llenar(rt.cuerpo, filas.map((f) => filaTabla(f, columnas)));
    return filas.length;
  }

  function nodoTabla() {
    const columnas = rt.tabla.columnas.filter((c) => !c.oculta || (rt.modo && rt.modo.mostrarOcultas));
    rt.columnasVisibles = columnas;
    const cabecera = h('tr', {}, columnas.map((c) => h('th', {
      class: claseCabecera(c), text: c.titulo, title: c.calculada ? `Columna calculada: ${c.formula}` : c.titulo,
      onclick: () => { if (rt.modo && rt.modo.alCabecera) rt.modo.alCabecera(c); },
    })));
    const filtros = estado.filtroVisible
      ? h('tr', { class: 'fila-filtros' }, columnas.map((c) => {
        const caja = h('input', { type: 'text', value: rt.filtros[c.id] || '', placeholder: 'filtrar…', autocomplete: 'off', 'aria-label': `Filtrar ${c.titulo}` });
        caja.addEventListener('input', () => { rt.filtros[c.id] = caja.value; pintarCuerpo(); });
        return h('th', {}, caja);
      }))
      : null;
    rt.cuerpo = h('tbody');
    pintarCuerpo();
    return h('div', { class: 'tabla-wrap' }, h('table', { class: 'datos tabla-trabajo' }, h('thead', {}, cabecera, filtros), rt.cuerpo));
  }

  function nodoChips() {
    const visibles = rt.tabla.filas.filter((f) => !f.oculta && !f.total).length;
    const total = rt.tabla.filas.filter((f) => !f.total).length;
    const chip = (etiqueta, valor, id) => h('button', { class: 'chip-espec', type: 'button', title: `/${id}`, onclick: () => ejecutar(id) },
      h('span', { class: 'detalle', text: `${etiqueta}: ` }), valor);
    return h('div', { class: 'barra-herramientas barra-espec' },
      chip('Datos', M.BASES[estado.base], 'datos_de_origen'),
      chip('Filas', `${visibles} de ${total}`, 'seleccionar_filas'),
      chip('Pasos', String(estado.pasos.length), 'ver_pasos'),
      chip('Gráficos', String(estado.graficos.length), 'paneles_de_escena'),
      h('button', { class: 'btn-primary', type: 'button', text: 'Comandos  Ctrl+/', onclick: () => EN.abrirPaleta() }),
      h('button', { class: 'btn-secondary', type: 'button', text: 'Deshacer', disabled: !estado.pasos.length, onclick: () => deshacer() }));
  }

  // ---------------------------------------------------------------- gráficos

  function crearGrafico(cfg) {
    estado.contador += 1;
    estado.graficos.push(Object.assign({ id: `g${estado.contador}` }, cfg));
    estado.fit = null;
    guardar();
  }

  async function pedirGrafico(previo) {
    const base = previo || { tipo: 'barras', orient: 'columnas', x: '', ys: [], titulo: '' };
    const tipo = await EN.paleta.lista({ titulo: 'Tipo de gráfico', items: Object.entries(M.TIPOS_GRAFICO).map(([id, t]) => ({ id, titulo: t })) });
    if (!tipo) return null;
    const orient = await EN.paleta.lista({
      titulo: '¿Qué es una serie?',
      items: [
        { id: 'columnas', titulo: 'Una serie por columna', desc: 'las filas son las categorías del eje' },
        { id: 'filas', titulo: 'Una serie por fila', desc: 'el eje son las columnas elegidas, p. ej. los meses' },
      ],
    });
    if (!orient) return null;
    let x = '';
    if (orient === 'columnas') {
      const textos = rt.tabla.columnas.filter((c) => c.tipo === 'texto');
      const elegido = await EN.paleta.lista({
        titulo: 'Etiquetas del eje', items: [{ id: '', titulo: 'Todas las columnas de texto', desc: 'por defecto' }].concat(textos.map((c) => ({ id: c.id, titulo: c.titulo }))),
      });
      if (elegido === null) return null;
      x = elegido;
    }
    const numericas = rt.tabla.columnas.filter((c) => c.tipo === 'numero');
    if (!numericas.length) { EN.toast('No hay columnas numéricas que dibujar.'); return null; }
    const ys = await EN.paleta.lista({
      titulo: orient === 'filas' ? 'Columnas del eje (en orden de la tabla)' : 'Columnas a dibujar', multiple: true, valores: base.ys,
      items: numericas.map((c) => ({ id: c.id, titulo: c.titulo, desc: c.oculta ? 'oculta' : '' })),
    });
    if (!ys || !ys.length) return null;
    const titulo = await EN.paleta.texto({ titulo: 'Título (vacío = automático)', valor: base.titulo || '' });
    if (titulo === null) return null;
    return { tipo, orient, x, ys: numericas.map((c) => c.id).filter((id) => ys.includes(id)), titulo };
  }

  async function menuPaneles() {
    const accion = await EN.paleta.lista({
      titulo: 'Paneles de escena (gráficos)',
      items: [{ id: 'anadir', titulo: 'Añadir un gráfico…' }, { id: 'editar', titulo: 'Editar un gráfico…' }, { id: 'quitar', titulo: 'Quitar un gráfico…' }],
    });
    if (!accion) return;
    const elegirExistente = (titulo) => EN.paleta.lista({
      titulo, items: estado.graficos.map((g, i) => ({ id: g.id, titulo: g.titulo || `Gráfico ${i + 1}`, desc: M.TIPOS_GRAFICO[g.tipo] })),
    });
    if (accion === 'anadir') {
      const cfg = await pedirGrafico(null);
      if (cfg) { crearGrafico(cfg); EN.irA('constructor', 'graficos'); }
    } else if (!estado.graficos.length) {
      EN.toast('Todavía no hay gráficos.');
    } else if (accion === 'editar') {
      const id = await elegirExistente('¿Qué gráfico editas?');
      const actual = estado.graficos.find((g) => g.id === id);
      if (!actual) return;
      const cfg = await pedirGrafico(actual);
      if (cfg) { Object.assign(actual, cfg); guardar(); if (rt.repintar) rt.repintar(); }
    } else {
      const id = await elegirExistente('¿Qué gráfico quitas?');
      if (!id) return;
      estado.graficos = estado.graficos.filter((g) => g.id !== id);
      if (estado.fit === id) estado.fit = null;
      guardar();
      if (rt.repintar) rt.repintar();
    }
  }

  function panelEscena(cfg, indice) {
    const fig = M.construirGrafico(rt.tabla, cfg);
    const ampliado = estado.fit === cfg.id;
    const cuerpo = h('div', { class: 'panel-escena-cuerpo' },
      fig ? EN.grafico(fig) : EN.aviso('Este gráfico usa columnas que ya no existen o no hay filas visibles. Edítalo o quítalo.', 'warn'));
    return h('div', { class: 'panel-escena' },
      h('div', { class: 'panel-escena-cab' },
        h('span', { class: 'titulo', text: cfg.titulo || `Gráfico ${indice + 1} · ${M.TIPOS_GRAFICO[cfg.tipo]}` }),
        h('button', { class: 'btn-secondary btn-mini', type: 'button', text: ampliado ? 'Restaurar' : 'Ampliar', onclick: () => { estado.fit = ampliado ? null : cfg.id; guardar(); rt.repintar(); } }),
        h('button', { class: 'btn-secondary btn-mini', type: 'button', text: 'Editar', onclick: async () => { const n = await pedirGrafico(cfg); if (n) { Object.assign(cfg, n); guardar(); rt.repintar(); } } }),
        h('button', { class: 'btn-secondary btn-mini', type: 'button', title: 'Quitar este gráfico', text: '✕', onclick: () => { estado.graficos = estado.graficos.filter((g) => g.id !== cfg.id); if (estado.fit === cfg.id) estado.fit = null; guardar(); rt.repintar(); } })),
      cuerpo);
  }

  function nodoGraficos() {
    EN.limpiarGraficos();
    if (!estado.graficos.length) {
      return h('div', { class: 'empty-hint' }, h('div', {},
        h('p', { text: 'Todavía no hay gráficos. Un gráfico se monta sobre la tabla de trabajo.' }),
        h('button', { class: 'btn-primary', type: 'button', text: 'Añadir un gráfico', onclick: menuPaneles })));
    }
    const mostrados = estado.fit && estado.graficos.some((g) => g.id === estado.fit)
      ? estado.graficos.filter((g) => g.id === estado.fit)
      : estado.graficos;
    return h('div', { class: 'graficos-grid' }, mostrados.map((g) => panelEscena(g, estado.graficos.indexOf(g))));
  }

  async function ampliarPanel() {
    if (!estado.graficos.length) { EN.toast('No hay gráficos.'); return; }
    const id = await EN.paleta.lista({
      titulo: 'Gráfico a ampliar al espacio disponible',
      items: [{ id: '', titulo: 'Ninguno (ver todos)' }].concat(estado.graficos.map((g, i) => ({ id: g.id, titulo: g.titulo || `Gráfico ${i + 1}`, desc: M.TIPOS_GRAFICO[g.tipo] }))),
    });
    if (id === null) return;
    estado.fit = id || null;
    guardar();
    EN.irA('constructor', 'graficos');
  }

  // ------------------------------------------------------------------- pasos

  function nodoPasos() {
    const columnas = columnasDescripcion();
    const lista = estado.pasos.length
      ? h('ol', { class: 'pasos-lista' }, estado.pasos.map((p, i) => h('li', { class: i === estado.pasos.length - 1 ? 'ultimo' : '', text: M.describirPaso(p, columnas) })))
      : h('p', { class: 'detalle', text: 'Todavía no hay pasos. Con los comandos (Ctrl+/) editas la tabla y cada cambio queda aquí.' });
    return h('div', { class: 'det' },
      h('p', { class: 'det-resumen', text: `Datos de partida: ${M.BASES[estado.base]}` }),
      lista,
      rt.tabla.avisos.map((a) => h('div', { class: 'estado-card warn', text: a })),
      h('div', { class: 'acciones' },
        h('button', { class: 'btn-secondary', type: 'button', text: 'Deshacer último', disabled: !estado.pasos.length, onclick: () => deshacer() }),
        h('button', { class: 'btn-secondary', type: 'button', text: 'Copiar', onclick: () => ejecutar('copiar_pasos') }),
        h('button', { class: 'btn-secondary', type: 'button', text: 'Pegar', onclick: () => ejecutar('pegar_pasos') })));
  }

  function abrirPasos() {
    rt.pasosVisibles = true;
    EN.detalle.abrir(`Pasos (${estado.pasos.length})`, nodoPasos());
  }

  function actualizarPasos() {
    if (rt.pasosVisibles && EN.E.r1 && rt.tabla) EN.detalle.abrir(`Pasos (${estado.pasos.length})`, nodoPasos());
  }

  function deshacer() {
    if (!estado.pasos.length) { EN.toast('No hay nada que deshacer.'); return; }
    const p = estado.pasos.pop();
    terminarModo();
    cambio();
    EN.toast(`Deshecho: ${M.describirPaso(p, columnasDescripcion())}`);
  }

  function describirTabla() {
    const lineas = [`Tabla de trabajo · ${M.BASES[estado.base]}`, `Simulación: ${(rt.datos && rt.datos.simulacion) || '—'}`];
    lineas.push(estado.pasos.length ? 'Pasos:' : 'Sin pasos: datos tal como llegan.');
    const columnas = columnasDescripcion();
    estado.pasos.forEach((p, i) => lineas.push(`${i + 1}. ${M.describirPaso(p, columnas)}`));
    return lineas.join('\n');
  }

  function exportarHtml() {
    const columnas = rt.tabla.columnas.filter((c) => !c.oculta);
    const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const filas = rt.tabla.filas.filter((f) => !f.oculta).map((f) => `<tr${f.color ? ` style="background:${esc(f.color)}"` : ''}${f.total ? ' class="total"' : ''}>${columnas.map((c) => `<td${c.tipo === 'numero' ? ' class="num"' : ''}>${esc(textoCelda(c, f.v[c.id]))}</td>`).join('')}</tr>`).join('');
    const html = `<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Tabla PGI Energía</title><style>
body{font-family:"Segoe UI",system-ui,sans-serif;font-size:13px;color:#222;margin:24px}pre{white-space:pre-wrap;color:#555}
table{border-collapse:collapse}th{background:#e8e8e8;text-align:left;padding:6px 12px;border-bottom:1px solid #ccc}
td{padding:5px 12px;border-bottom:1px solid #e0e0e0}td.num{text-align:right}tr.total td{font-weight:600;border-top:2px solid #ccc}</style></head>
<body><pre>${esc(describirTabla())}</pre><table><thead><tr>${columnas.map((c) => `<th>${esc(c.titulo)}</th>`).join('')}</tr></thead><tbody>${filas}</tbody></table></body></html>`;
    const enlace = h('a', { href: URL.createObjectURL(new Blob([html], { type: 'text/html;charset=utf-8' })), download: 'tabla_pgi_energia.html' });
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    URL.revokeObjectURL(enlace.href);
  }

  // ---------------------------------------------------------------- comandos

  const necesitaTabla = (id) => async () => iniciarModo(MODOS[id]());

  const COMANDOS = [
    { id: 'ocultar_columnas', desc: 'Modo: clic en una cabecera para ocultarla o mostrarla', tabla: true, run: necesitaTabla('ocultar_columnas') },
    { id: 'mostrar_todas_columnas', desc: 'Vuelve a mostrar todas las columnas ocultas', run: async () => anadirPaso({ p: 'mostrar_todas' }) },
    { id: 'seleccionar_columnas', desc: 'Modo: marca las columnas a CONSERVAR, luego Aplicar oculta el resto', tabla: true, run: necesitaTabla('seleccionar_columnas') },
    {
      id: 'desmarcar_todas_columnas', desc: 'Quita la marca sin ocultar nada todavía',
      run: async () => { rt.marcasCol.clear(); rt.marcasFila.clear(); if (rt.repintar) rt.repintar(); },
    },
    { id: 'seleccionar_filas', desc: 'Modo: marca las filas a CONSERVAR, luego Aplicar oculta el resto', tabla: true, run: necesitaTabla('seleccionar_filas') },
    { id: 'colorear_filas', desc: 'Modo: marca filas y elige un color; se pintan, todas siguen visibles', tabla: true, run: necesitaTabla('colorear_filas') },
    { id: 'mover_columnas_a_despues', desc: 'Modo: clic en la columna a mover y clic en la columna tras la que quedará', tabla: true, run: necesitaTabla('mover_columnas_a_despues') },
    { id: 'cabeceras_cambiar_nombre', desc: 'Modo: clic en una cabecera para renombrarla, hasta pulsar Terminar', tabla: true, run: necesitaTabla('cabeceras_cambiar_nombre') },
    { id: 'modo_totales', desc: 'Modo: clic en las cabeceras a sumar, luego Aplicar totales', tabla: true, run: necesitaTabla('modo_totales') },
    { id: 'columnas_matematicas', desc: 'Columna nueva con fórmula multi-columna: pinchas columnas y usas sus alias (ej: (C1+C2)*C3)', tabla: true, run: necesitaTabla('columnas_matematicas') },
    { id: 'sustituir_en_columna', desc: 'Modo: marca columnas de texto y una lista de «texto a sustituir → texto nuevo»', tabla: true, run: necesitaTabla('sustituir_en_columna') },
    { id: 'ordenar_filas', desc: 'Modo: clic en una cabecera para ordenar las filas (otro clic invierte el orden)', tabla: true, run: necesitaTabla('ordenar_filas') },
    {
      id: 'alternar_fila_filtros', desc: 'Oculta o muestra la fila de filtros de la tabla', tabla: true,
      run: async () => { estado.filtroVisible = !estado.filtroVisible; guardar(); rt.repintar(); },
    },
    { id: 'deshacer_tabla', desc: 'Deshace el último cambio sobre la tabla', run: async () => deshacer() },
    { id: 'paneles_de_escena', desc: 'Añade, edita o quita paneles de escena (gráficos de barras, líneas, área…) sobre la tabla', run: menuPaneles },
    { id: 'añadir_grafico_barras', desc: 'Modo: clic en las cabeceras de origen, luego Añadir gráfico', tabla: true, run: necesitaTabla('anadir_grafico_barras') },
    { id: 'fit_panels_escena', desc: 'Amplía un gráfico al espacio disponible (o vuelve a ver todos)', run: ampliarPanel },
    { id: 'ver_pasos', desc: 'Muestra en el panel derecho el registro de pasos de la tabla', run: async () => abrirPasos() },
    {
      id: 'copiar_pasos', desc: 'Copia el registro de pasos al portapapeles',
      run: async () => copiarTexto(JSON.stringify({ base: estado.base, pasos: estado.pasos }), 'Pasos copiados.'),
    },
    {
      id: 'pegar_pasos', desc: 'Pega y reproduce pasos (se añaden a los ya hechos)',
      run: async () => {
        let texto = '';
        try { texto = await navigator.clipboard.readText(); } catch (e) { texto = ''; }
        if (!texto.trim()) texto = (await EN.paleta.texto({ titulo: 'Pega aquí los pasos copiados', valor: '' })) || '';
        if (!texto.trim()) return;
        try {
          const dato = JSON.parse(texto);
          const lista = Array.isArray(dato) ? dato : dato.pasos;
          if (!Array.isArray(lista) || lista.some((p) => !p || !M.PASOS[p.p])) throw new Error('No son pasos de esta tabla.');
          if (dato.base && dato.base !== estado.base) EN.toast('Ojo: los pasos se grabaron con otros datos de partida.');
          lista.forEach((p) => estado.pasos.push(p));
          cambio();
          EN.toast(`${lista.length} paso(s) añadidos.`);
        } catch (e) {
          EN.toast(`No se pudieron pegar los pasos: ${e.message}`, 4000);
        }
      },
    },
    { id: 'describir_tabla', desc: 'Copia al portapapeles un texto sintético de origen y pasos (para un informe)', run: async () => copiarTexto(describirTabla(), 'Descripción copiada.') },
    { id: 'exportar_html', desc: 'Exporta la tabla actual a un .html independiente', run: async () => exportarHtml() },
    {
      id: 'datos_de_origen', desc: 'Elige cómo se ordenan los datos mensuales de partida (vacía los pasos y los gráficos)',
      run: async () => {
        const base = await EN.paleta.lista({ titulo: 'Datos de partida', items: Object.entries(M.BASES).map(([id, t]) => ({ id, titulo: t, desc: id === estado.base ? 'actual' : '' })) });
        if (!base || base === estado.base) return;
        estado.base = base;
        estado.pasos = [];
        estado.fit = null;
        estado.graficos = [{ id: 'g1', tipo: 'barras', orient: 'columnas', x: '', ys: [], titulo: '' }];
        estado.contador = 1;
        terminarModo();
        recalcular();
        const numericas = rt.tabla.columnas.filter((c) => c.tipo === 'numero').map((c) => c.id);
        estado.graficos[0].ys = base === 'largo' ? ['simulado_kwh', 'real_kwh'] : numericas.filter((id) => id !== 'total').slice(0, 3);
        if (base !== 'largo') Object.assign(estado.graficos[0], { tipo: 'lineas', orient: 'filas', ys: numericas.filter((id) => id !== 'total').slice(0, 12) });
        cambio();
      },
    },
    {
      id: 'guardar_escenario', desc: 'Guarda la tabla (datos de partida, pasos y gráficos) con un nombre',
      run: async () => {
        const nombre = await EN.paleta.texto({ titulo: 'Nombre del escenario', valor: '' });
        if (!nombre) return;
        const foto = JSON.parse(JSON.stringify({ base: estado.base, pasos: estado.pasos, graficos: estado.graficos }));
        estado.guardados = estado.guardados.filter((g) => g.nombre !== nombre).concat([Object.assign({ nombre }, foto)]);
        guardar();
        EN.toast(`Escenario «${nombre}» guardado.`);
      },
    },
    {
      id: 'cargar_escenario', desc: 'Abre un escenario guardado',
      run: async () => {
        if (!estado.guardados.length) { EN.toast('Todavía no has guardado ningún escenario.'); return; }
        const nombre = await EN.paleta.lista({ titulo: 'Escenarios guardados', items: estado.guardados.map((g) => ({ id: g.nombre, titulo: g.nombre, desc: `${g.pasos.length} paso(s) · ${g.graficos.length} gráfico(s)` })) });
        const g = estado.guardados.find((x) => x.nombre === nombre);
        if (!g) return;
        estado.base = M.BASES[g.base] ? g.base : 'largo';
        estado.pasos = JSON.parse(JSON.stringify(g.pasos));
        estado.graficos = JSON.parse(JSON.stringify(g.graficos));
        estado.fit = null;
        terminarModo();
        cambio();
      },
    },
    {
      id: 'borrar_escenario', desc: 'Borra un escenario guardado',
      run: async () => {
        if (!estado.guardados.length) { EN.toast('No hay escenarios guardados.'); return; }
        const nombre = await EN.paleta.lista({ titulo: 'Borrar escenario', items: estado.guardados.map((g) => ({ id: g.nombre, titulo: g.nombre })) });
        if (!nombre) return;
        estado.guardados = estado.guardados.filter((g) => g.nombre !== nombre);
        guardar();
        EN.toast(`Escenario «${nombre}» borrado.`);
      },
    },
    {
      id: 'reiniciar_constructor', desc: 'Vacía los pasos y los gráficos y vuelve a los datos de partida',
      run: async () => {
        Object.assign(estado, inicial(), { guardados: estado.guardados, filtroVisible: estado.filtroVisible });
        terminarModo();
        cambio();
        EN.toast('Constructor reiniciado.');
      },
    },
  ];

  async function ejecutar(id) {
    const c = COMANDOS.find((x) => x.id === id);
    if (!c) return;
    if (c.tabla && !rt.enTabla) { rt.pendiente = id; EN.irA('constructor', 'tabla'); return; }
    await c.run();
  }

  /** Comandos del Constructor para la paleta general (Ctrl+/). */
  const comandosConstructor = () => COMANDOS.map((c) => ({ id: `c:${c.id}`, titulo: `/${c.id}`, desc: c.desc, grupo: 'Constructor', run: () => ejecutar(c.id) }));

  // ------------------------------------------------------------------ vistas

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && rt.modo && rt.enTabla && !document.querySelector('.paleta-lienzo')) terminarModo();
  });

  function preparar(datos, enTabla) {
    // Cambió el edificio, el año o los datos: el modo y las marcas ya no valen.
    rt.datos = datos;
    rt.enTabla = enTabla;
    rt.modo = null;
    rt.formula = null;
    rt.marcasCol.clear();
    rt.marcasFila.clear();
    recalcular();
    EN.comandosVista = comandosConstructor;
  }

  function vistaTabla(datos) {
    preparar(datos, true);
    const arriba = h('div', { class: 'cb-arriba' });
    const cuerpo = h('div', { class: 'cb-tabla' });
    rt.repintar = () => { EN.llenar(arriba, nodoChips(), nodoBarraModo()); EN.llenar(cuerpo, nodoTabla()); };
    rt.repintar();
    actualizarPasos();
    if (rt.pendiente) {
      const id = rt.pendiente;
      rt.pendiente = null;
      setTimeout(() => ejecutar(id), 0);
    }
    return EN.vista(arriba, cuerpo);
  }

  function vistaGraficos(datos) {
    preparar(datos, false);
    const arriba = h('div', { class: 'cb-arriba' });
    const cuerpo = h('div', { class: 'cb-tabla' });
    rt.repintar = () => { EN.llenar(arriba, nodoChips()); EN.llenar(cuerpo, nodoGraficos()); };
    rt.repintar();
    actualizarPasos();
    return EN.vista(arriba, cuerpo);
  }

  EN.ESC_CONSTRUCTOR = {
    id: 'constructor', icono: 'sliders-horizontal', titulo: 'Constructor',
    subs: [
      { id: 'tabla', titulo: 'Tabla de datos', render: EN.conDatos('datos', null, vistaTabla) },
      { id: 'graficos', titulo: 'Gráficos', render: EN.conDatos('datos', null, vistaGraficos) },
    ],
  };
})();
