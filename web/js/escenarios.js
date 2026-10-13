/* Catálogo de escenarios y subescenarios. Cada subescenario es una vista que ocupa todo el
   canvas: render(ctx) devuelve un nodo DOM (o una promesa de nodo). Los subescenarios son
   las secciones que antes se apilaban con scroll dentro de cada pestaña. Alertas y Constructor
   viven en alertas.js y constructor.js. Resúmenes y formularios usan el mismo listado de dos
   columnas (EN.lista): título · valor, con los avisos al final y su marca de gravedad. */
(function () {
  'use strict';
  const EN = window.EN;
  const h = EN.h;
  const E = EN.E;
  const { vista, sinEdificio, conDatos, consulta } = EN;

  const mensaje = (texto, tono) => h('div', { class: 'estado-card ' + (tono || ''), text: texto });
  const resultadoForm = (slot, texto, tono) => slot.replaceChildren(mensaje(texto, tono));
  const nombreFichero = (f) => (f ? f.name : '');
  const fila = (campo) => ({ t: campo.t, nodo: campo.input });

  /** Resumen con gráfico: la lista ocupa su altura natural y el gráfico se queda con el hueco que sobra,
      así las vistas con pocos indicadores no dejan medio canvas vacío. Sin figura, solo la lista. */
  const resumenConGrafico = (lista, fig) => vista(null, fig
    ? h('div', { class: 'lista-grafico' }, h('div', { class: 'lista-arriba' }, lista), h('div', { class: 'lista-hueco' }, EN.grafico(fig)))
    : lista, !fig);

  const TEXTO_TONO = { ok: 'Dentro de ±10 %', warn: 'Entre ±10 % y ±20 %', mal: 'Por encima de ±20 %' };

  // ----------------------------------------------------------------- Panel

  const panel = {
    id: 'panel', icono: 'layout-dashboard', titulo: 'Panel',
    subs: [
      {
        id: 'resumen', titulo: 'Resumen',
        render: conDatos('panel', null, (d) => {
          const k = d.kpis;
          return resumenConGrafico(EN.lista([
            {
              titulo: 'Indicadores',
              filas: [
                { t: 'Meses BMS', v: `${k.meses_bms}/12` },
                { t: 'Consumo acumulado', v: EN.kwh(k.consumo_acumulado_kwh) },
                { t: `${k.indicador_etiqueta} acumulado`, v: EN.num(k.indicador_valor, 2) },
                { t: 'Desviación del mes', v: k.desviacion_mes_pct === null ? 'Sin dato' : EN.pct(k.desviacion_mes_pct) },
                { t: 'Cobertura anual', v: `${EN.num(k.cobertura_pct, 0)} %` },
              ],
            },
            {
              titulo: 'Avisos',
              filas: [
                { t: 'Simulación activa', v: d.simulacion_activa || 'No hay simulación activa', tono: d.simulacion_activa ? 'ok' : 'warn' },
                {
                  t: 'Alertas del mes',
                  v: k.alertas_mes === 0 ? 'Sin alertas relevantes en el mes activo' : `${k.alertas_mes} categorías superan el 10 % de desviación`,
                  tono: k.alertas_mes === 0 ? 'ok' : 'warn',
                },
              ],
            },
          ]), d.fig_consumo);
        }),
      },
      {
        id: 'edificio', titulo: 'Edificio',
        render: conDatos('panel', null, (d) => {
          const e = d.edificio;
          const v = (x) => (x === null || x === undefined || x === '' ? '—' : String(x));
          return vista(null, EN.lista([{
            titulo: 'Ficha del edificio',
            filas: [
              { t: 'Nombre', v: v(e.nombre) }, { t: 'Código', v: v(e.codigo_proyecto) }, { t: 'Cliente', v: v(e.cliente) },
              { t: 'Ubicación', v: v(e.ubicacion) }, { t: 'Uso', v: v(e.uso) }, { t: 'Categoría', v: v(e.categoria_edificio) },
              { t: 'Superficie', v: `${EN.num(e.superficie_m2)} m²` }, { t: 'Referencia', v: `${EN.num(d.referencia.valor)} ${d.referencia.unidad}` },
              { t: 'Sistema de climatización', v: v(e.sistema_climatizacion) }, { t: 'Horario de uso', v: v(e.horario_uso) },
              { t: 'Observaciones', v: v(e.observaciones) },
            ],
          }]), true);
        }),
      },
      {
        id: 'consumo', titulo: 'Consumo BMS acumulado',
        render: conDatos('panel', null, (d) => vista(null, EN.grafico(d.fig_consumo, 'No hay BMS cargado para este año.'))),
      },
      {
        id: 'tabla', titulo: 'Consumo mensual (tabla)',
        render: conDatos('panel', null, (d) => vista(null, EN.tabla(d.resumen_mes, { vacio: 'No hay BMS cargado para este año.' }))),
      },
    ],
  };

  // ------------------------------------------------------------- Edificios

  /** Formulario de edificio compartido por Crear y Editar: lista de dos columnas (título · campo). */
  function formEdificio(v, modo, alGuardar) {
    v = v || {};
    const cfg = EN.cfg;
    const c = {
      codigo: modo === 'crear' ? EN.campo({ name: 'codigo_proyecto', t: 'Código', ph: 'EDIF-2026-001' }) : null,
      nombre: EN.campo({ name: 'nombre', t: 'Nombre', valor: v.nombre }),
      cliente: EN.campo({ name: 'cliente', t: 'Cliente', valor: v.cliente }),
      ubicacion: EN.campo({ name: 'ubicacion', t: 'Ubicación', valor: v.ubicacion }),
      categoria: EN.campo({ name: 'categoria_edificio', t: 'Categoría de edificio', tipo: 'select', opciones: cfg.tipos_edificio, valor: v.categoria_edificio || cfg.tipos_edificio[0] }),
      uso: EN.campo({ name: 'uso', t: 'Uso', valor: v.uso }),
      superficie: EN.campo({ name: 'superficie_m2', t: 'Superficie (m²)', tipo: 'number', paso: 100, min: 0, valor: v.superficie_m2 || 0 }),
      unidad: EN.campo({ name: 'unidad_referencia', t: 'Unidad principal para comparar', tipo: 'select', opciones: cfg.unidades_referencia, valor: v.unidad_referencia || cfg.unidades_referencia[0] }),
      valorUnidad: EN.campo({ name: 'valor_unidad_referencia', t: 'Valor de la unidad principal', tipo: 'number', paso: 1, min: 0, valor: v.valor_unidad_referencia || 0 }),
      habitaciones: EN.campo({ name: 'habitaciones', t: 'Habitaciones', tipo: 'number', paso: 1, min: 0, valor: v.habitaciones || 0 }),
      puestos: EN.campo({ name: 'puestos_trabajo', t: 'Puestos de trabajo', tipo: 'number', paso: 1, min: 0, valor: v.puestos_trabajo || 0 }),
      camas: EN.campo({ name: 'camas', t: 'Camas', tipo: 'number', paso: 1, min: 0, valor: v.camas || 0 }),
      horario: EN.campo({ name: 'horario_uso', t: 'Horario de uso', ph: 'Ej. 24/7, laborables 8-20 h', valor: v.horario_uso }),
      sistema: EN.campo({ name: 'sistema_climatizacion', t: 'Sistema de climatización', valor: v.sistema_climatizacion }),
      obs: EN.campo({ name: 'observaciones', t: 'Observaciones', tipo: 'textarea', valor: v.observaciones }),
    };
    const slot = h('div');
    const boton = h('button', { class: 'btn-primary', type: 'submit', text: modo === 'crear' ? 'Crear edificio' : 'Guardar cambios' });
    const form = h('form', { class: 'formulario' },
      EN.lista([
        { titulo: 'Identificación', filas: [c.codigo, c.nombre, c.cliente, c.ubicacion].filter(Boolean).map(fila) },
        { titulo: 'Clasificación', filas: [c.categoria, c.uso, c.superficie].map(fila) },
        { titulo: 'Referencia para comparar edificios', filas: [c.unidad, c.valorUnidad].map(fila) },
        { titulo: 'Características', filas: [c.habitaciones, c.puestos, c.camas, c.horario, c.sistema].map(fila) },
        { titulo: 'Observaciones', filas: [fila(c.obs)] },
      ]),
      h('div', { class: 'acciones' }, boton), slot);
    form.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      boton.disabled = true;
      try {
        await alGuardar(EN.valores(form), slot);
      } catch (e) {
        resultadoForm(slot, e.message, 'mal');
      } finally {
        boton.disabled = false;
      }
    });
    return h('div', { class: 'form-wrap' }, form);
  }

  function selectorEdificio(lista, actual, alCambiar) {
    const c = EN.campo({
      name: 'edificio', t: 'Edificio', tipo: 'select',
      opciones: lista.map((e) => ({ v: e.codigo_proyecto, t: `${e.codigo_proyecto} - ${e.nombre}` })), valor: actual,
    });
    c.input.addEventListener('change', () => { alCambiar(c.input.value); c.input.blur(); });
    return EN.lista([{ filas: [fila(c)] }]);
  }

  function edificioElegido(ctx) {
    const todos = EN.edificiosTodos || [];
    const cod = (todos.some((e) => e.codigo_proyecto === EN.sel.edificio) && EN.sel.edificio) || ctx.codigo || (todos[0] && todos[0].codigo_proyecto);
    return { todos, codigo: cod, edificio: todos.find((e) => e.codigo_proyecto === cod) };
  }

  const edificios = {
    id: 'edificios', icono: 'building-2', titulo: 'Edificios',
    subs: [
      {
        id: 'crear', titulo: 'Crear',
        render: () => vista(null, formEdificio(null, 'crear', async (valores) => {
          const r = await EN.api('/api/edificios', { method: 'POST', json: valores });
          E.codigo = r.codigo;
          EN.toast(`Edificio ${r.codigo} creado.`);
          await EN.alCambiarDatos();
          EN.refrescar();
        })),
      },
      {
        id: 'editar', titulo: 'Editar',
        render: (ctx) => {
          const { todos, codigo, edificio } = edificioElegido(ctx);
          if (!edificio) return EN.aviso('No hay edificios.', 'warn');
          const selector = selectorEdificio(todos, codigo, (c) => { EN.sel.edificio = c; EN.refrescar(); });
          const form = formEdificio(edificio, 'editar', async (valores, slot) => {
            await EN.api(`/api/edificios/${encodeURIComponent(codigo)}`, { method: 'PUT', json: valores });
            EN.toast('Edificio actualizado.');
            await EN.alCambiarDatos();
            resultadoForm(slot, 'Cambios guardados.', 'ok');
          });
          return vista(selector, form);
        },
      },
      {
        id: 'estado', titulo: 'Archivar / Reactivar',
        render: (ctx) => {
          const { todos, codigo } = edificioElegido(ctx);
          if (!todos.length) return EN.aviso('No hay edificios.', 'warn');
          const cambiar = async (estado) => {
            try {
              await EN.api(`/api/edificios/${encodeURIComponent(codigo)}/estado`, { method: 'POST', json: { estado } });
              EN.toast(estado === 'ARCHIVADO' ? 'Edificio archivado.' : 'Edificio reactivado.');
              await EN.alCambiarDatos();
              EN.refrescar();
            } catch (e) { EN.toast(e.message, 4000); }
          };
          const barra = h('div', { class: 'barra-herramientas' },
            h('span', { text: `Seleccionado: ${codigo}` }),
            h('button', { class: 'btn-secondary', text: 'Archivar', onclick: () => cambiar('ARCHIVADO') }),
            h('button', { class: 'btn-primary', text: 'Reactivar', onclick: () => cambiar('ACTIVO') }));
          const tabla = EN.tabla(todos, {
            columnas: ['codigo_proyecto', 'nombre', 'cliente', 'ubicacion', 'categoria_edificio', 'superficie_m2', 'estado'],
            alClic: (f) => { EN.sel.edificio = f.codigo_proyecto; EN.refrescar(); },
            seleccion: (f) => f.codigo_proyecto === codigo,
          });
          return vista(barra, tabla);
        },
      },
      {
        id: 'eliminar', titulo: 'Eliminar',
        render: async (ctx) => {
          const { todos, codigo } = edificioElegido(ctx);
          if (!todos.length) return EN.aviso('No hay edificios para eliminar.', 'warn');
          const d = await EN.datos(`/api/edificios/${encodeURIComponent(codigo)}/eliminacion`);
          if (d.aviso) return EN.aviso(d.aviso, 'warn');
          const r = d.resumen;
          const confirmacion = EN.campo({ name: 'confirmacion', t: `Escribe ${codigo} para confirmar`, ph: codigo });
          const acepta = EN.campo({ name: 'acepta', t: 'Entiendo que esta acción no se puede deshacer', tipo: 'checkbox' });
          const boton = h('button', { class: 'btn-danger', type: 'button', text: 'Eliminar proyecto definitivamente', disabled: true });
          const slot = h('div');
          const validar = () => { boton.disabled = !(acepta.input.checked && confirmacion.input.value.trim().toUpperCase() === codigo.toUpperCase()); };
          confirmacion.input.addEventListener('input', validar);
          acepta.input.addEventListener('change', validar);
          boton.addEventListener('click', async () => {
            boton.disabled = true;
            try {
              const res = await EN.api(`/api/edificios/${encodeURIComponent(codigo)}/eliminar`, { method: 'POST', json: { confirmacion: confirmacion.input.value } });
              EN.sel.edificio = null;
              EN.toast(`Proyecto eliminado: ${res.simulaciones} simulaciones y ${res.consumos_bms} importaciones BMS.`, 4000);
              await EN.alCambiarDatos();
              EN.refrescar();
            } catch (e) { resultadoForm(slot, e.message, 'mal'); validar(); }
          });
          const cuerpo = h('div', { class: 'form-wrap' }, h('div', { class: 'formulario' },
            EN.lista([
              { titulo: 'Proyecto', filas: [{ t: 'Nombre', v: d.edificio.nombre || '—' }, { t: 'Cliente', v: d.edificio.cliente || '—' }, { t: 'Estado', v: d.edificio.estado || '—' }] },
              {
                titulo: 'Datos que se borrarán',
                filas: [
                  { t: 'Simulaciones', v: String(r.simulaciones) }, { t: 'Filas de simulación', v: EN.num(r.detalle_simulaciones) },
                  { t: 'BMS importados', v: String(r.consumos_bms) }, { t: 'Filas BMS', v: EN.num(r.detalle_bms) },
                ],
              },
              {
                titulo: 'Aviso',
                filas: [{ t: 'Alcance', v: 'Se borran el edificio y sus datos de simulaciones y BMS en la base de datos. Las carpetas y archivos guardados se conservan.', tono: 'warn' }],
              },
              { titulo: 'Confirmación', filas: [fila(confirmacion), fila(acepta)] },
            ]),
            h('div', { class: 'acciones' }, boton), slot));
          return vista(selectorEdificio(todos, codigo, (c) => { EN.sel.edificio = c; EN.refrescar(); }), cuerpo);
        },
      },
    ],
  };

  // ---------------------------------------------------------- Simulaciones

  /** Simulación elegida en la tabla; por defecto la activa o la primera. */
  const simElegida = (lista) => lista.find((s) => s.id === EN.sel.sim) || lista.find((s) => s.activa) || lista[0];

  async function conSimulacion(ctx, construir) {
    if (!ctx.codigo) return sinEdificio();
    const d = await EN.datos(`/api/simulaciones?${EN.qs({ codigo: ctx.codigo })}`);
    if (!d.simulaciones.length) return EN.aviso('No hay simulaciones. Importa un .dat en Simulaciones › Importar.', 'warn');
    const sim = simElegida(d.simulaciones);
    const det = await EN.datos(`/api/simulaciones/${sim.id}/detalle`);
    if (det.aviso) return EN.aviso(det.aviso, 'warn');
    return construir(sim, det);
  }

  const etiquetaSim = (s) => h('span', { text: `Simulación #${s.id} · ${s.nombre_simulacion}${s.activa ? ' (activa)' : ''}` });

  const simulaciones = {
    id: 'simulaciones', icono: 'chart-line', titulo: 'Simulaciones',
    subs: [
      {
        // Material interno: se aporta a mano cada vez que hay una simulación nueva (no llega por correo).
        id: 'importar', titulo: 'Importar .dat',
        render: (ctx) => {
          if (!ctx.codigo) return sinEdificio();
          let archivo = null;
          const nombreArchivo = h('div', { class: 'detalle', text: 'Ningún archivo seleccionado' });
          const poner = (lista) => {
            const f = lista.find((x) => /\.(dat|txt)$/i.test(x.name));
            if (!f) { EN.toast('Aquí va un archivo .dat de DesignBuilder.'); return; }
            archivo = f;
            nombreArchivo.textContent = nombreFichero(archivo);
          };
          const zona = EN.zonaArchivos({ texto: 'Arrastra aquí el .dat de DesignBuilder', accept: '.dat,.txt', multiple: false, alAnadir: poner });
          EN.receptores = { dat: poner };
          const pendiente = EN.recogerArchivos('dat');
          if (pendiente.length) poner(pendiente);
          const campos = {
            nombre: EN.campo({ name: 'nombre', t: 'Nombre de la simulación', valor: 'Simulación DesignBuilder' }),
            anio: EN.campo({ name: 'anio', t: 'Año', tipo: 'number', min: 2000, max: 2100, paso: 1, valor: ctx.anio }),
            descripcion: EN.campo({ name: 'descripcion', t: 'Descripción', tipo: 'textarea' }),
            activa: EN.campo({ name: 'activa', t: 'Marcar como activa', tipo: 'checkbox', valor: true }),
          };
          const slot = h('div');
          const boton = h('button', { class: 'btn-primary', type: 'submit', text: 'Importar simulación' });
          const form = h('form', { class: 'formulario' },
            EN.lista([{
              titulo: 'Nueva simulación',
              filas: [fila(campos.nombre), fila(campos.anio), fila(campos.descripcion), fila(campos.activa), { t: 'Archivo .dat', nodo: h('div', {}, zona, nombreArchivo) }],
            }]),
            h('div', { class: 'acciones' }, boton), slot);
          form.addEventListener('submit', async (ev) => {
            ev.preventDefault();
            if (!archivo) { resultadoForm(slot, 'Elige o arrastra un archivo .dat.', 'mal'); return; }
            const datos = new FormData();
            datos.set('codigo', ctx.codigo);
            datos.set('nombre', campos.nombre.input.value);
            datos.set('descripcion', campos.descripcion.input.value);
            datos.set('anio', campos.anio.input.value);
            datos.set('activa', campos.activa.input.checked ? '1' : '0');
            datos.set('archivo', archivo, nombreFichero(archivo));
            boton.disabled = true;
            try {
              const r = await EN.api('/api/simulaciones', { method: 'POST', form: datos });
              EN.toast('Simulación importada.');
              await EN.alCambiarDatos();
              EN.sel.sim = r.sim_id;
              EN.llenar(slot,
                mensaje(`Simulación importada: ${EN.num(r.filas)} filas.`, 'ok'),
                r.ignoradas.length ? mensaje(`Categorías ignoradas: ${r.ignoradas.join(', ')}`, 'warn') : null,
                h('div', { style: 'margin-top: 12px; max-height: 320px; position: relative; display: flex' }, EN.tabla(r.vista_previa, { enFlujo: true })));
            } catch (e) { resultadoForm(slot, e.message, 'mal'); } finally { boton.disabled = false; }
          });
          return vista(null, h('div', { class: 'form-wrap' }, form));
        },
      },
      {
        id: 'existentes', titulo: 'Existentes',
        render: async (ctx) => {
          if (!ctx.codigo) return sinEdificio();
          const d = await EN.datos(`/api/simulaciones?${EN.qs({ codigo: ctx.codigo })}`);
          if (!d.simulaciones.length) return EN.aviso('No hay simulaciones. Importa un .dat en Simulaciones › Importar.', 'warn');
          const sim = simElegida(d.simulaciones);
          const activar = async () => {
            try {
              await EN.api(`/api/simulaciones/${sim.id}/activar`, { method: 'POST', json: { codigo: ctx.codigo } });
              EN.toast('Simulación marcada como activa.');
              await EN.alCambiarDatos();
              EN.refrescar();
            } catch (e) { EN.toast(e.message, 4000); }
          };
          const barra = h('div', { class: 'barra-herramientas' }, etiquetaSim(sim),
            h('button', { class: 'btn-primary', text: 'Marcar como activa', disabled: !!sim.activa, onclick: activar }));
          return vista(barra, EN.tabla(d.simulaciones, {
            columnas: ['id', 'nombre_simulacion', 'descripcion', 'activa', 'fecha_creacion'],
            alClic: (f) => { EN.sel.sim = f.id; EN.refrescar(); },
            seleccion: (f) => f.id === sim.id,
          }));
        },
      },
      {
        id: 'detalle', titulo: 'Detalle',
        render: (ctx) => conSimulacion(ctx, (sim, det) => vista(
          h('div', { class: 'barra-herramientas' }, etiquetaSim(sim)),
          EN.tabla(det.detalle, { columnas: ['anio', 'mes', 'categoria', 'consumo_kwh'] }))),
      },
      {
        id: 'grafico', titulo: 'Consumo por categoría',
        render: (ctx) => conSimulacion(ctx, (sim, det) => vista(
          h('div', { class: 'barra-herramientas' }, etiquetaSim(sim)), EN.grafico(det.figura))),
      },
    ],
  };

  // ------------------------------------------------------------------- BMS

  /** Lista de CSV para importar (arrastrar y soltar o elegir). La columna Origen deja sitio a los que lleguen por correo. */
  async function bandejaCsv(ctx) {
    // CSV que han llegado por correo y esperan en la bandeja de este edificio (si el correo falla, la lista manual sigue).
    let recibidos = [];
    let correoEstado = { configurado: false };
    try {
      [recibidos, correoEstado] = await Promise.all([
        EN.api(`/api/bandeja?${EN.qs({ codigo: ctx.codigo })}`).then((r) => r.items),
        EN.api('/api/correo/estado'),
      ]);
    } catch (e) { /* sin correo */ }
    const fechaCorta = (iso) => (iso ? new Date(iso).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' }) : '');
    const items = recibidos.map((r) => ({
      archivo: { name: r.archivo }, origen: 'Correo', mes: r.mes, anio: r.anio, bandejaId: r.id, estado: 'pendiente', mensaje: '',
      detalle: `${r.asunto} · ${fechaCorta(r.recibido)} · año ${r.anio}`,
    }));
    const opcionesMes = EN.cfg.meses.map((m) => ({ v: m.num, t: `${String(m.num).padStart(2, '0')} - ${m.nombre}` }));
    const detectarMes = (nombre) => {
      const m = /(20\d{2})[_\-.](0?[1-9]|1[0-2])(?!\d)/.exec(nombre);
      return m ? Number(m[2]) : ctx.mes;
    };
    const ESTADOS = { pendiente: ['warn', 'Pendiente'], importando: [null, 'Importando…'], importado: ['ok', 'Importado'], error: ['mal', 'Error'] };

    const cuerpo = h('tbody');
    const tabla = h('div', { class: 'tabla-wrap en-flujo' },
      h('table', { class: 'datos' }, h('thead', {}, h('tr', {}, ['Archivo', 'Origen', 'Mes', 'Estado', ''].map((t) => h('th', { text: t })))), cuerpo));
    const vacio = h('div', { class: 'detalle', text: 'Todavía no hay archivos en la lista. Arrastra aquí los CSV del BMS o elígelos.' });
    const botonTodos = h('button', { class: 'btn-primary', type: 'button', text: 'Importar todos' });
    const botonVaciar = h('button', { class: 'btn-secondary', type: 'button', text: 'Vaciar lista' });

    async function importar(it) {
      it.estado = 'importando';
      it.mensaje = '';
      pintar();
      try {
        let r;
        if (it.bandejaId) {
          // Viene del correo: el archivo ya está en el servidor.
          r = await EN.api('/api/bandeja/importar', { method: 'POST', json: { codigo: ctx.codigo, id: it.bandejaId, anio: it.anio, mes: it.mes } });
        } else {
          const datos = new FormData();
          datos.set('codigo', ctx.codigo);
          datos.set('anio', ctx.anio);
          datos.set('meses', JSON.stringify([it.mes]));
          datos.set('descripcion', `Importación desde la lista (${it.origen})`);
          datos.append('archivos', it.archivo, it.archivo.name);
          r = await EN.api('/api/bms', { method: 'POST', form: datos });
        }
        const x = r.resultados[0];
        if (x.ok) {
          it.estado = 'importado';
          it.mensaje = `${EN.nombreMes(x.mes)} · ${EN.num(x.filas)} filas`;
          await EN.alCambiarDatos();
        } else {
          it.estado = 'error';
          it.mensaje = x.errores.join(' · ');
        }
      } catch (e) {
        it.estado = 'error';
        it.mensaje = e.message;
      }
      pintar();
    }

    async function quitar(it) {
      if (it.bandejaId && it.estado !== 'importado') {
        try {
          await EN.api('/api/bandeja/descartar', { method: 'POST', json: { codigo: ctx.codigo, id: it.bandejaId } });
        } catch (e) { EN.toast(e.message, 4000); return; }
      }
      items.splice(items.indexOf(it), 1);
      pintar();
    }

    function filaItem(it) {
      const [tono, texto] = ESTADOS[it.estado];
      const cerrada = it.estado === 'importado' || it.estado === 'importando';
      const mes = h('select', { disabled: cerrada }, opcionesMes.map((o) => h('option', { value: o.v, text: o.t })));
      mes.value = String(it.mes);
      mes.addEventListener('change', () => { it.mes = Number(mes.value); });
      return h('tr', {},
        h('td', {}, it.archivo.name, it.detalle ? h('div', { class: 'detalle', text: it.detalle }) : null),
        h('td', { text: it.origen }),
        h('td', {}, mes),
        h('td', {}, tono ? h('span', { class: `punto ${tono}`, 'aria-hidden': 'true' }) : null, texto, it.mensaje ? h('div', { class: 'detalle', text: it.mensaje }) : null),
        h('td', {}, h('div', { class: 'acciones-fila' },
          h('button', { class: 'btn-primary', type: 'button', text: 'Importar', disabled: cerrada, onclick: () => importar(it) }),
          h('button', {
            class: 'btn-secondary', type: 'button', text: it.bandejaId ? 'Descartar' : 'Quitar', disabled: it.estado === 'importando',
            title: it.bandejaId ? 'Lo saca de la bandeja sin importarlo (el archivo se conserva)' : '',
            onclick: () => quitar(it),
          }))));
    }

    function pintar() {
      cuerpo.replaceChildren(...items.map(filaItem));
      tabla.hidden = !items.length;
      vacio.hidden = items.length > 0;
      botonTodos.disabled = !items.some((i) => i.estado === 'pendiente' || i.estado === 'error');
      botonVaciar.disabled = !items.length;
    }

    botonTodos.addEventListener('click', async () => {
      for (const it of items.filter((i) => i.estado === 'pendiente' || i.estado === 'error')) await importar(it);
    });
    botonVaciar.addEventListener('click', () => { items.splice(0, items.length); pintar(); });

    const anadir = (lista) => {
      const validos = lista.filter((f) => /\.csv$/i.test(f.name));
      if (validos.length < lista.length) EN.toast('Solo se admiten archivos .csv.');
      validos.forEach((archivo) => items.push({ archivo, origen: 'Manual', mes: detectarMes(archivo.name), estado: 'pendiente', mensaje: '' }));
      pintar();
    };
    const zona = EN.zonaArchivos({ texto: 'Arrastra aquí los CSV del BMS', accept: '.csv', multiple: true, alAnadir: anadir });
    EN.receptores = { csv: anadir };

    // Cómo se reconoce el correo que trae los CSV de este edificio (se guarda al salir de cada campo).
    const asunto = EN.campo({ name: 'correo_asunto', t: 'Palabras clave del asunto', valor: (ctx.edificio && ctx.edificio.correo_asunto) || '', ph: 'Ej. CSV monitorización' });
    const remitente = EN.campo({ name: 'correo_remitente', t: 'Remitente (opcional)', valor: (ctx.edificio && ctx.edificio.correo_remitente) || '', ph: 'Ej. @empresa.com' });
    const guardado = h('span', { class: 'detalle' });
    const guardarCorreo = async () => {
      try {
        await EN.api(`/api/edificios/${encodeURIComponent(ctx.codigo)}/correo`, { method: 'POST', json: { asunto: asunto.input.value, remitente: remitente.input.value } });
        guardado.textContent = 'Guardado.';
        await EN.alCambiarDatos();
      } catch (e) {
        guardado.textContent = e.message;
      }
    };
    [asunto, remitente].forEach((c) => c.input.addEventListener('change', guardarCorreo));

    const botonRevisar = h('button', { class: 'btn-secondary', type: 'button', text: 'Revisar correo ahora' });
    botonRevisar.addEventListener('click', async () => {
      botonRevisar.disabled = true;
      try {
        const r = await EN.api('/api/correo/revisar', { method: 'POST', json: {} });
        EN.toast(r.nuevos ? `${r.nuevos} CSV nuevo(s) en la bandeja.` : 'No hay correos nuevos para este edificio.', 4000);
        EN.refrescar();
      } catch (e) { EN.toast(e.message, 6000); } finally { botonRevisar.disabled = false; }
    });
    const textoBuzon = !correoEstado.configurado
      ? 'Sin configurar: faltan las variables ENERGIA_IMAP_… en el equipo del servidor'
      : `${correoEstado.buzon} · ${correoEstado.ultima_revision ? `última revisión ${fechaCorta(correoEstado.ultima_revision)}` : 'aún sin revisar'}`
        + `${correoEstado.automatico_cada_min ? ` · automática cada ${correoEstado.automatico_cada_min} min` : ''}`
        + `${correoEstado.error ? ` · error: ${correoEstado.error}` : ''}`;
    const tonoBuzon = correoEstado.error ? 'mal' : correoEstado.configurado ? 'ok' : 'warn';

    const correo = h('div', {},
      EN.lista([{
        titulo: `Correo de origen · ${ctx.codigo}`,
        filas: [
          fila(asunto),
          fila(remitente),
          { t: 'Buzón', v: textoBuzon, tono: tonoBuzon },
          { t: 'Revisar', nodo: botonRevisar },
          { t: 'Cómo se usa', v: 'Los correos cuyo asunto contenga todas las palabras clave (y cuyo remitente coincida, si lo rellenas) dejan sus CSV en la lista, con origen Correo, para importarlos o descartarlos.' },
        ],
      }]),
      guardado);

    pintar();
    anadir(EN.recogerArchivos('csv'));
    return vista(
      h('div', { class: 'barra-herramientas' }, h('span', { class: 'detalle', text: `Destino: ${ctx.codigo} · año ${ctx.anio}. El mes se propone a partir del nombre del archivo.` })),
      h('div', { class: 'bandeja' }, correo, zona, vacio, tabla, h('div', { class: 'acciones' }, botonTodos, botonVaciar)), true);
  }

  const bms = {
    id: 'bms', icono: 'gauge', titulo: 'BMS',
    subs: [
      { id: 'importar', titulo: 'Importar CSV', render: (ctx) => (ctx.codigo ? bandejaCsv(ctx) : sinEdificio()) },
      {
        id: 'existentes', titulo: 'Existentes',
        render: async (ctx) => {
          if (!ctx.codigo) return sinEdificio();
          const d = await EN.datos(`/api/bms?${EN.qs({ codigo: ctx.codigo })}`);
          if (!d.bms.length) return EN.aviso('No hay consumos BMS. Importa un CSV en BMS › Importar.', 'warn');
          const elegido = d.bms.find((b) => b.id === EN.sel.bms) || d.bms[0];
          return vista(null, EN.tabla(d.bms, {
            columnas: ['id', 'anio', 'mes', 'nombre_importacion', 'descripcion'],
            alClic: (f) => { EN.sel.bms = f.id; EN.refrescar(); },
            seleccion: (f) => f.id === elegido.id,
          }));
        },
      },
      {
        id: 'detalle', titulo: 'Detalle',
        render: async (ctx) => {
          if (!ctx.codigo) return sinEdificio();
          const d = await EN.datos(`/api/bms?${EN.qs({ codigo: ctx.codigo })}`);
          if (!d.bms.length) return EN.aviso('No hay consumos BMS. Importa un CSV en BMS › Importar.', 'warn');
          const b = d.bms.find((x) => x.id === EN.sel.bms) || d.bms[0];
          const det = await EN.datos(`/api/bms/${b.id}/detalle`);
          if (det.aviso) return EN.aviso(det.aviso, 'warn');
          return vista(
            h('div', { class: 'barra-herramientas' }, h('span', { text: `Importación #${b.id} · ${b.anio}-${String(b.mes).padStart(2, '0')} · ${b.nombre_importacion}` })),
            EN.tabla(det.detalle));
        },
      },
    ],
  };

  // ------------------------------------------------------------ Comparativa

  const resumenMes = conDatos('comparativa/mes', null, (d) => {
    const k = d.kpis;
    const tono = EN.tonoDesviacion(k.desviacion_pct);
    return resumenConGrafico(EN.lista([
      {
        titulo: 'Indicadores',
        filas: [
          { t: 'Simulado', v: EN.kwh(k.simulado_kwh) },
          { t: 'Real BMS', v: EN.kwh(k.real_kwh) },
          { t: 'Desviación', v: EN.pct(k.desviacion_pct), d: EN.kwh(k.desviacion_kwh) },
          { t: k.indicador_etiqueta, v: EN.num(k.indicador_valor, 2) },
        ],
      },
      {
        titulo: 'Avisos',
        filas: [
          { t: 'Simulación activa', v: d.simulacion, tono: 'ok' },
          { t: 'Estado de la desviación', v: TEXTO_TONO[tono], tono },
        ],
      },
    ]), d.fig_barras);
  });

  const resumenAcumulada = conDatos('comparativa/acumulada', null, (d) => {
    const k = d.kpis;
    const tono = EN.tonoDesviacion(k.desviacion_pct);
    return resumenConGrafico(EN.lista([
      {
        titulo: 'Indicadores',
        filas: [
          { t: 'Meses BMS', v: `${k.meses_bms}/12` },
          { t: 'Cobertura', v: `${EN.num(k.cobertura_pct, 0)} %` },
          { t: 'Desviación acumulada', v: EN.pct(k.desviacion_pct), d: EN.kwh(k.desviacion_kwh) },
          { t: 'Proyección anual', v: EN.kwh(k.proyeccion_anual_kwh) },
          { t: `${k.indicador_etiqueta} acumulado`, v: EN.num(k.indicador_valor, 2) },
        ],
      },
      {
        titulo: 'Avisos',
        filas: [
          { t: 'Simulación activa', v: d.simulacion, tono: 'ok' },
          { t: 'Estado de la desviación', v: TEXTO_TONO[tono], tono },
        ],
      },
    ]), d.fig_evolucion);
  });

  const graf = (ruta, clave) => conDatos(ruta, null, (d) => vista(null, EN.grafico(d[clave])));
  const tab = (ruta, clave, columnas) => conDatos(ruta, null, (d) => vista(null, EN.tabla(d[clave], { columnas })));

  /** Base comparable: filtro por categoría de edificio (chips) + ranking o tabla. */
  function baseComparable(modo) {
    return async (ctx) => {
      if (!ctx.codigo) return sinEdificio();
      const extra = { categorias: (EN.sel.categorias || []).join('|') };
      const d = await EN.datos(`/api/comparativa/base?${consulta(ctx, extra)}`);
      if (d.aviso) return EN.aviso(d.aviso, 'warn');
      const chips = h('div', { class: 'chips' }, d.categorias.map((c) => h('span', {
        class: 'chip' + (d.seleccion.includes(c) ? ' on' : ''), text: c, role: 'button', tabindex: '0',
        onclick: () => {
          const actual = new Set(d.seleccion);
          if (actual.has(c)) actual.delete(c); else actual.add(c);
          EN.sel.categorias = actual.size ? [...actual] : null;
          EN.refrescar();
        },
      })));
      const cuerpo = modo === 'ranking' ? EN.grafico(d.figura) : EN.tabla(d.tabla);
      return vista(h('div', { class: 'barra-herramientas' }, h('span', { text: 'Filtrar por categoría:' }), chips), cuerpo);
    };
  }

  const comparativa = {
    id: 'comparativa', icono: 'scale', titulo: 'Comparativa',
    subs: [
      { id: 'mes-resumen', grupo: 'Mensual', titulo: 'Resumen', render: resumenMes },
      { id: 'mes-barras', grupo: 'Mensual', titulo: 'Simulado frente a real', render: graf('comparativa/mes', 'fig_barras') },
      { id: 'mes-desviacion', grupo: 'Mensual', titulo: 'Desviación por categoría', render: graf('comparativa/mes', 'fig_desviacion') },
      { id: 'mes-pareto', grupo: 'Mensual', titulo: 'Pareto de desviaciones', render: graf('comparativa/mes', 'fig_pareto') },
      { id: 'mes-tabla', grupo: 'Mensual', titulo: 'Detalle', render: tab('comparativa/mes', 'tabla') },
      { id: 'acum-resumen', grupo: 'Acumulada', titulo: 'Resumen', render: resumenAcumulada },
      { id: 'acum-evolucion', grupo: 'Acumulada', titulo: 'Evolución mensual', render: graf('comparativa/acumulada', 'fig_evolucion') },
      { id: 'acum-barras', grupo: 'Acumulada', titulo: 'Categorías acumuladas', render: graf('comparativa/acumulada', 'fig_barras') },
      { id: 'acum-desviacion', grupo: 'Acumulada', titulo: 'Desviación acumulada', render: graf('comparativa/acumulada', 'fig_desviacion') },
      { id: 'acum-meses', grupo: 'Acumulada', titulo: 'Resumen mensual', render: tab('comparativa/acumulada', 'tabla_meses') },
      { id: 'acum-categorias', grupo: 'Acumulada', titulo: 'Detalle por categoría', render: tab('comparativa/acumulada', 'tabla_categorias') },
      { id: 'base-ranking', grupo: 'Base comparable', titulo: 'Ranking de edificios', render: baseComparable('ranking') },
      { id: 'base-tabla', grupo: 'Base comparable', titulo: 'Tabla', render: baseComparable('tabla') },
    ],
  };

  // ---------------------------------------------------------------- Informe

  const informe = {
    id: 'informe', icono: 'file-text', titulo: 'Informe mensual',
    subs: [
      {
        id: 'resumen', titulo: 'Resumen',
        render: conDatos('informe', null, (d) => {
          const k = d.kpis;
          const n = d.alertas.length;
          return vista(null, EN.lista([
            {
              titulo: 'Indicadores',
              filas: [
                { t: 'Simulado', v: EN.kwh(k.simulado_kwh) },
                { t: 'Real BMS', v: EN.kwh(k.real_kwh) },
                { t: 'Desviación', v: EN.pct(k.desviacion_pct), d: EN.kwh(k.desviacion_kwh) },
                { t: `${k.indicador_etiqueta} del mes`, v: EN.num(k.indicador_valor, 2) },
              ],
            },
            {
              titulo: 'Avisos',
              filas: [{
                t: 'Alertas del mes',
                v: n === 0 ? 'No se detectan desviaciones superiores al 10 %' : `${n} categorías superan el 10 % de desviación (ver Alertas)`,
                tono: n === 0 ? 'ok' : 'warn',
              }],
            },
          ]), true);
        }),
      },
      {
        id: 'alertas', titulo: 'Alertas',
        render: conDatos('informe', null, (d) => (d.alertas.length
          ? vista(null, EN.tabla(d.alertas))
          : vista(null, EN.aviso('No se detectan desviaciones relevantes superiores al 10 %.')))),
      },
      { id: 'comparativa', titulo: 'Comparativa', render: tab('informe', 'tabla') },
      {
        id: 'observaciones', titulo: 'Observaciones',
        render: conDatos('informe', null, (d) => vista(null, h('div', { class: 'observaciones', text: d.observaciones }), true)),
      },
      {
        id: 'texto', titulo: 'Texto del informe',
        render: conDatos('informe', null, (d) => {
          const area = h('textarea', { class: 'texto-informe', readOnly: true });
          area.value = d.texto.trim();
          const descargar = () => {
            const enlace = h('a', { href: URL.createObjectURL(new Blob([d.texto], { type: 'text/plain;charset=utf-8' })), download: d.archivo });
            document.body.appendChild(enlace);
            enlace.click();
            enlace.remove();
            URL.revokeObjectURL(enlace.href);
          };
          const copiar = async () => {
            try { await navigator.clipboard.writeText(d.texto); EN.toast('Texto copiado.'); } catch (e) { area.select(); EN.toast('Selecciona y copia con Ctrl+C.'); }
          };
          return vista(
            h('div', { class: 'barra-herramientas' },
              h('button', { class: 'btn-primary', text: 'Descargar TXT', onclick: descargar }),
              h('button', { class: 'btn-secondary', text: 'Copiar', onclick: copiar })),
            area);
        }),
      },
    ],
  };

  // ------------------------------------------------------- Costes y CO2

  /** Filas editables de parámetros (precios o factores): se guardan y recalculan al cambiar. */
  function filasParametros(definiciones) {
    return definiciones.map((p) => {
      const c = EN.campo({ name: p.clave, t: p.t, tipo: 'number', valor: E.params[p.clave], paso: 0.01, min: 0 });
      c.input.addEventListener('change', () => {
        const v = Number(c.input.value);
        if (Number.isFinite(v) && v >= 0) { E.params[p.clave] = v; EN.guardar(); EN.refrescar(); } else c.input.value = E.params[p.clave];
      });
      return fila(c);
    });
  }

  /** Escenario de "cuenta" anual (costes, CO2): parámetros + resumen y vistas mensual/categoría. */
  function escenarioCuenta(o) {
    const extra = () => Object.fromEntries(o.parametros.map((p) => [p.consulta, E.params[p.clave]]));
    const datos = (construir) => conDatos(o.ruta, extra, construir);
    return {
      id: o.id, icono: o.icono, titulo: o.titulo,
      subs: [
        {
          id: 'resumen', titulo: 'Parámetros y resumen',
          render: datos((d) => resumenConGrafico(EN.lista([
            { titulo: 'Parámetros', filas: filasParametros(o.parametros) },
            { titulo: 'Resumen del año', filas: o.filas(d.kpis) },
          ]), d.fig_mes)),
        },
        { id: 'mes-grafico', grupo: 'Mensual', titulo: `${o.nombre} mensual`, render: datos((d) => vista(null, EN.grafico(d.fig_mes))) },
        { id: 'mes-tabla', grupo: 'Mensual', titulo: 'Tabla mensual', render: datos((d) => vista(null, EN.tabla(d.tabla_mes))) },
        { id: 'cat-grafico', grupo: 'Por categoría', titulo: `${o.nombre} por categoría`, render: datos((d) => vista(null, EN.grafico(d.fig_categoria))) },
        { id: 'cat-tabla', grupo: 'Por categoría', titulo: 'Tabla por categoría', render: datos((d) => vista(null, EN.tabla(d.tabla_categoria))) },
      ],
    };
  }

  const costes = escenarioCuenta({
    id: 'costes', icono: 'euro', titulo: 'Costes', nombre: 'Coste', ruta: 'costes',
    parametros: [
      { clave: 'precioElec', consulta: 'precio_elec', t: 'Precio electricidad (€/kWh)' },
      { clave: 'precioGas', consulta: 'precio_gas', t: 'Precio gas natural (€/kWh)' },
    ],
    filas: (k) => [
      { t: 'Meses BMS', v: `${k.meses_bms}/12` },
      { t: 'Coste acumulado', v: `${EN.num(k.coste_total_eur, 0)} €` },
      { t: 'Coste por m²', v: `${EN.num(k.coste_m2, 2)} €/m²` },
      { t: 'Proyección anual', v: `${EN.num(k.proyeccion_anual_eur, 0)} €` },
    ],
  });

  const co2 = escenarioCuenta({
    id: 'co2', icono: 'leaf', titulo: 'CO₂', nombre: 'CO₂', ruta: 'co2',
    parametros: [
      { clave: 'factorElec', consulta: 'factor_elec', t: 'Electricidad (kgCO₂/kWh)' },
      { clave: 'factorGas', consulta: 'factor_gas', t: 'Gas natural (kgCO₂/kWh)' },
    ],
    filas: (k) => [
      { t: 'Meses BMS', v: `${k.meses_bms}/12` },
      { t: 'CO₂ acumulado', v: `${EN.num(k.co2_acumulado_tn, 2)} tCO₂` },
      { t: 'Emisiones por m²', v: `${EN.num(k.co2_m2_kg, 2)} kgCO₂/m²` },
      { t: 'Proyección anual', v: `${EN.num(k.proyeccion_anual_tn, 2)} tCO₂` },
    ],
  });

  EN.ESCENARIOS = [panel, edificios, simulaciones, bms, comparativa, EN.ESC_ALERTAS]
    .concat(EN.esAdmin() ? [EN.ESC_CONSTRUCTOR] : [])
    .concat([informe, costes, co2]);
})();
