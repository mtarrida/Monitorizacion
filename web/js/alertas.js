/* Escenario Alertas: mapa de calor de desviaciones (categorías × meses) y resumen por gravedad.
   Al pulsar una celda, una categoría o un mes, el porqué aparece en el panel derecho (EN.detalle).
   Las "posibles causas" son hipótesis por categoría a partir del sentido y la persistencia de la
   desviación: orientan qué mirar, no diagnostican. */
(function () {
  'use strict';
  const EN = window.EN;
  const h = EN.h;

  const MESES_CORTOS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  const NIVEL_TEXTO = { ok: 'Correcto', atencion: 'Atención', revisar: 'Revisar', sin_dato: 'Sin dato' };
  const TONO = { ok: 'ok', atencion: 'warn', revisar: 'mal' };

  EN.COLUMNAS.nivel = {
    t: 'Gravedad',
    clase: '',
    nodo: (n) => [h('span', { class: `punto ${TONO[n] || ''}`, 'aria-hidden': 'true' }), NIVEL_TEXTO[n] || ''],
  };
  EN.COLUMNAS.periodo = { t: 'Periodo' };

  // ---------------------------------------------------------------- formatos

  const signo = (v) => (v > 0 ? '+' : v < 0 ? '−' : '');
  const textoCelda = (c) => (c.desviacion_pct === null ? 's/ sim.' : `${signo(c.desviacion_pct)}${EN.num(Math.abs(c.desviacion_pct), 0)} %`);
  const textoLargo = (c) => (c.desviacion_pct === null ? 'sin valor simulado' : `${signo(c.desviacion_pct)}${EN.num(Math.abs(c.desviacion_pct), 1)} %`);
  const punto = (nivel) => h('span', { class: `punto ${TONO[nivel] || ''}`, 'aria-hidden': 'true' });

  /** Clase de color de una celda: dos tonos por nivel para que se note la magnitud. */
  function claseCelda(c) {
    const p = c.desviacion_pct === null ? null : Math.abs(c.desviacion_pct);
    if (c.nivel === 'ok') return p <= 5 ? 'hm-ok1' : 'hm-ok2';
    if (c.nivel === 'atencion') return p <= 15 ? 'hm-at1' : 'hm-at2';
    if (c.nivel === 'revisar') return p === null || p > 35 ? 'hm-re2' : 'hm-re1';
    return 'hm-vacio';
  }

  // ------------------------------------------------------------ explicaciones

  const GENERICAS = {
    mas: [
      'Horarios o modos de funcionamiento distintos de los simulados.',
      'Ocupación o cargas superiores a las supuestas.',
      'Equipo con rendimiento inferior al de proyecto.',
      'Datos del BMS asignados a esta categoría de forma distinta a la del modelo.',
    ],
    menos: [
      'Uso u ocupación menores que los supuestos.',
      'Equipo más eficiente que el de proyecto.',
      'Consumo medido en otra categoría o sin medir.',
      'Equipo parado o en avería.',
    ],
  };

  const CAUSAS = {
    Heating: {
      mas: ['Consignas de calefacción más altas que las de proyecto o sin banda muerta.', 'Horario más largo que el simulado (arranques anticipados, fines de semana).', 'Mes más frío que el año climático de la simulación.', 'Infiltraciones o huecos abiertos con la calefacción en marcha.'],
      menos: ['Consigna real más baja o zonas sin ocupar.', 'Mes más cálido que el año tipo.', 'Ocupación menor que la simulada.', 'Parte de la demanda cubierta por otro sistema que el BMS no suma a esta categoría.'],
    },
    Cooling: {
      mas: ['Consignas de refrigeración más bajas que las de proyecto.', 'Ganancias internas u ocupación superiores a las simuladas.', 'Mes más caluroso que el año tipo.', 'Free-cooling o recuperación que no está actuando.'],
      menos: ['Consigna más alta u horarios más cortos.', 'Mes más fresco que el año tipo.', 'Equipos parados o averiados que no refrigeran.'],
    },
    'Interior Lighting': {
      mas: ['Horarios de encendido más largos o sin apagado automático.', 'Sin regulación por luz natural o por presencia.', 'Potencia instalada real mayor que la de proyecto.'],
      menos: ['Regulación por presencia o luz natural más eficaz que la supuesta.', 'Menor ocupación u horario más corto.', 'Parte de la iluminación sin submedida en el BMS.'],
    },
    'Exterior Lighting': {
      mas: ['Programación horaria o célula crepuscular mal ajustadas.', 'Más puntos de luz o más potencia que lo simulado.'],
      menos: ['Apagados parciales o programación más restrictiva.'],
    },
    Fans: {
      mas: ['Caudales o presiones de consigna más altos.', 'Funcionamiento fuera del horario simulado.', 'Sin variación de velocidad, o filtros sucios que elevan la pérdida de carga.'],
      menos: ['Variación de velocidad más eficaz que la supuesta.', 'Horario real más corto.', 'Ventilación reducida por menor ocupación.'],
    },
    Pumps: {
      mas: ['Bombas funcionando de forma continua o a caudal fijo.', 'Sin variación de velocidad o presión diferencial mal ajustada.'],
      menos: ['Paradas por demanda baja o mejor control que el simulado.'],
    },
    'Interior Equipment': {
      mas: ['Más equipos u horas de uso que lo previsto (cargas enchufadas).', 'Equipos en espera encendidos fuera de horario.'],
      menos: ['Menos equipos o menor uso que el supuesto.', 'Parte de las cargas fuera del contador de esta categoría.'],
    },
    'Water Systems': {
      mas: ['Mayor demanda de ACS que la simulada.', 'Pérdidas en acumulación o recirculación.', 'Consigna de ACS más alta.'],
      menos: ['Menor ocupación o consumo de agua caliente.'],
    },
  };

  const COMPROBAR = [
    'Tendencias horarias de la categoría en el BMS durante el mes.',
    'Horarios y consignas programados frente a los del modelo.',
    'Ocupación real frente a la supuesta en la simulación.',
    'Clima del mes frente al archivo meteorológico del modelo.',
    'Que el contador esté asignado a esta categoría y que el mes del BMS esté completo.',
  ];

  /** Meses consecutivos (contando el actual) con el mismo sentido y gravedad de atención o peor. */
  function racha(celdasCategoria, c) {
    const mismo = (x) => x && x.nivel !== 'ok' && x.nivel !== 'sin_dato' && Math.sign(x.desviacion_kwh) === Math.sign(c.desviacion_kwh);
    const porMes = new Map(celdasCategoria.map((x) => [x.mes, x]));
    let n = 1;
    for (let m = c.mes - 1; mismo(porMes.get(m)); m--) n++;
    for (let m = c.mes + 1; mismo(porMes.get(m)); m++) n++;
    return n;
  }

  /** Explicación de una desviación: resumen, causas posibles, qué comprobar y persistencia. */
  function porQue(c, celdasCategoria) {
    const sentido = c.desviacion_kwh > 0 ? 'mas' : 'menos';
    const hipotesis = CAUSAS[c.categoria] || GENERICAS;
    let resumen;
    let causas;
    if (c.simulado_kwh === 0) {
      resumen = `Hay consumo real (${EN.kwh(c.real_kwh)}) pero la simulación no incluye esta categoría.`;
      causas = [
        'La categoría no está en el modelo de DesignBuilder (o se ha simulado con otro nombre).',
        'El nombre que usa el BMS no coincide con el del .dat y no se han podido emparejar.',
        'Es un consumo real que el proyecto no contempló (equipos no previstos).',
      ];
    } else {
      const sube = c.desviacion_kwh > 0;
      resumen = c.nivel === 'ok'
        ? `Dentro de lo esperado: el consumo real está un ${EN.num(Math.abs(c.desviacion_pct), 1)} % ${sube ? 'por encima' : 'por debajo'} de lo simulado.`
        : `El consumo real es un ${EN.num(Math.abs(c.desviacion_pct), 1)} % ${sube ? 'mayor' : 'menor'} que el simulado (${signo(c.desviacion_kwh)}${EN.num(Math.abs(c.desviacion_kwh), 0)} kWh).`;
      causas = hipotesis[sentido] || GENERICAS[sentido];
    }

    let persistencia = null;
    if (c.nivel !== 'ok' && c.nivel !== 'sin_dato') {
      if (c.mes === undefined || c.mes === null) {
        const afectados = celdasCategoria.filter((x) => x.nivel !== 'ok' && x.nivel !== 'sin_dato').length;
        persistencia = `${afectados} de ${celdasCategoria.length} meses con datos superan el ±10 %.`;
      } else {
        const n = racha(celdasCategoria, c);
        persistencia = n >= 2
          ? `Se repite ${n} meses seguidos: apunta a una causa estable (consignas, horarios o hipótesis del modelo) más que a un hecho puntual.`
          : 'Solo aparece este mes: busca algo concreto (avería, cambio de horario, clima extremo, mes incompleto en el BMS).';
      }
    }
    return { resumen, causas, persistencia };
  }

  // ----------------------------------------------------- contenido del detalle

  const lista = (items) => h('ul', { class: 'det-ul' }, items.map((t) => h('li', { text: t })));

  function seccion(titulo, contenido, nota) {
    return h('div', { class: 'det-sec' }, h('h4', { text: titulo }), contenido, nota ? h('p', { class: 'detalle', text: nota }) : null);
  }

  function bloqueExplicacion(p) {
    return [
      p.persistencia ? h('p', { class: 'det-resumen', text: p.persistencia }) : null,
      seccion('Posibles causas', lista(p.causas), 'Orientativas: los datos no bastan para dar un diagnóstico, sirven para decidir qué mirar primero.'),
      seccion('Qué comprobar', lista(COMPROBAR)),
    ];
  }

  function cabecera(titulo, c) {
    return h('div', { class: 'det-cab' }, punto(c.nivel), h('strong', { text: titulo }), h('span', { class: 'detalle', text: NIVEL_TEXTO[c.nivel] }));
  }

  function filasDatos(c) {
    return [
      { t: 'Simulado', v: EN.kwh(c.simulado_kwh) },
      { t: 'Real BMS', v: EN.kwh(c.real_kwh) },
      { t: 'Desviación', v: EN.kwh(c.desviacion_kwh), d: textoLargo(c), tono: TONO[c.nivel] },
      { t: 'Electricidad / gas (real)', v: `${EN.num(c.electricidad_kwh, 0)} / ${EN.num(c.gas_kwh, 0)} kWh` },
    ];
  }

  function detalleCelda(c, d) {
    const delMes = d.celdas.filter((x) => x.mes === c.mes);
    const impacto = delMes.reduce((s, x) => s + Math.abs(x.desviacion_kwh), 0);
    const peso = impacto ? (Math.abs(c.desviacion_kwh) / impacto) * 100 : 0;
    const categoria = d.celdas.filter((x) => x.categoria === c.categoria).sort((a, b) => a.mes - b.mes);
    const p = porQue(c, categoria);
    return h('div', { class: 'det' },
      cabecera(`${c.categoria} · ${EN.nombreMes(c.mes)}`, c),
      h('p', { class: 'det-resumen', text: p.resumen }),
      EN.lista([{
        titulo: 'Datos',
        filas: filasDatos(c).concat([
          { t: 'Peso en la desviación del mes', v: `${EN.num(peso, 0)} %` },
          { t: 'Evolución de la categoría', v: categoria.map((x) => `${MESES_CORTOS[x.mes - 1]} ${textoCelda(x)}`).join(' → ') },
        ]),
      }]),
      bloqueExplicacion(p));
  }

  const tablaMeses = (filas) => EN.tabla(filas, { columnas: ['periodo', 'simulado_kwh', 'real_kwh', 'desviacion_pct', 'nivel'], enFlujo: true, decimales: 0 });

  function detalleFila(cat, d) {
    const meses = d.celdas.filter((x) => x.categoria === cat.categoria).sort((a, b) => a.mes - b.mes);
    const p = porQue(Object.assign({}, cat, { mes: null }), meses);
    return h('div', { class: 'det' },
      cabecera(`${cat.categoria} · acumulado`, cat),
      h('p', { class: 'det-resumen', text: p.resumen }),
      EN.lista([{ titulo: 'Acumulado de los meses con BMS', filas: filasDatos(cat) }]),
      seccion('Mes a mes', tablaMeses(meses.map((x) => Object.assign({}, x, { periodo: EN.nombreMes(x.mes) })))),
      bloqueExplicacion(p));
  }

  function detalleColumna(total, d) {
    const celdas = d.celdas.filter((x) => x.mes === total.mes);
    const orden = celdas.slice().sort((a, b) => Math.abs(b.desviacion_kwh) - Math.abs(a.desviacion_kwh));
    const mayor = orden[0];
    return h('div', { class: 'det' },
      cabecera(`${EN.nombreMes(total.mes)} · todas las categorías`, total),
      mayor ? h('p', { class: 'det-resumen', text: `La categoría que más pesa en la desviación del mes es ${mayor.categoria} (${signo(mayor.desviacion_kwh)}${EN.num(Math.abs(mayor.desviacion_kwh), 0)} kWh, ${textoLargo(mayor)}).` }) : null,
      EN.lista([{ titulo: 'Total del mes', filas: filasDatos(total) }]),
      seccion('Categorías, de mayor a menor impacto', EN.tabla(orden, { columnas: ['categoria', 'real_kwh', 'desviacion_pct', 'nivel'], enFlujo: true, decimales: 0 })));
  }

  function detalleTotal(d) {
    const meses = d.totales_mes.slice().sort((a, b) => a.mes - b.mes);
    return h('div', { class: 'det' },
      cabecera('Total · todos los meses con BMS', d.total),
      EN.lista([{ titulo: 'Acumulado', filas: filasDatos(d.total) }]),
      seccion('Mes a mes', tablaMeses(meses.map((x) => Object.assign({}, x, { periodo: EN.nombreMes(x.mes) })))));
  }

  // ------------------------------------------------------------ mapa de calor

  function leyenda() {
    const item = (clase, texto) => h('span', { class: 'hm-ley' }, h('span', { class: `hm-muestra ${clase}` }), texto);
    return h('div', { class: 'barra-herramientas hm-leyenda' },
      item('hm-ok2', 'Correcto · hasta ±10 %'), item('hm-at1', 'Atención · ±10–20 %'), item('hm-re2', 'Revisar · más de ±20 %'), item('hm-vacio', 'Sin BMS'),
      h('span', { class: 'detalle', text: 'Cada cuadrado es la desviación del consumo real sobre el simulado. Pulsa un cuadrado, una categoría o un mes.' }));
  }

  function mapaCalor(d, ctx) {
    const porClave = new Map(d.celdas.map((c) => [`${c.categoria}|${c.mes}`, c]));
    const totalMes = new Map(d.totales_mes.map((t) => [t.mes, t]));
    const grid = h('div', { class: 'hm-grid' });
    grid.style.gridTemplateColumns = `minmax(130px, 190px) repeat(${d.meses.length}, minmax(24px, 1fr)) minmax(64px, 1.2fr)`;
    grid.style.gridTemplateRows = `auto repeat(${d.categorias.length + 1}, minmax(30px, 1fr))`;

    let marcados = [];
    const marcar = (selector) => {
      marcados.forEach((e) => e.classList.remove('sel'));
      marcados = [...grid.querySelectorAll(selector)];
      marcados.forEach((e) => e.classList.add('sel'));
    };

    const celdaBoton = (c, clase, titulo, texto, dataset, alPulsar) => {
      const el = h('button', { class: `hm-celda ${clase}`, type: 'button', title: titulo, text: texto, dataset });
      el.addEventListener('click', alPulsar);
      return el;
    };

    // Cabecera: esquina + 12 meses + acumulado
    grid.appendChild(h('div', { class: 'hm-esquina' }));
    d.meses.forEach((m) => {
      const total = totalMes.get(m.mes);
      const cab = h('button', {
        class: 'hm-cab' + (m.mes === ctx.mes ? ' activo' : ''), type: 'button', disabled: !m.con_bms,
        title: m.con_bms ? `${EN.nombreMes(m.mes)}: resumen del mes` : `${EN.nombreMes(m.mes)}: sin BMS`, text: MESES_CORTOS[m.mes - 1],
      });
      if (total) cab.addEventListener('click', () => { marcar(`[data-mes="${m.mes}"]`); EN.detalle.abrir(EN.nombreMes(m.mes), detalleColumna(total, d)); });
      cab.dataset.mes = m.mes;
      grid.appendChild(cab);
    });
    grid.appendChild(h('div', { class: 'hm-cab hm-cab-acum', text: 'Acumulado' }));

    // Una fila por categoría
    d.categorias.forEach((cat, i) => {
      const abrirFila = () => { marcar(`[data-fila="${i}"]`); EN.detalle.abrir(cat.categoria, detalleFila(cat, d)); };
      const etiqueta = h('button', { class: 'hm-fila', type: 'button', title: `${cat.categoria}: ver la categoría completa`, dataset: { fila: i } }, punto(cat.nivel), cat.categoria);
      etiqueta.addEventListener('click', abrirFila);
      grid.appendChild(etiqueta);

      d.meses.forEach((m) => {
        const c = porClave.get(`${cat.categoria}|${m.mes}`);
        if (!m.con_bms || !c) {
          grid.appendChild(h('div', { class: 'hm-celda hm-vacio', dataset: { fila: i, mes: m.mes }, title: m.con_bms ? 'Sin consumo en esta categoría' : 'Sin BMS este mes' }));
          return;
        }
        grid.appendChild(celdaBoton(c, claseCelda(c), `${cat.categoria} · ${EN.nombreMes(m.mes)}: ${textoLargo(c)} (${EN.kwh(c.desviacion_kwh)})`, textoCelda(c), { fila: i, mes: m.mes },
          () => { marcar(`.hm-celda[data-fila="${i}"][data-mes="${m.mes}"]`); EN.detalle.abrir(`${cat.categoria} · ${EN.nombreMes(m.mes)}`, detalleCelda(c, d)); }));
      });
      grid.appendChild(celdaBoton(cat, `hm-acum ${claseCelda(cat)}`, `${cat.categoria}, acumulado: ${textoLargo(cat)}`, textoCelda(cat), { fila: i, mes: 'total' }, abrirFila));
    });

    // Fila de totales por mes
    const etiquetaTotal = h('button', { class: 'hm-fila hm-total', type: 'button', title: 'Total de todos los meses', dataset: { fila: 'total' } }, punto(d.total.nivel), 'Total');
    etiquetaTotal.addEventListener('click', () => { marcar('[data-fila="total"]'); EN.detalle.abrir('Total', detalleTotal(d)); });
    grid.appendChild(etiquetaTotal);
    d.meses.forEach((m) => {
      const t = totalMes.get(m.mes);
      if (!t) { grid.appendChild(h('div', { class: 'hm-celda hm-vacio', dataset: { fila: 'total', mes: m.mes } })); return; }
      grid.appendChild(celdaBoton(t, `hm-total ${claseCelda(t)}`, `${EN.nombreMes(m.mes)}, total: ${textoLargo(t)}`, textoCelda(t), { fila: 'total', mes: m.mes },
        () => { marcar(`[data-mes="${m.mes}"]`); EN.detalle.abrir(EN.nombreMes(m.mes), detalleColumna(t, d)); }));
    });
    grid.appendChild(celdaBoton(d.total, `hm-acum hm-total ${claseCelda(d.total)}`, `Total acumulado: ${textoLargo(d.total)}`, textoCelda(d.total), { fila: 'total', mes: 'total' },
      () => { marcar('[data-fila="total"]'); EN.detalle.abrir('Total', detalleTotal(d)); }));

    return EN.vista(leyenda(), h('div', { class: 'hm-wrap' }, grid));
  }

  // ------------------------------------------------------ resumen por gravedad

  function resumen(d) {
    const est = EN.sel.alertas || (EN.sel.alertas = { ambito: 'acum', orden: 'asc' });
    const filasBase = est.ambito === 'acum'
      ? d.categorias.map((c) => Object.assign({}, c, { periodo: 'Acumulado' }))
      : d.celdas.map((c) => Object.assign({}, c, { periodo: EN.nombreMes(c.mes) }));
    const filas = filasBase.filter((c) => c.nivel !== 'sin_dato');
    const peso = (c) => (c.desviacion_pct === null ? Infinity : Math.abs(c.desviacion_pct));
    filas.sort((a, b) => (peso(a) - peso(b)) || (Math.abs(a.desviacion_kwh) - Math.abs(b.desviacion_kwh)));
    if (est.orden === 'desc') filas.reverse();

    const cuenta = (n) => filas.filter((c) => c.nivel === n).length;
    const boton = (texto, activo, alPulsar) => h('button', { class: activo ? 'btn-primary' : 'btn-secondary', type: 'button', text: texto, onclick: alPulsar });
    const barra = h('div', { class: 'barra-herramientas' },
      boton('Acumulado por categoría', est.ambito === 'acum', () => { est.ambito = 'acum'; EN.refrescar(); }),
      boton('Por categoría y mes', est.ambito === 'mes', () => { est.ambito = 'mes'; EN.refrescar(); }),
      boton(est.orden === 'asc' ? 'De menos a más graves' : 'De más a menos graves', false, () => { est.orden = est.orden === 'asc' ? 'desc' : 'asc'; EN.refrescar(); }),
      h('span', { class: 'detalle', text: `${cuenta('ok')} correctas · ${cuenta('atencion')} en atención · ${cuenta('revisar')} por revisar` }));

    const tabla = EN.tabla(filas, {
      columnas: ['nivel', 'categoria', 'periodo', 'simulado_kwh', 'real_kwh', 'desviacion_kwh', 'desviacion_pct'],
      alClic: (f, tr) => {
        tr.parentElement.querySelectorAll('tr.sel').forEach((x) => x.classList.remove('sel'));
        tr.classList.add('sel');
        if (est.ambito === 'acum') EN.detalle.abrir(f.categoria, detalleFila(f, d));
        else EN.detalle.abrir(`${f.categoria} · ${EN.nombreMes(f.mes)}`, detalleCelda(f, d));
      },
      vacio: 'No hay desviaciones que mostrar.',
    });
    return EN.vista(barra, tabla);
  }

  EN.ESC_ALERTAS = {
    id: 'alertas', icono: 'triangle-alert', titulo: 'Alertas',
    subs: [
      { id: 'mapa', titulo: 'Mapa de calor', render: EN.conDatos('alertas', null, mapaCalor) },
      { id: 'resumen', titulo: 'Resumen por gravedad', render: EN.conDatos('alertas', null, resumen) },
    ],
  };
})();
