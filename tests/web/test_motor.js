const assert = require('assert');
const M = require('../../web/js/tabla_motor.js');

// Datos de prueba: 3 categorías × 3 meses con BMS (1-3) y una categoría que el BMS trae sin simular
const filas = [];
const sim = { Heating: [100, 100, 100], Cooling: [50, 50, 50], Fans: [0, 0, 0] };
const real = { Heating: [90, 110, 130], Cooling: [60, 50, 40], Fans: [10, 10, 10] };
Object.keys(sim).forEach((c) => [1, 2, 3].forEach((m) => filas.push({ mes: m, categoria: c, simulado_kwh: sim[c][m - 1], real_kwh: real[c][m - 1], electricidad_kwh: real[c][m - 1], gas_kwh: 0 })));
// meses 4..12 sin BMS
Object.keys(sim).forEach((c) => { for (let m = 4; m <= 12; m++) filas.push({ mes: m, categoria: c, simulado_kwh: 100, real_kwh: null, electricidad_kwh: null, gas_kwh: null }); });
const datos = { filas, categorias: ['Cooling', 'Fans', 'Heating'], meses_con_bms: [1, 2, 3] };

// --- bases
const largo = M.crearBase(datos, 'largo');
assert.strictEqual(largo.filas.length, 9, 'largo: solo meses con BMS');
assert.deepStrictEqual(largo.filas[0].v.categoria, 'Cooling');
assert.strictEqual(largo.filas[0].v.desviacion_kwh, 10);
assert.strictEqual(largo.filas[0].v.desviacion_pct, 20);
const fans = largo.filas.find((f) => f.v.categoria === 'Fans');
assert.strictEqual(fans.v.desviacion_pct, null, 'sin simulado no hay %');

const ancho = M.crearBase(datos, 'ancho_real');
assert.strictEqual(ancho.columnas.length, 14);
assert.strictEqual(ancho.filas.length, 3);
const heating = ancho.filas.find((f) => f.v.categoria === 'Heating');
assert.strictEqual(heating.v.mes_1, 90); assert.strictEqual(heating.v.mes_4, null); assert.strictEqual(heating.v.total, 330);
const pct = M.crearBase(datos, 'ancho_desv_pct');
assert.ok(Math.abs(pct.filas.find((f) => f.v.categoria === 'Heating').v.total - 10) < 1e-9, 'total % = (330-300)/300');
assert.strictEqual(M.crearBase(datos, 'no_existe').id, 'largo');

// --- formulas
assert.strictEqual(M.evaluarFormula('(C1+C2)*C3', { C1: 1, C2: 2, C3: 4 }), 12);
assert.strictEqual(M.evaluarFormula('-C1 + 10 / 4', { C1: 1 }), 1.5);
assert.strictEqual(M.evaluarFormula('IF(C1>10, "Alto", "Bajo")', { C1: 11 }), 'Alto');
assert.strictEqual(M.evaluarFormula('IF(C1>10, "Alto", "Bajo")', { C1: null }), 'Bajo');
assert.strictEqual(M.evaluarFormula('C1 > 5', { C1: 6 }), true);
assert.strictEqual(M.evaluarFormula('AND(C1>1, OR(C2<0, NOT(C3=2)))', { C1: 2, C2: 5, C3: 3 }), true);
assert.strictEqual(M.evaluarFormula('ROUND(C1/3, 2)', { C1: 10 }), 3.33);
assert.strictEqual(M.evaluarFormula('ABS(C1)', { C1: -4 }), 4);
assert.strictEqual(M.evaluarFormula('MAX(C1, C2, 3)', { C1: 1, C2: null }), 3);
assert.strictEqual(M.evaluarFormula('C1/C2', { C1: 1, C2: 0 }), null, 'división por cero');
assert.strictEqual(M.evaluarFormula('C1+C2', { C1: 1, C2: null }), null, 'vacío contagia');
assert.strictEqual(M.evaluarFormula('"a" + C1', { C1: 'b' }), 'ab');
['', '(C1', 'C1 +', 'FOO(1)', 'C1 $ 2', '"sin cerrar'].forEach((f) => assert.throws(() => M.parsear(f), Error, f));
// Nada de ejecutar código: una "fórmula" maliciosa solo puede fallar al analizarse
assert.throws(() => M.parsear('constructor.constructor("return 1")()'));
assert.throws(() => M.parsear('process.exit()'));

// --- pasos
const base = M.crearBase(datos, 'largo');
let t = M.aplicarPasos(base, []);
assert.strictEqual(t.filas.length, 9);
t = M.aplicarPasos(base, [{ p: 'alternar_columna', id: 'gas_kwh' }, { p: 'alternar_columna', id: 'electricidad_kwh' }]);
assert.deepStrictEqual(t.columnas.filter((c) => c.oculta).map((c) => c.id), ['electricidad_kwh', 'gas_kwh']);
t = M.aplicarPasos(base, [{ p: 'alternar_columna', id: 'gas_kwh' }, { p: 'mostrar_todas' }]);
assert.ok(t.columnas.every((c) => !c.oculta));
t = M.aplicarPasos(base, [{ p: 'seleccionar_columnas', conservar: ['categoria', 'mes', 'real_kwh'] }]);
assert.deepStrictEqual(t.columnas.filter((c) => !c.oculta).map((c) => c.id), ['categoria', 'mes', 'real_kwh']);
t = M.aplicarPasos(base, [{ p: 'seleccionar_filas', conservar: ['f0', 'f1'] }]);
assert.strictEqual(t.filas.filter((f) => !f.oculta).length, 2);
t = M.aplicarPasos(base, [{ p: 'colorear_filas', filas: ['f2'], color: '#ff0000' }]);
assert.strictEqual(t.filas[2].color, '#ff0000'); assert.strictEqual(t.filas[0].color, null);
t = M.aplicarPasos(base, [{ p: 'mover_columna', id: 'real_kwh', despues: 'categoria' }]);
assert.deepStrictEqual(t.columnas.slice(0, 3).map((c) => c.id), ['categoria', 'real_kwh', 'mes']);
t = M.aplicarPasos(base, [{ p: 'renombrar', id: 'real_kwh', titulo: 'Real' }]);
assert.strictEqual(t.columnas.find((c) => c.id === 'real_kwh').titulo, 'Real');
t = M.aplicarPasos(base, [{ p: 'totales', ids: ['simulado_kwh', 'real_kwh'] }]);
const tot = t.filas[t.filas.length - 1];
assert.ok(tot.total && tot.id === 'total'); assert.strictEqual(tot.v.categoria, 'Total'); assert.strictEqual(tot.v.real_kwh, 510); assert.strictEqual(tot.v.simulado_kwh, 450);
t = M.aplicarPasos(base, [{ p: 'seleccionar_filas', conservar: ['f0', 'f1', 'f2'] }, { p: 'totales', ids: ['real_kwh'] }]);
assert.strictEqual(t.filas[t.filas.length - 1].v.real_kwh, 60 + 50 + 40, 'el total solo suma las filas visibles');
t = M.aplicarPasos(base, [{ p: 'formula', id: 'm1', titulo: 'Ratio', formula: 'C1/C2', alias: { C1: 'real_kwh', C2: 'simulado_kwh' } }]);
assert.strictEqual(t.columnas[t.columnas.length - 1].id, 'm1');
assert.strictEqual(t.filas[0].v.m1, 60 / 50);
assert.strictEqual(t.filas.find((f) => f.v.categoria === 'Fans').v.m1, null);
// una fórmula puede usar otra columna calculada
t = M.aplicarPasos(base, [
  { p: 'formula', id: 'm1', titulo: 'Doble', formula: 'C1*2', alias: { C1: 'real_kwh' } },
  { p: 'formula', id: 'm2', titulo: 'Más 1', formula: 'C1+1', alias: { C1: 'm1' } }]);
assert.strictEqual(t.filas[0].v.m2, 121);
t = M.aplicarPasos(base, [{ p: 'sustituir', ids: ['mes'], pares: [['Ene', 'Enero'], ['Feb', '']] }]);
assert.strictEqual(t.filas[0].v.mes, 'Enero'); assert.strictEqual(t.filas[1].v.mes, '');
t = M.aplicarPasos(base, [{ p: 'ordenar', id: 'real_kwh', dir: 'desc' }, { p: 'totales', ids: ['real_kwh'] }]);
assert.strictEqual(t.filas[0].v.real_kwh, 130); assert.strictEqual(t.filas[t.filas.length - 1].id, 'total');
t = M.aplicarPasos(base, [{ p: 'ordenar', id: 'desviacion_pct', dir: 'asc' }]);
assert.strictEqual(t.filas[t.filas.length - 1].v.desviacion_pct, null, 'los vacíos van al final');

// pasos que fallan no rompen el resto
t = M.aplicarPasos(base, [{ p: 'alternar_columna', id: 'no_existe' }, { p: 'inventado' }, { p: 'renombrar', id: 'mes', titulo: 'M' },
  { p: 'formula', id: 'm1', titulo: 'x', formula: 'C9+1', alias: { C1: 'mes' } }]);
assert.strictEqual(t.avisos.length, 3); assert.strictEqual(t.columnas.find((c) => c.id === 'mes').titulo, 'M');
// reproducibilidad: misma base + mismos pasos = misma tabla (deshacer = quitar el último paso)
const pasos = [{ p: 'alternar_columna', id: 'gas_kwh' }, { p: 'ordenar', id: 'real_kwh', dir: 'asc' }, { p: 'totales', ids: ['real_kwh'] }];
assert.deepStrictEqual(M.aplicarPasos(base, pasos), M.aplicarPasos(base, JSON.parse(JSON.stringify(pasos))));
assert.ok(!M.aplicarPasos(base, pasos.slice(0, 2)).filas.some((f) => f.total), 'deshacer quita los totales');
assert.strictEqual(M.idColumnaNueva([]), 'm1'); assert.strictEqual(M.idColumnaNueva([{ p: 'formula', id: 'm1' }, { p: 'formula', id: 'm4' }]), 'm5');
assert.ok(M.describirPaso({ p: 'formula', id: 'm1', titulo: 'R', formula: 'C1/C2', alias: { C1: 'real_kwh', C2: 'simulado_kwh' } }, base.columnas).includes('«Real BMS (kWh)»'));
assert.ok(M.describirPaso({ p: 'ordenar', id: 'mes', dir: 'desc' }, base.columnas).includes('mayor a menor'));

// --- gráficos
let g = M.construirGrafico(M.aplicarPasos(base, []), { tipo: 'barras', orient: 'columnas', ys: ['simulado_kwh', 'real_kwh'] });
assert.strictEqual(g.data.length, 2); assert.strictEqual(g.data[0].x.length, 9); assert.strictEqual(g.data[0].x[0], 'Cooling · Ene');
assert.strictEqual(g.data[0].type, 'bar'); assert.strictEqual(g.layout.barmode, 'group');
g = M.construirGrafico(M.aplicarPasos(base, [{ p: 'totales', ids: ['real_kwh'] }]), { tipo: 'apiladas', orient: 'columnas', x: 'categoria', ys: ['real_kwh'] });
assert.strictEqual(g.data[0].x.length, 9, 'la fila de totales no se dibuja'); assert.strictEqual(g.layout.barmode, 'stack');
g = M.construirGrafico(M.aplicarPasos(base, [{ p: 'seleccionar_filas', conservar: ['f0', 'f1'] }]), { tipo: 'lineas', orient: 'columnas', ys: ['real_kwh'] });
assert.strictEqual(g.data[0].y.length, 2, 'solo las filas visibles'); assert.strictEqual(g.data[0].type, 'scatter');
const a = M.aplicarPasos(ancho, []);
g = M.construirGrafico(a, { tipo: 'lineas', orient: 'filas', ys: ['mes_1', 'mes_2', 'mes_3'] });
assert.strictEqual(g.data.length, 3, 'una serie por fila'); assert.deepStrictEqual(g.data[0].x, ['Ene', 'Feb', 'Mar']); assert.strictEqual(g.data[0].name, 'Cooling');
g = M.construirGrafico(a, { tipo: 'area', orient: 'columnas', x: 'categoria', ys: ['total'] });
assert.strictEqual(g.data[0].fill, 'tozeroy');
assert.strictEqual(M.construirGrafico(a, { tipo: 'barras', ys: [] }), null);
assert.strictEqual(M.construirGrafico(a, { tipo: 'barras', ys: ['no_existe'] }), null);
assert.strictEqual(M.construirGrafico(M.aplicarPasos(base, [{ p: 'seleccionar_filas', conservar: ['nada'] }]), { tipo: 'barras', ys: ['real_kwh'] }), null);

console.log('MOTOR OK');
