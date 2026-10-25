// Panel SmartEgg: p5.js + MQTT por WebSocket

// Configuración: editable aquí o por la URL
// Ejemplo: index.html?url=wss://mi-servidor/mqtt&user=web&pass=clave&node=incubadora-01
const Q = new URLSearchParams(location.search);
const CFG = {
  url:    Q.get('url')  || 'ws://localhost:9001',   // en la nube: ws://IP_PUBLICA:PUERTO_WS
  user:   Q.get('user') || '',
  pass:   Q.get('pass') || '',
  prefix: Q.get('prefix') || 'smartegg',
  node:   Q.get('node') || 'incubadora-01'
};
const base = `${CFG.prefix}/${CFG.node}/`;

// Rangos ideales (los mismos de la incubadora)
const RANGO = { t: { min: 30, max: 45, lo: 37, hi: 38 }, h: { min: 0, max: 100, lo: 50, hi: 65 } };

// Estado que se muestra
const S = {
  conn: false, t: null, h: null, cal: false, ven: false, rot: false,
  vis: null, ml: null, en: null,
  sys: { bloqueado: false, ciclo_activo: false, motivo: '' }
};
const $ = id => document.getElementById(id);
const num  = v => { v = Number(v); return Number.isFinite(v) ? v : null; };
const bool = v => v === true || v === 1 || ['1', 'on', 'true', 'ON'].includes(v);

// Mensajes que llegan del broker
function onMsg(topic, buf) {
  const raw = buf.toString();
  let p; try { p = JSON.parse(raw); } catch { p = raw; }
  const obj = (p && typeof p === 'object') ? p : {};

  switch (topic.slice(base.length)) {
    case 'sensores/lectura': {
      const t = num(obj.temperatura ?? obj.temp), h = num(obj.humedad ?? obj.hum);
      if (t !== null) S.t = t;
      if (h !== null) S.h = h;
      break;
    }
    case 'sensores/temperatura': S.t = num(obj.valor ?? p) ?? S.t; break;
    case 'sensores/humedad':     S.h = num(obj.valor ?? p) ?? S.h; break;
    case 'actuadores/estado': {
      const a = obj.actuadores || obj;
      S.cal = bool(a.calefaccion); S.ven = bool(a.ventilacion); S.rot = bool(a.rotacion);
      break;
    }
    case 'vision/resultado': S.vis = { clase: obj.clase, conf: num(obj.confianza) }; break;
    case 'ml/anomalia':      S.ml  = { anom: bool(obj.anomalia ?? obj.es_anomalia) }; break;
    case 'energia/consumo':  S.en  = obj; break;
    case 'sistema/estado': {
      Object.assign(S.sys, obj);
      S.sys.bloqueado = bool(obj.bloqueado) || obj.estado === 'bloqueado';
      S.sys.ciclo_activo = bool(obj.ciclo_activo);
      const m = obj.motivo;
      S.sys.motivo = m && typeof m === 'object'
        ? (m.descripcion || m.mensaje || m.tipo || JSON.stringify(m)) : (m || '');
      break;
    }
    case 'alarmas/critica':
      $('alarma').textContent = 'Última alarma: ' + (obj.mensaje || obj.tipo || raw) +
        ' (' + new Date().toLocaleTimeString('es-GT') + ')';
      break;
  }
  render();
}

// Conexión MQTT sobre WebSocket
const cli = mqtt.connect(CFG.url, {
  username: CFG.user || undefined,
  password: CFG.pass || undefined,
  reconnectPeriod: 3000,
  clientId: 'smartegg-p5-' + Math.random().toString(16).slice(2, 8)
});
cli.on('connect', () => { S.conn = true; cli.subscribe(base + '#', { qos: 1 }); render(); });
cli.on('close',   () => { S.conn = false; render(); });
cli.on('error',   e  => console.error('MQTT:', e.message));
cli.on('message', onMsg);

function pub(sufijo, obj) {
  if (!S.conn) return;
  cli.publish(base + sufijo,
    JSON.stringify({ ...obj, node_id: CFG.node, timestamp: new Date().toISOString() }),
    { qos: 1 });
}

// Controles: todo se envía por MQTT, nunca por API
document.querySelectorAll('[data-sys]').forEach(b =>
  b.onclick = () => pub('sistema/cmd', { accion: b.dataset.sys }));
document.querySelectorAll('[data-act]').forEach(b => b.onclick = () => {
  const enc = { calefaccion: S.cal, ventilacion: S.ven, rotacion: S.rot }[b.dataset.act];
  pub('actuadores/cmd', { actuador: b.dataset.act, accion: enc ? 'off' : 'on' });
});
$('unlock').onclick = () => pub('sistema/cmd', { accion: 'desbloquear', autorizado: true, rol: 'admin' });

// Pintar las tarjetas HTML
function medida(idValor, idMarca, v, r, unidad) {
  const el = $(idValor);
  el.textContent = v === null ? '—' : v.toFixed(1) + ' ' + unidad;
  const ok = v !== null && v >= r.lo && v <= r.hi;
  el.className = 'value' + (v === null ? '' : ok ? ' ok' : ' bad');
  if (v !== null) $(idMarca).style.left = 'calc(' + Math.min(100, Math.max(0, (v - r.min) / (r.max - r.min) * 100)) + '% - 2px)';
}
function chip(id, texto, tipo) { const e = $(id); e.className = 'badge ' + tipo; e.innerHTML = '<i></i>' + texto; }

function render() {
  // conexión
  $('badge').className = 'badge ' + (S.conn ? 'success' : 'neutral');
  $('badgeTxt').textContent = S.conn ? 'Conectado al broker' : 'Sin conexión';
  // mediciones
  medida('vT', 'mT', S.t, RANGO.t, '°C');
  medida('vH', 'mH', S.h, RANGO.h, '%');
  const w = S.en && num(S.en.potencia_actual_w), kwh = S.en && num(S.en.energia_ciclo_kwh);
  $('vW').textContent = w === null || w === undefined ? '—' : w.toFixed(1) + ' W';
  $('vKwh').textContent = 'Energía del ciclo: ' + (kwh === null || kwh === undefined ? '—' : kwh.toFixed(4) + ' kWh');
  // estados
  const v = S.vis;
  if (!v || !v.clase) chip('chVis', 'Visión: sin datos', 'neutral');
  else {
    const pct = v.conf === null ? '' : ' ' + Math.round(v.conf <= 1 ? v.conf * 100 : v.conf) + '%';
    chip('chVis', 'Visión: ' + v.clase.replace('_', ' ') + pct,
      v.clase === 'objeto_extrano' ? 'danger' : v.clase === 'huevo' ? 'success' : 'info');
  }
  chip('chMl', S.ml ? (S.ml.anom ? 'Modelo ML: anomalía' : 'Modelo ML: normal') : 'Modelo ML: sin datos',
    S.ml ? (S.ml.anom ? 'danger' : 'success') : 'neutral');
  chip('chCiclo', S.sys.ciclo_activo ? 'Ciclo en marcha' : 'Ciclo detenido', S.sys.ciclo_activo ? 'success' : 'neutral');
  // controles y bloqueo
  document.querySelectorAll('.ctl').forEach(b => b.disabled = !S.conn || S.sys.bloqueado);
  document.querySelectorAll('[data-act]').forEach(b =>
    b.classList.toggle('on', { calefaccion: S.cal, ventilacion: S.ven, rotacion: S.rot }[b.dataset.act]));
  $('unlock').disabled = !S.conn;
  $('lock').classList.toggle('show', S.sys.bloqueado);
  $('motivo').textContent = S.sys.motivo || '';
}

// Zonas ideales dibujadas en los medidores
function bandas() {
  [['bT', RANGO.t], ['bH', RANGO.h]].forEach(([id, r]) => {
    const a = (r.lo - r.min) / (r.max - r.min) * 100, b = (r.hi - r.min) / (r.max - r.min) * 100;
    $(id).style.left = a + '%'; $(id).style.width = (b - a) + '%';
  });
}
$('nodo').textContent = CFG.node;
bandas(); render();

// Visualización p5.js (solo la incubadora; lo demás es HTML)
// Vista superior de la bandeja. En cada volteo pasa al otro lado (centro ±45°) a la velocidad
// del servo y se queda ahí, como TareaServo en IoT/main/actuators.cpp; con el bloqueo vuelve al centro.
let giro = 0, lado = 1, rotAntes = false;
const PASO_SERVO = Math.PI / 180 / 15;   // el servo avanza 1° cada 15 ms

function setup() { createCanvas(10, 10).parent('cv'); fit(); textFont('Plus Jakarta Sans'); }
function windowResized() { fit(); }
function fit() { const w = $('cv').clientWidth; resizeCanvas(w, Math.min(440, Math.max(300, w * 0.8))); }

// Relleno con degradado radial (para el volumen de huevos y cámara)
function radial(x, y, r, paradas) {
  const g = drawingContext.createRadialGradient(x, y, 0, x, y, r);
  paradas.forEach(([p, c]) => g.addColorStop(p, c));
  drawingContext.fillStyle = g;
}

function draw() {
  clear();
  const w = width, h = height;
  const cx = w / 2, cy = h / 2 + 12, R = Math.min(w, h) * 0.32;
  const t = S.t, caliente = t !== null && t > RANGO.t.hi, fria = t !== null && t < RANGO.t.lo;
  const tono = caliente ? '255,107,107' : fria ? '94,200,255' : '61,220,151';

  // Volteo
  if (S.rot && !rotAntes) lado *= -1;
  rotAntes = S.rot;
  const objetivo = S.sys.bloqueado ? 0 : QUARTER_PI * lado;
  giro += constrain(objetivo - giro, -PASO_SERVO * deltaTime, PASO_SERVO * deltaTime);

  // Cámara: halo con el color de la temperatura; la calefacción lo hace latir en ámbar
  noStroke();
  radial(cx, cy, R * 1.5, [[0, `rgba(${tono},0.28)`], [0.7, `rgba(${tono},0.10)`], [1, `rgba(${tono},0)`]]);
  circle(cx, cy, R * 3);
  if (S.cal) {
    const p = sin(frameCount * 0.08) * 0.5 + 0.5;
    noFill(); stroke(245, 184, 74, 60 + p * 120); strokeWeight(3 + p * 3);
    circle(cx, cy, R * 2.55 + p * 10);
  }

  // Escala del servo: −45°, 0°, +45° y aguja con la posición actual
  noFill(); stroke(255, 255, 255, 40); strokeWeight(2);
  arc(cx, cy, R * 2.7, R * 2.7, -HALF_PI - QUARTER_PI, -HALF_PI + QUARTER_PI);
  textAlign(CENTER, CENTER); textSize(11); textStyle(NORMAL);
  [-1, 0, 1].forEach(k => {
    const a = -HALF_PI + k * QUARTER_PI;
    stroke(255, 255, 255, 70); line(cx + cos(a) * R * 1.3, cy + sin(a) * R * 1.3, cx + cos(a) * R * 1.4, cy + sin(a) * R * 1.4);
    noStroke(); fill(124, 132, 163);
    text((k > 0 ? '+' : k < 0 ? '−' : '') + abs(k * 45) + '°', cx + cos(a) * R * 1.55, cy + sin(a) * R * 1.55);
  });
  const ag = -HALF_PI + giro;
  noStroke(); fill(S.rot ? '#8aa2ff' : '#b4bad0');
  push(); translate(cx + cos(ag) * R * 1.35, cy + sin(ag) * R * 1.35); rotate(ag + HALF_PI); triangle(-6, -7, 6, -7, 0, 4); pop();

  // Bandeja (gira completa con el servo)
  push();
  translate(cx, cy);
  rotate(giro);
  fill(93, 106, 160);
  for (let k = 0; k < 48; k++) {   // engrane del borde
    push(); rotate(k * TWO_PI / 48); rect(-R * 0.035, -R * 1.18, R * 0.07, R * 0.1, 2); pop();
  }
  radial(-R * 0.3, -R * 0.3, R * 1.4, [[0, '#4a5585'], [1, '#2a3358']]);
  stroke(255, 255, 255, 30); strokeWeight(1.5);
  circle(0, 0, R * 2.3);

  const clase = S.vis && S.vis.clase;
  for (let i = 0; i < 6; i++) {
    const a = i * TWO_PI / 6 - HALF_PI, x = cos(a) * R * 0.72, y = sin(a) * R * 0.72;
    noStroke(); fill(20, 26, 50); circle(x, y, R * 0.5);   // hueco
    push();
    translate(x, y);
    rotate(a + HALF_PI);
    if (clase === 'vacio') {
      noFill(); stroke(124, 132, 163); strokeWeight(2);
      drawingContext.setLineDash([5, 5]); ellipse(0, 0, R * 0.34, R * 0.44); drawingContext.setLineDash([]);
    } else {
      fill(0, 0, 0, 60); ellipse(R * 0.03, R * 0.04, R * 0.34, R * 0.44);   // sombra
      const [c1, c2] = clase === 'objeto_extrano' ? ['#ffb3b3', '#d94848'] : ['#fffaf0', '#e4d3b0'];
      radial(-R * 0.06, -R * 0.09, R * 0.28, [[0, c1], [1, c2]]);
      ellipse(0, 0, R * 0.34, R * 0.44);
    }
    pop();
  }
  // Eje central con marca de orientación
  noStroke(); radial(0, 0, R * 0.16, [[0, '#8aa2ff'], [1, '#3a55e6']]); circle(0, 0, R * 0.28);
  stroke(255); strokeWeight(2); line(0, -R * 0.05, 0, -R * 0.12);
  pop();

  // Ventilador: carcasa y aspas que giran cuando está encendido
  push();
  const fx = cx + R * 1.3, fy = cy + R * 1.0, fr = Math.max(18, R * 0.2);
  translate(fx, fy);
  noFill(); stroke(S.ven ? 'rgba(61,220,151,0.5)' : 'rgba(124,132,163,0.4)'); strokeWeight(2);
  circle(0, 0, fr * 2.3);
  rotate(S.ven ? frameCount * 0.3 : 0);
  noStroke(); fill(S.ven ? '#3ddc97' : '#7c84a3');
  for (let k = 0; k < 3; k++) { rotate(TWO_PI / 3); ellipse(0, -fr * 0.55, fr * 0.45, fr * 1.05); }
  fill(18, 25, 51); circle(0, 0, fr * 0.35);
  pop();

  // Bloqueo: la escena parpadea en rojo
  if (S.sys.bloqueado) {
    noStroke(); fill(255, 107, 107, 40 + abs(sin(frameCount * 0.1)) * 70); rect(0, 0, w, h, 18);
    fill(255); textAlign(CENTER, CENTER); textStyle(BOLD); textSize(Math.max(22, w * 0.06));
    text('SISTEMA BLOQUEADO', w / 2, h / 2);
  }
}
