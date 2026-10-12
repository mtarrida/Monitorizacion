/* Motor del Constructor: tabla de trabajo con pasos reproducibles, como en EnergyPlus HTML++.
   Sin DOM ni red, así se puede probar con Node.

   Una tabla nace de una BASE (los datos mensuales ordenados de una forma) y de una lista de PASOS
   (ocultar columnas, seleccionar o colorear filas, mover o renombrar columnas, totales, columnas
   matemáticas, sustituir texto, ordenar). La tabla que se ve es siempre aplicarPasos(base, pasos):
   deshacer es quitar el último paso, copiar pasos es copiar la lista. */
(function (raiz) {
  'use strict';

  const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  const COLORES = [
    '#AB1735', '#4B5563', '#A7B0BE', '#E57373', '#6B7280', '#8C1E35', '#90A4AE', '#BF6B7F', '#37474F', '#CFD8DC',
    '#D98BA0', '#556270', '#7B1F34', '#9AA5B1', '#B03A48', '#2F3A46',
  ];

  const BASES = {
    largo: 'Mes × categoría (una fila por mes y categoría)',
    ancho_real: 'Categorías × meses · Real BMS (kWh)',
    ancho_simulado: 'Categorías × meses · Simulado (kWh)',
    ancho_desv_kwh: 'Categorías × meses · Desviación (kWh)',
    ancho_desv_pct: 'Categorías × meses · Desviación (%)',
  };

  const esNum = (v) => typeof v === 'number' && Number.isFinite(v);
  const aNumeroONull = (v) => (esNum(v) ? v : null);

  function desviacion(simulado, real) {
    if (!esNum(real)) return { kwh: null, pct: null };
    const kwh = real - (simulado || 0);
    return { kwh, pct: !simulado ? null : (kwh / simulado) * 100 };
  }

  // ------------------------------------------------------------------- bases

  /** datos = respuesta de /api/datos. Devuelve {id, titulo, columnas, filas:[{id, v}]}. */
  function crearBase(datos, id) {
    const filas = (datos && datos.filas) || [];
    if (!BASES[id]) id = 'largo';

    if (id === 'largo') {
      const columnas = [
        { id: 'categoria', titulo: 'Categoría', tipo: 'texto' },
        { id: 'mes', titulo: 'Mes', tipo: 'texto' },
        { id: 'simulado_kwh', titulo: 'Simulado (kWh)', tipo: 'numero', dec: 0 },
        { id: 'real_kwh', titulo: 'Real BMS (kWh)', tipo: 'numero', dec: 0 },
        { id: 'desviacion_kwh', titulo: 'Desviación (kWh)', tipo: 'numero', dec: 0 },
        { id: 'desviacion_pct', titulo: 'Desviación (%)', tipo: 'numero', dec: 1 },
        { id: 'electricidad_kwh', titulo: 'Electricidad (kWh)', tipo: 'numero', dec: 0 },
        { id: 'gas_kwh', titulo: 'Gas (kWh)', tipo: 'numero', dec: 0 },
      ];
      const datosFilas = filas
        .filter((f) => esNum(f.real_kwh))
        .sort((a, b) => (a.categoria < b.categoria ? -1 : a.categoria > b.categoria ? 1 : a.mes - b.mes))
        .map((f, i) => {
          const d = desviacion(f.simulado_kwh, f.real_kwh);
          return {
            id: `f${i}`,
            v: {
              categoria: f.categoria, mes: MESES[f.mes - 1], simulado_kwh: aNumeroONull(f.simulado_kwh), real_kwh: aNumeroONull(f.real_kwh),
              desviacion_kwh: d.kwh, desviacion_pct: d.pct, electricidad_kwh: aNumeroONull(f.electricidad_kwh), gas_kwh: aNumeroONull(f.gas_kwh),
            },
          };
        });
      return { id, titulo: BASES[id], columnas, filas: datosFilas };
    }

    const medidas = {
      ancho_real: { dec: 0, f: (f) => aNumeroONull(f.real_kwh) },
      ancho_simulado: { dec: 0, f: (f) => aNumeroONull(f.simulado_kwh) },
      ancho_desv_kwh: { dec: 0, f: (f) => desviacion(f.simulado_kwh, f.real_kwh).kwh },
      ancho_desv_pct: { dec: 1, f: (f) => desviacion(f.simulado_kwh, f.real_kwh).pct },
    };
    const medida = medidas[id];
    const columnas = [{ id: 'categoria', titulo: 'Categoría', tipo: 'texto' }]
      .concat(MESES.map((m, i) => ({ id: `mes_${i + 1}`, titulo: m, tipo: 'numero', dec: medida.dec })))
      .concat([{ id: 'total', titulo: 'Total', tipo: 'numero', dec: medida.dec }]);

    const categorias = (datos && datos.categorias) || [];
    const datosFilas = [];
    categorias.forEach((categoria) => {
      const v = { categoria };
      let hayDato = false;
      let sumaSim = 0;
      let sumaReal = 0;
      let suma = 0;
      for (let m = 1; m <= 12; m++) {
        const f = filas.find((x) => x.categoria === categoria && x.mes === m);
        const valor = f ? medida.f(f) : null;
        v[`mes_${m}`] = valor;
        if (valor !== null) { hayDato = true; suma += valor; }
        if (f && esNum(f.real_kwh)) { sumaSim += f.simulado_kwh || 0; sumaReal += f.real_kwh; }
      }
      if (!hayDato) return;
      v.total = id === 'ancho_desv_pct' ? (sumaSim === 0 ? null : ((sumaReal - sumaSim) / sumaSim) * 100) : suma;
      datosFilas.push({ id: `f${datosFilas.length}`, v });
    });
    return { id, titulo: BASES[id], columnas, filas: datosFilas };
  }

  // ---------------------------------------------------------------- fórmulas

  const FUNCIONES = {
    IF: (c, a, b) => (verdadero(c) ? a : b === undefined ? null : b),
    AND: (...a) => a.every(verdadero),
    OR: (...a) => a.some(verdadero),
    NOT: (a) => !verdadero(a),
    ABS: (a) => (esNum(a) ? Math.abs(a) : null),
    ROUND: (a, n) => { if (!esNum(a)) return null; const f = 10 ** (esNum(n) ? n : 0); return Math.round(a * f) / f; },
    MIN: (...a) => { const n = a.filter(esNum); return n.length ? Math.min(...n) : null; },
    MAX: (...a) => { const n = a.filter(esNum); return n.length ? Math.max(...n) : null; },
    SUM: (...a) => a.filter(esNum).reduce((s, x) => s + x, 0),
    AVG: (...a) => { const n = a.filter(esNum); return n.length ? n.reduce((s, x) => s + x, 0) / n.length : null; },
  };

  function verdadero(v) { return v === true || (esNum(v) && v !== 0) || (typeof v === 'string' && v !== ''); }

  function tokenizar(texto) {
    const fichas = [];
    let i = 0;
    while (i < texto.length) {
      const c = texto[i];
      if (/\s/.test(c)) { i++; continue; }
      let m;
      if ((m = /^\d+(?:[.,]\d+)?/.exec(texto.slice(i)))) { fichas.push({ t: 'num', v: parseFloat(m[0].replace(',', '.')) }); i += m[0].length; continue; }
      if (c === '"') {
        const fin = texto.indexOf('"', i + 1);
        if (fin < 0) throw new Error('Falta cerrar unas comillas.');
        fichas.push({ t: 'str', v: texto.slice(i + 1, fin) });
        i = fin + 1;
        continue;
      }
      if ((m = /^[A-Za-z_][A-Za-z0-9_]*/.exec(texto.slice(i)))) { fichas.push({ t: 'id', v: m[0] }); i += m[0].length; continue; }
      if ((m = /^(<=|>=|<>|!=|[-+*/(),<>=])/.exec(texto.slice(i)))) { fichas.push({ t: 'op', v: m[0] === '!=' ? '<>' : m[0] }); i += m[0].length; continue; }
      throw new Error(`Carácter no válido: «${c}».`);
    }
    return fichas;
  }

  /** Analiza una fórmula tipo (C1+C2)*C3 o IF(C1>10, "Alto", "Bajo") y devuelve su árbol. */
  function parsear(texto) {
    const fichas = tokenizar(String(texto || ''));
    if (!fichas.length) throw new Error('La fórmula está vacía.');
    let pos = 0;
    const ver = () => fichas[pos];
    const comer = (op) => { if (ver() && ver().t === 'op' && ver().v === op) { pos++; return true; } return false; };

    function comparacion() {
      let a = suma();
      while (ver() && ver().t === 'op' && ['<', '<=', '>', '>=', '=', '<>'].includes(ver().v)) {
        const op = fichas[pos++].v;
        a = { t: 'bin', op, a, b: suma() };
      }
      return a;
    }
    function suma() {
      let a = producto();
      while (ver() && ver().t === 'op' && (ver().v === '+' || ver().v === '-')) { const op = fichas[pos++].v; a = { t: 'bin', op, a, b: producto() }; }
      return a;
    }
    function producto() {
      let a = unario();
      while (ver() && ver().t === 'op' && (ver().v === '*' || ver().v === '/')) { const op = fichas[pos++].v; a = { t: 'bin', op, a, b: unario() }; }
      return a;
    }
    function unario() {
      if (ver() && ver().t === 'op' && (ver().v === '-' || ver().v === '+')) { const op = fichas[pos++].v; return { t: 'un', op, a: unario() }; }
      return primario();
    }
    function primario() {
      const f = fichas[pos++];
      if (!f) throw new Error('La fórmula termina antes de tiempo.');
      if (f.t === 'num') return { t: 'num', v: f.v };
      if (f.t === 'str') return { t: 'str', v: f.v };
      if (f.t === 'id') {
        if (ver() && ver().t === 'op' && ver().v === '(') {
          pos++;
          const nombre = f.v.toUpperCase();
          if (!FUNCIONES[nombre]) throw new Error(`Función desconocida: ${f.v}.`);
          const args = [];
          if (!comer(')')) {
            do { args.push(comparacion()); } while (comer(','));
            if (!comer(')')) throw new Error('Falta cerrar un paréntesis.');
          }
          return { t: 'call', f: nombre, args };
        }
        return { t: 'id', n: f.v.toUpperCase() };
      }
      if (f.t === 'op' && f.v === '(') {
        const e = comparacion();
        if (!comer(')')) throw new Error('Falta cerrar un paréntesis.');
        return e;
      }
      throw new Error(`No esperaba «${f.v}».`);
    }

    const arbol = comparacion();
    if (pos < fichas.length) throw new Error(`No esperaba «${fichas[pos].v}».`);
    return arbol;
  }

  function identificadores(arbol, salida = new Set()) {
    if (!arbol) return salida;
    if (arbol.t === 'id') salida.add(arbol.n);
    ['a', 'b'].forEach((k) => identificadores(arbol[k], salida));
    (arbol.args || []).forEach((x) => identificadores(x, salida));
    return salida;
  }

  /** Evalúa el árbol con los valores de los alias (C1, C2…). Sin eval: solo recorre el árbol. */
  function evaluar(arbol, valores) {
    switch (arbol.t) {
      case 'num': case 'str': return arbol.v;
      case 'id': return Object.prototype.hasOwnProperty.call(valores, arbol.n) ? valores[arbol.n] : null;
      case 'un': { const a = evaluar(arbol.a, valores); return esNum(a) ? (arbol.op === '-' ? -a : a) : null; }
      case 'call': return FUNCIONES[arbol.f](...arbol.args.map((x) => evaluar(x, valores)));
      case 'bin': {
        const a = evaluar(arbol.a, valores);
        const b = evaluar(arbol.b, valores);
        switch (arbol.op) {
          case '+': if (typeof a === 'string' || typeof b === 'string') return `${a ?? ''}${b ?? ''}`; return esNum(a) && esNum(b) ? a + b : null;
          case '-': return esNum(a) && esNum(b) ? a - b : null;
          case '*': return esNum(a) && esNum(b) ? a * b : null;
          case '/': return esNum(a) && esNum(b) && b !== 0 ? a / b : null;
          case '=': return a === b;
          case '<>': return a !== b;
          default: {
            if (a === null || b === null || a === undefined || b === undefined) return false;
            if (arbol.op === '<') return a < b;
            if (arbol.op === '<=') return a <= b;
            if (arbol.op === '>') return a > b;
            return a >= b;
          }
        }
      }
      default: return null;
    }
  }

  function evaluarFormula(texto, valores) { return evaluar(parsear(texto), valores); }

  // ------------------------------------------------------------------- pasos

  function columna(t, id) {
    const c = t.columnas.find((x) => x.id === id);
    if (!c) throw new Error(`No existe la columna «${id}».`);
    return c;
  }

  const PASOS = {
    alternar_columna(t, p) { const c = columna(t, p.id); c.oculta = !c.oculta; },
    mostrar_todas(t) { t.columnas.forEach((c) => { c.oculta = false; }); },
    seleccionar_columnas(t, p) {
      if (!p.conservar || !p.conservar.length) throw new Error('No hay columnas que conservar.');
      p.conservar.forEach((id) => columna(t, id));
      t.columnas.forEach((c) => { c.oculta = !p.conservar.includes(c.id); });
    },
    seleccionar_filas(t, p) {
      if (!p.conservar || !p.conservar.length) throw new Error('No hay filas que conservar.');
      t.filas.forEach((f) => { if (!f.total) f.oculta = !p.conservar.includes(f.id); });
    },
    colorear_filas(t, p) { t.filas.forEach((f) => { if ((p.filas || []).includes(f.id)) f.color = p.color; }); },
    mover_columna(t, p) {
      const i = t.columnas.findIndex((c) => c.id === p.id);
      if (i < 0) throw new Error(`No existe la columna «${p.id}».`);
      const [c] = t.columnas.splice(i, 1);
      const j = t.columnas.findIndex((x) => x.id === p.despues);
      if (j < 0) { t.columnas.splice(i, 0, c); throw new Error(`No existe la columna «${p.despues}».`); }
      t.columnas.splice(j + 1, 0, c);
    },
    renombrar(t, p) { columna(t, p.id).titulo = p.titulo; },
    totales(t, p) {
      const ids = (p.ids || []).map((id) => columna(t, id).id);
      t.filas = t.filas.filter((f) => !f.total);
      const v = {};
      const primeraTexto = t.columnas.find((c) => c.tipo === 'texto');
      if (primeraTexto) v[primeraTexto.id] = 'Total';
      ids.forEach((id) => {
        v[id] = t.filas.filter((f) => !f.oculta).reduce((s, f) => s + (esNum(f.v[id]) ? f.v[id] : 0), 0);
      });
      t.filas.push({ id: 'total', v, oculta: false, color: null, total: true });
    },
    formula(t, p) {
      const arbol = parsear(p.formula);
      const alias = p.alias || {};
      identificadores(arbol).forEach((n) => { if (!alias[n]) throw new Error(`Alias desconocido: ${n}.`); });
      Object.values(alias).forEach((id) => columna(t, id));
      if (t.columnas.some((c) => c.id === p.id)) throw new Error(`La columna «${p.id}» ya existe.`);
      t.columnas.push({ id: p.id, titulo: p.titulo || p.id, tipo: 'numero', dec: 2, oculta: false, formula: p.formula, calculada: true });
      t.filas.forEach((f) => {
        if (f.total) { f.v[p.id] = null; return; }
        const valores = {};
        Object.entries(alias).forEach(([n, id]) => { valores[n.toUpperCase()] = f.v[id] === undefined ? null : f.v[id]; });
        f.v[p.id] = evaluar(arbol, valores);
      });
    },
    sustituir(t, p) {
      (p.ids || []).forEach((id) => columna(t, id));
      t.filas.forEach((f) => {
        (p.ids || []).forEach((id) => {
          if (typeof f.v[id] !== 'string') return;
          (p.pares || []).forEach(([de, a]) => { if (de) f.v[id] = f.v[id].split(de).join(a || ''); });
        });
      });
    },
    ordenar(t, p) {
      columna(t, p.id);
      const total = t.filas.filter((f) => f.total);
      const resto = t.filas.filter((f) => !f.total);
      const dir = p.dir === 'desc' ? -1 : 1;
      resto.sort((a, b) => {
        const x = a.v[p.id];
        const y = b.v[p.id];
        const nx = x === null || x === undefined;
        const ny = y === null || y === undefined;
        if (nx || ny) return nx === ny ? 0 : nx ? 1 : -1; // los vacíos siempre al final
        if (esNum(x) && esNum(y)) return (x - y) * dir;
        return String(x).localeCompare(String(y), 'es') * dir;
      });
      t.filas = resto.concat(total);
    },
  };

  /** Tabla visible = base + pasos. Un paso que falla no rompe el resto: queda anotado en `avisos`. */
  function aplicarPasos(base, pasos) {
    const t = {
      columnas: base.columnas.map((c) => Object.assign({}, c, { oculta: false })),
      filas: base.filas.map((f) => ({ id: f.id, v: Object.assign({}, f.v), oculta: false, color: null, total: false })),
      avisos: [],
    };
    (pasos || []).forEach((p, i) => {
      try {
        if (!PASOS[p.p]) throw new Error('paso desconocido');
        PASOS[p.p](t, p);
      } catch (e) {
        t.avisos.push(`Paso ${i + 1} (${p.p}): ${e.message}`);
      }
    });
    return t;
  }

  /** Siguiente id libre para una columna matemática (m1, m2…). */
  function idColumnaNueva(pasos) {
    const n = (pasos || []).filter((p) => p.p === 'formula').map((p) => parseInt(String(p.id).replace(/\D/g, ''), 10) || 0);
    return `m${(n.length ? Math.max(...n) : 0) + 1}`;
  }

  function describirPaso(p, columnas) {
    const titulo = (id) => { const c = (columnas || []).find((x) => x.id === id); return c ? `«${c.titulo}»` : `«${id}»`; };
    const lista = (ids) => (ids || []).map(titulo).join(', ');
    switch (p.p) {
      case 'alternar_columna': return `Ocultar o mostrar la columna ${titulo(p.id)}`;
      case 'mostrar_todas': return 'Mostrar todas las columnas';
      case 'seleccionar_columnas': return `Conservar solo las columnas ${lista(p.conservar)}`;
      case 'seleccionar_filas': return `Conservar solo ${p.conservar.length} fila(s)`;
      case 'colorear_filas': return `Colorear ${p.filas.length} fila(s) de ${p.color}`;
      case 'mover_columna': return `Mover la columna ${titulo(p.id)} detrás de ${titulo(p.despues)}`;
      case 'renombrar': return `Renombrar la columna ${titulo(p.id)} a «${p.titulo}»`;
      case 'totales': return `Fila de totales de ${lista(p.ids)}`;
      case 'formula': return `Columna «${p.titulo}» = ${p.formula}  (${Object.entries(p.alias || {}).map(([n, id]) => `${n}=${titulo(id)}`).join(', ')})`;
      case 'sustituir': return `Sustituir texto en ${lista(p.ids)}: ${(p.pares || []).map(([de, a]) => `«${de}» → «${a || ''}»`).join(', ')}`;
      case 'ordenar': return `Ordenar por ${titulo(p.id)} ${p.dir === 'desc' ? 'de mayor a menor' : 'de menor a mayor'}`;
      default: return p.p;
    }
  }

  // ---------------------------------------------------------------- gráficos

  const TIPOS_GRAFICO = { barras: 'Barras agrupadas', apiladas: 'Barras apiladas', lineas: 'Líneas', area: 'Área' };

  /** Figura Plotly de un panel de escena sobre la tabla actual. null si no hay nada que dibujar.
      cfg: {tipo, orient: 'columnas' | 'filas', x: id de columna (opcional), ys: [ids], titulo} */
  function construirGrafico(tabla, cfg) {
    const filas = tabla.filas.filter((f) => !f.oculta && !f.total);
    const ys = (cfg.ys || []).map((id) => tabla.columnas.find((c) => c.id === id)).filter(Boolean);
    if (!filas.length || !ys.length) return null;

    const etiqueta = (f) => {
      const x = cfg.x && tabla.columnas.find((c) => c.id === cfg.x);
      if (x) return String(f.v[x.id] === null || f.v[x.id] === undefined ? '' : f.v[x.id]);
      const textos = tabla.columnas.filter((c) => c.tipo === 'texto' && !c.oculta);
      return textos.map((c) => f.v[c.id]).filter((v) => v !== null && v !== undefined && v !== '').join(' · ') || f.id;
    };
    const valor = (f, c) => (esNum(f.v[c.id]) ? f.v[c.id] : null);

    let trazas;
    let xs;
    if (cfg.orient === 'filas') {
      xs = ys.map((c) => c.titulo);
      trazas = filas.map((f) => ({ nombre: etiqueta(f), y: ys.map((c) => valor(f, c)) }));
    } else {
      xs = filas.map(etiqueta);
      trazas = ys.map((c) => ({ nombre: c.titulo, y: filas.map((f) => valor(f, c)) }));
    }

    const data = trazas.map((t, i) => {
      const color = COLORES[i % COLORES.length];
      const base = { name: t.nombre, x: xs, y: t.y };
      if (cfg.tipo === 'barras' || cfg.tipo === 'apiladas') return Object.assign(base, { type: 'bar', marker: { color } });
      const linea = { type: 'scatter', mode: 'lines+markers', line: { color, width: 3 }, connectgaps: false };
      if (cfg.tipo === 'area') Object.assign(linea, { fill: 'tozeroy', fillcolor: `${color}33` });
      return Object.assign(base, linea);
    });

    // Con una serie por fila no hay un título natural: el panel ya dice de qué gráfico se trata.
    const auto = cfg.orient === 'filas' ? '' : ys.map((c) => c.titulo).join(', ');
    const layout = {
      title: { text: cfg.titulo || auto },
      barmode: cfg.tipo === 'apiladas' ? 'stack' : 'group',
      xaxis: { title: { text: '' }, tickangle: xs.length > 8 ? -30 : 0 },
      legend: { orientation: 'h', y: -0.2 },
      margin: { l: 70, r: 20, t: 55, b: xs.length > 8 ? 120 : 70 },
    };
    return { data, layout };
  }

  const API = { MESES, COLORES, BASES, TIPOS_GRAFICO, crearBase, aplicarPasos, idColumnaNueva, describirPaso, parsear, evaluarFormula, identificadores, construirGrafico, PASOS };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else { raiz.EN = raiz.EN || {}; raiz.EN.motor = API; }
})(typeof window !== 'undefined' ? window : globalThis);
