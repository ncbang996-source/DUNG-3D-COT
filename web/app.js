import * as THREE from 'three';
import { OrbitControls } from 'three/addons/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/CSS2DRenderer.js';

const DENSITY = 7850; // kg/m3
const VARIANTS = ['in+', 'in-', 'out+', 'out-'];
const VAR_TEXT = {
  face: { 'in+': 'Cánh vào trong, lưng phía trên', 'in-': 'Cánh vào trong, lưng phía dưới',
          'out+': 'Cánh ra ngoài, lưng phía trên', 'out-': 'Cánh ra ngoài, lưng phía dưới' },
  plan: { 'in+': 'Cánh chĩa xuống, lưng phía ngoài', 'in-': 'Cánh chĩa xuống, lưng phía trong',
          'out+': 'Cánh chĩa lên, lưng phía ngoài', 'out-': 'Cánh chĩa lên, lưng phía trong' },
};
const PALETTE = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2',
  '#7f7f7f', '#bcbd22', '#17becf', '#393b79', '#e7ba52'];
const TYPE_COL = { 'CĐ': '#a40000', 'C': '#e0393e', 'XĐ': '#0b56b5', 'X': '#4aa3ff', 'G': '#8a8f98',
  'XAD': '#139a43', 'XAT': '#8cc63f', 'XCS': '#9b3fb5' };
const VAR_COL = { leg: '#a40000', 'in+': '#4aa3ff', 'in-': '#0b56b5', 'out+': '#ff9f1c', 'out-': '#c45a00' };

const $ = (id) => document.getElementById(id);
const view = $('view');

// ---------------------------------------------------------------- scene
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(window.devicePixelRatio);
view.appendChild(renderer.domElement);
const labelRenderer = new CSS2DRenderer();
labelRenderer.domElement.style.position = 'absolute';
labelRenderer.domElement.style.top = '0';
labelRenderer.domElement.style.pointerEvents = 'none';
view.appendChild(labelRenderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, 1, 0.05, 2000);
camera.up.set(0, 0, 1);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0x667080, 1.4));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(30, -40, 80);
scene.add(sun);

const dark = matchMedia('(prefers-color-scheme: dark)').matches;
scene.background = new THREE.Color(dark ? 0x101317 : 0xeef1f5);

const steelGroup = new THREE.Group();
const axisGroup = new THREE.Group();
const nodeLabelGroup = new THREE.Group();
const memLabelGroup = new THREE.Group();
scene.add(steelGroup, axisGroup, nodeLabelGroup, memLabelGroup);
axisGroup.visible = false;

function resize() {
  const w = view.clientWidth, h = view.clientHeight;
  renderer.setSize(w, h);
  labelRenderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(view);

// ---------------------------------------------------------------- data
let DATA, members, byId, sections;
const meshes = new Map();       // id -> mesh
const state = { colorBy: 'section', selected: null, fSection: '', fType: '', fGroup: '', ghost: true };

function frameOf(m, v) {
  if (m.rule === 'leg') return [m.e1, m.e2];
  return m.frames[v];
}

function buildGeometry(m) {
  const s = sections[m.section];
  const prof = s.profile;                           // mm, heel at origin
  const [g1, g2] = m.g;                              // mm
  const [e1, e2] = frameOf(m, m.variant).map((a) => new THREE.Vector3(...a));
  const p1 = new THREE.Vector3(...m.p1), p2 = new THREE.Vector3(...m.p2);
  const ring = (p) => prof.map(([a, b]) => p.clone()
    .addScaledVector(e1, (a - g1) / 1000).addScaledVector(e2, (b - g2) / 1000));
  const r0 = ring(p1), r1 = ring(p2);
  const pos = [];
  const push = (...vs) => vs.forEach((v) => pos.push(v.x, v.y, v.z));
  const n = prof.length;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    push(r0[i], r0[j], r1[j], r0[i], r1[j], r1[i]);
  }
  const tris = THREE.ShapeUtils.triangulateShape(prof.map(([a, b]) => new THREE.Vector2(a, b)), []);
  for (const [a, b, c] of tris) { push(r0[a], r0[c], r0[b]); push(r1[a], r1[b], r1[c]); }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.computeVertexNormals();
  return geo;
}

const matCache = new Map();
function material(color, ghost) {
  const key = color + (ghost ? 'g' : '');
  if (!matCache.has(key)) {
    matCache.set(key, new THREE.MeshStandardMaterial({
      color, metalness: 0.25, roughness: 0.6, side: THREE.DoubleSide,
      transparent: ghost, opacity: ghost ? 0.08 : 1, depthWrite: !ghost,
    }));
  }
  return matCache.get(key);
}
const selMat = new THREE.MeshStandardMaterial({ color: 0xffd400, emissive: 0x664400, side: THREE.DoubleSide });

let sectionColors = {};
function colorOf(m) {
  if (state.colorBy === 'type') return TYPE_COL[m.type] || '#888';
  if (state.colorBy === 'variant') return VAR_COL[m.rule === 'leg' ? 'leg' : m.variant];
  return sectionColors[m.section];
}

function passes(m) {
  return (!state.fSection || m.section === state.fSection) &&
    (!state.fType || m.type === state.fType) &&
    (!state.fGroup || String(m.group) === state.fGroup);
}

function refreshMaterials() {
  for (const m of members) {
    const mesh = meshes.get(m.id);
    const ok = passes(m);
    mesh.visible = ok || state.ghost;
    mesh.userData.pickable = ok;
    mesh.material = state.selected === m.id ? selMat : material(colorOf(m), !ok);
  }
  for (const o of memLabelGroup.children) o.visible = passes(byId.get(o.userData.id));
  renderLegend();
}

function renderLegend() {
  let entries;
  if (state.colorBy === 'type') entries = Object.entries(TYPE_COL);
  else if (state.colorBy === 'variant') entries = [['Thanh cánh', VAR_COL.leg], ...VARIANTS.map((v) => [v, VAR_COL[v]])];
  else entries = Object.entries(sectionColors);
  $('legend').innerHTML = entries.map(([k, c]) => `<div><span style="background:${c}"></span>${k}</div>`).join('');
}

function rebuildMember(m) {
  const mesh = meshes.get(m.id);
  mesh.geometry.dispose();
  mesh.geometry = buildGeometry(m);
}

// ---------------------------------------------------------------- labels
function makeLabel(text, cls, pos, id) {
  const el = document.createElement('div');
  el.className = 'lbl ' + cls;
  el.textContent = text;
  const o = new CSS2DObject(el);
  o.position.set(...pos);
  o.userData.id = id;
  return o;
}
function ensureLabels() {
  if (!nodeLabelGroup.children.length) {
    for (const n of DATA.nodes) nodeLabelGroup.add(makeLabel(n.label, 'node', n.xyz));
  }
  if (!memLabelGroup.children.length) {
    for (const m of members) {
      const mid = m.p1.map((v, i) => (v + m.p2[i]) / 2);
      memLabelGroup.add(makeLabel(m.id, 'mem', mid, m.id));
    }
  }
}

// ---------------------------------------------------------------- info panel
function fmt(x, d = 2) { return Number(x).toLocaleString('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d }); }
function massOf(m) { return m.A_cm2 * 1e-4 * m.length * DENSITY; }
function boltText(b) {
  const opts = Object.entries(b).filter(([, n]) => n != null);
  if (!opts.length) return '—';
  const min = Math.min(...opts.map(([, n]) => n));
  const best = opts.filter(([, n]) => n === min).map(([k]) => k);  // ưu tiên số lượng ít
  const head = best.length === 1 ? `${min} × ${best[0]}` : `${min} × ${best.join(' hoặc ')} <b>(bằng số lượng, chưa chọn)</b>`;
  return head + (opts.length > 1 ? ` <span class="muted">(${opts.map(([k, n]) => `${k}:${n}`).join(', ')})</span>` : '');
}

function showInfo(m) {
  $('info').hidden = !m;
  if (!m) return;
  const s = sections[m.section];
  $('iId').textContent = m.id;
  const rows = [
    ['Nhóm', m.group], ['Tiết diện', `${m.section} (JIS G3192 ${s.b}×${s.b}×${s.t})`], ['Type', m.type],
    ['Chiều dài', fmt(m.length, 3) + ' m'], ['A', fmt(m.A_cm2) + ' cm²'], ['Khối lượng', fmt(massOf(m), 1) + ' kg'],
    ['Bu lông', boltText(m.bolts)], ['Nút', `${m.node1 ?? '?'} → ${m.node2 ?? '?'}`],
    ['Quy tắc', m.rule === 'leg' ? 'Thanh cánh (lưng ra ngoài góc)' :
      m.rule === 'face' ? `Trên mặt cột ${m.face}` : 'Vách ngang / xà'],
    ['Hướng cánh', m.rule === 'leg' ? '—' : `${m.variant} · ${VAR_TEXT[m.rule][m.variant]}` +
      (m.variant !== m.auto_variant ? ' <b>(đã sửa)</b>' : '')],
  ];
  $('iTable').innerHTML = rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('');
  const sel = $('iVariant');
  sel.disabled = m.rule === 'leg';
  $('applyGroup').disabled = $('resetVar').disabled = m.rule === 'leg';
  sel.innerHTML = m.rule === 'leg' ? '<option>—</option>' :
    VARIANTS.map((v) => `<option value="${v}" ${v === m.variant ? 'selected' : ''}>${v} · ${VAR_TEXT[m.rule][v]}</option>`).join('');
  drawSection(m);
}

function drawSection(m) {
  const s = sections[m.section];
  const pad = 26, size = 220 - 2 * pad, k = size / s.b;
  const X = (a) => pad + a * k, Y = (b) => 220 - pad - b * k;
  const pts = s.profile.map(([a, b]) => `${X(a).toFixed(1)},${Y(b).toFixed(1)}`).join(' ');
  const [g1, g2] = m.g;
  const c = getComputedStyle(document.body).color;
  $('secSvg').innerHTML = `
    <polygon points="${pts}" fill="${colorOf(m)}" fill-opacity=".35" stroke="${c}" stroke-width="1.2"/>
    <line x1="${X(s.cx)}" y1="${Y(0) + 6}" x2="${X(s.cx)}" y2="${Y(s.b)}" stroke="${c}" stroke-dasharray="3 3" stroke-opacity=".4"/>
    <circle cx="${X(s.cx)}" cy="${Y(s.cy)}" r="3" fill="none" stroke="${c}"/>
    <circle cx="${X(g1)}" cy="${Y(g2)}" r="4.5" fill="#e02424"/>
    <text x="${X(s.b / 2)}" y="${Y(0) + 16}" text-anchor="middle" fill="${c}" font-size="11">b = ${s.b}</text>
    <text x="${X(s.b) - 2}" y="${Y(s.t) - 6}" text-anchor="end" fill="${c}" font-size="11">t = ${s.t}</text>
    <text x="${X(0) + 4}" y="${pad - 8}" fill="${c}" font-size="10">● đường tim DXF (đỏ) · ○ trọng tâm</text>`;
}

// ---------------------------------------------------------------- picking
const ray = new THREE.Raycaster();
const ptr = new THREE.Vector2();
let downAt = null;
renderer.domElement.addEventListener('pointerdown', (e) => { downAt = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', (e) => {
  if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 4) return;
  const r = renderer.domElement.getBoundingClientRect();
  ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ptr, camera);
  const hit = ray.intersectObjects([...meshes.values()].filter((x) => x.visible && x.userData.pickable))[0];
  select(hit ? hit.object.userData.id : null);
});

function select(id) {
  state.selected = id;
  refreshMaterials();
  showInfo(id ? byId.get(id) : null);
}

// ---------------------------------------------------------------- variant edit
function setVariant(m, v) {
  if (m.rule === 'leg' || m.variant === v) return;
  m.variant = v;
  rebuildMember(m);
}
$('iVariant').addEventListener('change', (e) => {
  const m = byId.get(state.selected); setVariant(m, e.target.value); showInfo(m); updateOvCount();
});
$('applyGroup').addEventListener('click', () => {
  const m = byId.get(state.selected);
  for (const o of members) if (o.group === m.group) setVariant(o, m.variant);
  showInfo(m); updateOvCount(); refreshMaterials();
});
$('resetVar').addEventListener('click', () => {
  const m = byId.get(state.selected); setVariant(m, m.auto_variant); showInfo(m); updateOvCount(); refreshMaterials();
});

function overrides() {
  const pre = new Set(DATA.report.orientation.overridden || []);
  return members.filter((m) => m.rule !== 'leg' && (m.variant !== m.auto_variant || pre.has(m.id)));
}
function updateOvCount() {
  const n = overrides().length;
  $('ovCount').textContent = n ? `${n} thanh có hướng ghi đè.` : 'Chưa có thanh nào ghi đè hướng.';
}
function download(name, text) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob(['﻿' + text], { type: 'text/csv;charset=utf-8' }));
  a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
$('btnOverride').addEventListener('click', () => {
  const rows = overrides().sort((a, b) => a.id - b.id).map((m) => `${m.id},${m.variant}`);
  download('orientation_override.csv', ['id,variant', ...rows].join('\n') + '\n');
});

// ---------------------------------------------------------------- stats
function stats() {
  const by = {};
  for (const m of members) {
    const s = (by[m.section] ??= { count: 0, len: 0, mass: 0, A: m.A_cm2, b: sections[m.section].b });
    s.count++; s.len += m.length; s.mass += massOf(m);
  }
  return Object.entries(by).sort((a, b) => a[1].b - b[1].b || a[0].localeCompare(b[0]));
}
$('btnStats').addEventListener('click', () => {
  const rows = stats();
  const tot = rows.reduce((a, [, s]) => ({ c: a.c + s.count, l: a.l + s.len, m: a.m + s.mass }), { c: 0, l: 0, m: 0 });
  $('statsBody').innerHTML = `<table><tr><th>Tiết diện</th><th>A (cm²)</th><th>Số thanh</th><th>Tổng dài (m)</th><th>Khối lượng (kg)</th></tr>` +
    rows.map(([k, s]) => `<tr><td>${k}</td><td>${fmt(s.A)}</td><td>${s.count}</td><td>${fmt(s.len)}</td><td>${fmt(s.mass, 1)}</td></tr>`).join('') +
    `<tr><th>Tổng</th><th></th><th>${tot.c}</th><th>${fmt(tot.l)}</th><th>${fmt(tot.m, 1)}</th></tr></table>
    <p class="muted">Chỉ tính thanh thép góc, chưa có bản mã và bu lông.</p>`;
  $('statsDlg').showModal();
});
$('btnStatsCsv').addEventListener('click', () => {
  const rows = stats().map(([k, s]) => [k, s.A, s.count, s.len.toFixed(3), s.mass.toFixed(2)].join(','));
  download('khoi_luong_theo_tiet_dien.csv', ['section,A_cm2,count,length_m,mass_kg', ...rows].join('\n') + '\n');
});

// ---------------------------------------------------------------- controls
$('colorBy').addEventListener('change', (e) => { state.colorBy = e.target.value; refreshMaterials(); if (state.selected) drawSection(byId.get(state.selected)); });
$('showSteel').addEventListener('change', (e) => { steelGroup.visible = e.target.checked; });
$('showAxis').addEventListener('change', (e) => { axisGroup.visible = e.target.checked; });
$('showNodes').addEventListener('change', (e) => { ensureLabels(); nodeLabelGroup.visible = e.target.checked; });
$('showMemNo').addEventListener('change', (e) => { ensureLabels(); memLabelGroup.visible = e.target.checked; refreshMaterials(); });
for (const [id, key] of [['fSection', 'fSection'], ['fType', 'fType'], ['fGroup', 'fGroup']]) {
  $(id).addEventListener('change', (e) => { state[key] = e.target.value; refreshMaterials(); });
}
$('fGhost').addEventListener('change', (e) => { state.ghost = e.target.checked; refreshMaterials(); });

// ---------------------------------------------------------------- load
async function load() {
  DATA = await (await fetch('data/scene.json')).json();
  members = DATA.members;
  sections = DATA.sections;
  byId = new Map(members.map((m) => [m.id, m]));
  const secNames = Object.keys(sections).sort((a, b) => sections[a].b - sections[b].b || a.localeCompare(b));
  secNames.forEach((s, i) => { sectionColors[s] = PALETTE[i % PALETTE.length]; });

  for (const m of members) {
    const mesh = new THREE.Mesh(buildGeometry(m), material(colorOf(m), false));
    mesh.userData = { id: m.id, pickable: true };
    meshes.set(m.id, mesh);
    steelGroup.add(mesh);
  }
  const lp = [];
  for (const m of members) lp.push(...m.p1, ...m.p2);
  const lg = new THREE.BufferGeometry();
  lg.setAttribute('position', new THREE.Float32BufferAttribute(lp, 3));
  axisGroup.add(new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: dark ? 0xffffff : 0x000000 })));
  nodeLabelGroup.visible = memLabelGroup.visible = false;

  const opt = (sel, vals) => vals.forEach((v) => sel.insertAdjacentHTML('beforeend', `<option value="${v}">${v}</option>`));
  opt($('fSection'), secNames);
  opt($('fType'), [...new Set(members.map((m) => m.type))].sort());
  opt($('fGroup'), [...new Set(members.map((m) => m.group))].sort((a, b) => a - b));

  const box = new THREE.Box3().setFromObject(steelGroup);
  const c = box.getCenter(new THREE.Vector3()), sz = box.getSize(new THREE.Vector3());
  controls.target.copy(c);
  camera.position.set(c.x + sz.z * 0.9, c.y - sz.z * 1.3, c.z + sz.z * 0.15);
  resize();

  const tot = members.reduce((a, m) => a + massOf(m), 0);
  const ori = DATA.report.orientation;
  $('summary').innerHTML = `${members.length} thanh · ${DATA.nodes.length} nút · ${secNames.length} tiết diện<br>` +
    `Khối lượng thanh: <b>${fmt(tot, 0)} kg</b><br>` +
    `<span class="muted">Hướng tự động: ${ori.flipped_out.reduce((a, g) => a + g.members.length, 0)} thanh lật ra ngoài, ` +
    `${ori.unresolved.reduce((a, g) => a + g.members.length, 0)} thanh vẫn cấn.</span>`;
  refreshMaterials();
  updateOvCount();
  window.__ready = true;
}

load().catch((e) => { $('summary').textContent = 'Lỗi tải dữ liệu: ' + e.message; console.error(e); });

renderer.setAnimationLoop(() => {
  controls.update();
  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
});

// cho kiểm thử tự động
window.__app = { select, state, meshes, byId: () => byId, camera, controls };
