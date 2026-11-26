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
function fatal(msg) {
  view.innerHTML = `<div class="fatal">${msg}</div>`;
  const s = document.getElementById('summary'); if (s) s.textContent = 'Không hiển thị được mô hình 3D.';
}
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true });
} catch (e) {
  fatal('Trình duyệt không khởi tạo được WebGL (đồ họa 3D).<br>Hãy mở bằng Chrome, Edge hoặc Firefox bản mới, ' +
        'và bật "Tăng tốc phần cứng" (Hardware acceleration) trong cài đặt trình duyệt.<br><small>' + e.message + '</small>');
  throw e;
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.domElement.style.display = 'block';
view.appendChild(renderer.domElement);
renderer.domElement.addEventListener('webglcontextlost', (e) => {
  e.preventDefault();
  fatal('Mất kết nối đồ họa (WebGL context lost). Card đồ họa hoặc trình duyệt đã ngắt.<br>' +
        'Hãy tải lại trang; nếu lặp lại, bật "Tăng tốc phần cứng" hoặc thử trình duyệt khác.');
});
const labelRenderer = new CSS2DRenderer();
labelRenderer.domElement.style.position = 'absolute';
labelRenderer.domElement.style.top = '0';
labelRenderer.domElement.style.pointerEvents = 'none';
view.appendChild(labelRenderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, 1, 0.05, 2000);
camera.up.set(0, 0, 1);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = false;
controls.addEventListener('change', () => requestRender());
scene.add(new THREE.HemisphereLight(0xffffff, 0x667080, 1.4));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(30, -40, 80);
scene.add(sun);

const dark = matchMedia('(prefers-color-scheme: dark)').matches;
scene.background = new THREE.Color(dark ? 0x101317 : 0xeef1f5);

const steelGroup = new THREE.Group();
const plateGroup = new THREE.Group();
const boltGroup = new THREE.Group();
const axisGroup = new THREE.Group();
const nodeLabelGroup = new THREE.Group();
const memLabelGroup = new THREE.Group();
scene.add(steelGroup, plateGroup, boltGroup, axisGroup, nodeLabelGroup, memLabelGroup);
axisGroup.visible = false;

function resize() {
  const w = view.clientWidth, h = view.clientHeight;
  renderer.setSize(w, h);
  labelRenderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  requestRender();
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

// Cắt đa giác giữ phần s2 <= h (Sutherland–Hodgman với một nửa mặt phẳng).
function clipBelow(poly, h) {
  const out = [];
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i], b = poly[(i + 1) % poly.length];
    const ina = a[1] <= h + 1e-9, inb = b[1] <= h + 1e-9;
    if (ina) out.push(a);
    if (ina !== inb) { const t = (h - a[1]) / (b[1] - a[1]); out.push([a[0] + t * (b[0] - a[0]), h]); }
  }
  return out;
}

// Thanh có vát cánh (cut1/cut2 = {flange: 'conn'|'out'|'heel', a: ngang cánh, b: dọc thanh} mm): dựng 2 cánh thành 2
// khối phẳng, cắt góc mép cánh ở đầu thanh tương ứng.
// góc bẻ cánh (rad) tại x (mm dọc thanh): 0 ngoài vùng, tuyến tính trong đoạn chuyển tiếp
function bendTheta(bends, x) {
  let th = 0;
  for (const b of bends) {
    const f = Math.max(0, Math.min(1, (x - (b.x0 - b.ramp)) / b.ramp, ((b.x1 + b.ramp) - x) / b.ramp));
    const v = f * b.theta_deg * Math.PI / 180;
    if (Math.abs(v) > Math.abs(th)) th = v;
  }
  return th;
}

// giữ phần đa giác (x, w) nằm trong x0 <= x <= x1
function clipX(poly, x0, x1) {
  const half = (pg, keep, xc) => {
    const out = [];
    for (let i = 0; i < pg.length; i++) {
      const a = pg[i], b = pg[(i + 1) % pg.length];
      const ia = keep(a[0]), ib = keep(b[0]);
      if (ia) out.push(a);
      if (ia !== ib) { const t = (xc - a[0]) / (b[0] - a[0]); out.push([xc, a[1] + t * (b[1] - a[1])]); }
    }
    return out;
  };
  return half(half(poly, (x) => x >= x0 - 1e-9, x0), (x) => x <= x1 + 1e-9, x1);
}

function buildCutGeometry(m) {
  const s = sections[m.section];
  const [g1, g2] = m.g;
  const [e1, e2] = frameOf(m, m.variant).map((a) => new THREE.Vector3(...a));
  const off = new THREE.Vector3(...((m.offs && m.offs[m.variant]) || [0, 0, 0]));
  const p1 = new THREE.Vector3(...(m.p1d || m.p1)).add(off).add(new THREE.Vector3(...(m.poff1 || [0, 0, 0])));
  const p2 = new THREE.Vector3(...(m.p2d || m.p2)).add(off).add(new THREE.Vector3(...(m.poff2 || [0, 0, 0])));
  const L = p1.distanceTo(p2) * 1000;
  const u = p2.clone().sub(p1).normalize();
  // thanh bẻ lệch / ép sát giữa thanh: độ sâu theo chiều dài (prof), cộng phần lệch so với nối thẳng 2 đầu
  const prof = m.prof, pn = m.prof_n ? new THREE.Vector3(...m.prof_n) : null;
  const extra = (x) => {
    if (!prof) return 0;
    let d = prof[prof.length - 1][1];
    for (let i = 0; i < prof.length - 1; i++) {
      const [xa, da] = prof[i], [xb, db] = prof[i + 1];
      if (x <= xb) { d = xb > xa ? da + (db - da) * (x - xa) / (xb - xa) : db; break; }
    }
    const d0 = prof[0][1], d1 = prof[prof.length - 1][1];
    return d - (d0 + (d1 - d0) * x / L);
  };
  const P = (x, a, b) => {
    const v = p1.clone().lerp(p2, x / L).addScaledVector(e1, (a - g1) / 1000).addScaledVector(e2, (b - g2) / 1000);
    return pn ? v.addScaledVector(pn, extra(x) / 1000) : v;
  };
  const pos = [];
  const push = (...vs) => vs.forEach((v) => pos.push(v.x, v.y, v.z));
  for (const fl of ['conn', 'out']) {
    // đa giác trong mặt (x dọc thanh, w ngang cánh từ lưng tới mép)
    const W = s.b;
    let poly = [[0, 0], [L, 0], [L, W], [0, W]];
    const c1 = m.cut1 && m.cut1.flange === fl ? m.cut1 : null, c2 = m.cut2 && m.cut2.flange === fl ? m.cut2 : null;
    // vát góc LƯNG (flange 'heel'): cánh liên kết cắt tam giác a x b ở góc lưng; cánh còn lại (gắn ở lưng) bị
    // đường cắt đi qua nên lùi đầu thanh b mm
    const h1 = m.cut1 && m.cut1.flange === 'heel' ? m.cut1 : null, h2 = m.cut2 && m.cut2.flange === 'heel' ? m.cut2 : null;
    poly = [];
    if (h1 && fl === 'conn') poly.push([0, h1.a], [h1.b, 0]); else poly.push([h1 ? h1.b : 0, 0]);
    if (h2 && fl === 'conn') poly.push([L - h2.b, 0], [L, h2.a]); else poly.push([h2 ? L - h2.b : L, 0]);
    if (c2) poly.push([L, W - c2.a], [L - c2.b, W]); else poly.push([h2 && fl === 'out' ? L - h2.b : L, W]);
    if (c1) poly.push([c1.b, W], [0, W - c1.a]); else poly.push([h1 && fl === 'out' ? h1.b : 0, W]);
    const bends = fl === 'out' ? (m.bends || []) : [];
    const map = fl === 'conn' ? (x, w, t) => P(x, w, t) : (x, w, t) => {
      if (!bends.length) return P(x, t, w);
      // cánh bẻ cục bộ: xoay quanh mép lưng (trục thanh) góc theta(x)
      const th = bendTheta(bends, x);
      const H = P(x, 0, 0);
      const v = P(x, t, w).sub(H);
      return H.add(v.applyAxisAngle(u, th));
    };
    // cắt đa giác thành các dải theo trạm x (đầu/cuối đoạn chuyển tiếp) để mặt bẻ đi đúng hình
    const stations = [...new Set(bends.flatMap((b) => [b.x0 - b.ramp, b.x0, b.x1, b.x1 + b.ramp])
      .concat(prof ? prof.map((q) => q[0]) : [])
      .filter((x) => x > 0 && x < L))].sort((a, b) => a - b);
    const cuts = [0, ...stations, L];
    for (let k = 0; k < cuts.length - 1; k++) {
      let pg = clipX(poly, cuts[k], cuts[k + 1]);
      if (pg.length < 3) continue;
      const A0 = pg.map(([x, w]) => map(x, w, 0)), A1 = pg.map(([x, w]) => map(x, w, s.t));
      const n = pg.length;
      for (let i = 0; i < n; i++) { const j = (i + 1) % n; push(A0[i], A0[j], A1[j], A0[i], A1[j], A1[i]); }
      for (let i = 1; i < n - 1; i++) { push(A0[0], A0[i + 1], A0[i]); push(A1[0], A1[i], A1[i + 1]); }
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.computeVertexNormals();
  return geo;
}

function buildGeometry(m) {
  if (m.cut1 || m.cut2 || (m.bends && m.bends.length) || m.prof) return buildCutGeometry(m);
  const s = sections[m.section];
  const chamfer = !!(m.chamfer1 || m.chamfer2);
  // thanh vát: phần cánh không khoan lỗ cao hơn h0 = t + r1 dựng riêng (hình thang), profile cắt tại h0
  const prof = chamfer ? clipBelow(s.profile, s.t + s.r1) : s.profile;   // mm, heel at origin
  const [g1, g2] = m.g;                              // mm
  const [e1, e2] = frameOf(m, m.variant).map((a) => new THREE.Vector3(...a));
  // đầu thanh vẽ: điểm DXF (hoặc điểm bắt đã dời) + dịch ép sát cánh thanh cánh + đẩy ra khỏi bản mã
  const off = new THREE.Vector3(...((m.offs && m.offs[m.variant]) || [0, 0, 0]));
  const p1 = new THREE.Vector3(...(m.p1d || m.p1)).add(off).add(new THREE.Vector3(...(m.poff1 || [0, 0, 0])));
  const p2 = new THREE.Vector3(...(m.p2d || m.p2)).add(off).add(new THREE.Vector3(...(m.poff2 || [0, 0, 0])));
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
  if (chamfer) {
    // cánh không khoan lỗ (dọc s2, dày theo s1): hình thang vát 45° hai đầu, từ chiều cao h0 tới b
    const h0 = s.t + s.r1, L = p1.distanceTo(p2) * 1000, cmax = Math.min(s.b - h0, L / 2);
    const c1 = m.chamfer1 ? cmax : 0, c2 = m.chamfer2 ? cmax : 0;   // chỉ vát ở đầu thanh thật
    const u = p2.clone().sub(p1).normalize();
    const P = (x, a, b) => {
      const t = x / L;                 // x tính từ p1 (mm); nội suy p1-p2 để giữ độ dịch từng đầu
      return p1.clone().lerp(p2, t).addScaledVector(e1, (a - g1) / 1000).addScaledVector(e2, (b - g2) / 1000);
    };
    const quad = [[0, h0], [L, h0], [L - c2, h0 + cmax], [c1, h0 + cmax]];  // (x, s2)
    const A0 = quad.map(([x, b]) => P(x, 0, b)), A1 = quad.map(([x, b]) => P(x, s.t, b));
    for (let i = 0; i < 4; i++) { const j = (i + 1) % 4; push(A0[i], A0[j], A1[j], A0[i], A1[j], A1[i]); }
    push(A0[0], A0[2], A0[1], A0[0], A0[3], A0[2], A1[0], A1[1], A1[2], A1[0], A1[2], A1[3]);
  }
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
  if (state.colorBy === 'variant') {
    if (m.rule === 'leg') return VAR_COL.leg;
    if (VAR_COL[m.variant]) return VAR_COL[m.variant];
    return { NGOAI: '#ff9f1c', TRONG: '#4aa3ff', LEN: '#e0393e', XUONG: '#139a43' }[m.side] || '#888';
  }
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
  requestRender();
}

function renderLegend() {
  let entries;
  if (state.colorBy === 'type') entries = Object.entries(TYPE_COL);
  else if (state.colorBy === 'variant') entries = members.some((m) => m.variant === 'bv')
    ? [['Thanh cánh', VAR_COL.leg], ['NGOÀI (mặt cột)', '#ff9f1c'], ['TRONG (mặt cột)', '#4aa3ff'], ['Vách: cánh lên', '#e0393e'], ['Vách: cánh xuống', '#139a43']]
    : [['Thanh cánh', VAR_COL.leg], ...VARIANTS.map((v) => [v, VAR_COL[v]])];
  else entries = Object.entries(sectionColors);
  $('legend').innerHTML = entries.map(([k, c]) => `<div><span style="background:${c}"></span>${k}</div>`).join('');
}

function rebuildMember(m) {
  const mesh = meshes.get(m.id);
  mesh.geometry.dispose();
  mesh.geometry = buildGeometry(m);
  requestRender();
}

// ---------------------------------------------------------------- bản mã, bu lông
const plateMat = new THREE.MeshStandardMaterial({ color: 0x2f9e8f, metalness: 0.3, roughness: 0.55, side: THREE.DoubleSide });
const boltMat = new THREE.MeshStandardMaterial({ color: 0xd4a017, metalness: 0.6, roughness: 0.35 });
const nutMat = new THREE.MeshStandardMaterial({ color: 0xb03a2e, metalness: 0.5, roughness: 0.4 });   // đai ốc (đỏ) để thấy hướng
const fillerMat = new THREE.MeshStandardMaterial({ color: 0x7a5cc4, metalness: 0.3, roughness: 0.5, side: THREE.DoubleSide });
function buildPlates() {
  for (const [k, pl] of (DATA.plates || []).entries()) {
    const o = new THREE.Vector3(...pl.origin), a1 = new THREE.Vector3(...pl.a1), a2 = new THREE.Vector3(...pl.a2);
    const td = new THREE.Vector3(...pl.thick_dir).multiplyScalar(pl.t_mm / 1000);
    const P = pl.poly.map(([x, y]) => o.clone().addScaledVector(a1, x).addScaledVector(a2, y));
    const Q = P.map((p) => p.clone().add(td));
    const pos = [];
    const push = (...vs) => vs.forEach((v) => pos.push(v.x, v.y, v.z));
    const n = P.length;
    for (let i = 0; i < n; i++) { const j = (i + 1) % n; push(P[i], P[j], Q[j], P[i], Q[j], Q[i]); }
    for (let i = 1; i < n - 1; i++) { push(P[0], P[i], P[i + 1]); push(Q[0], Q[i + 1], Q[i]); }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.computeVertexNormals();
    const mesh = new THREE.Mesh(geo, pl.kind === 'filler' ? fillerMat : plateMat);
    mesh.userData = { plate: k, pickable: true };
    plateGroup.add(mesh);
  }
}
function buildBolts() {
  const bolts = DATA.bolts || [];
  if (!bolts.length) return;
  const shaftGeo = new THREE.CylinderGeometry(0.5, 0.5, 1, 10);   // trục Y, co giãn theo bu lông
  const nutGeo = new THREE.CylinderGeometry(0.5, 0.5, 1, 6);      // lục giác
  const shafts = new THREE.InstancedMesh(shaftGeo, boltMat, bolts.length);
  const heads = new THREE.InstancedMesh(nutGeo, boltMat, bolts.length);
  const nuts = new THREE.InstancedMesh(nutGeo, nutMat, bolts.length);
  const Y = new THREE.Vector3(0, 1, 0), M = new THREE.Matrix4(), q = new THREE.Quaternion();
  bolts.forEach((b, i) => {
    const d = b.d_mm / 1000, nd = new THREE.Vector3(...(b.nut || b.axis));
    const c = new THREE.Vector3(...b.p);
    q.setFromUnitVectors(Y, nd);
    if (b.grip_mm != null && b.L_mm != null) {
      // p = mặt tựa đầu bu lông; thân dài L theo ký hiệu bản vẽ xuyên qua các lớp thép (kẹp = grip)
      const L = b.L_mm / 1000, grip = b.grip_mm / 1000;
      M.compose(c.clone().addScaledVector(nd, L / 2), q, new THREE.Vector3(d, L, d)); shafts.setMatrixAt(i, M);
      M.compose(c.clone().addScaledVector(nd, -0.33 * d), q, new THREE.Vector3(1.7 * d, 0.65 * d, 1.7 * d)); heads.setMatrixAt(i, M);
      M.compose(c.clone().addScaledVector(nd, grip + 0.4 * d), q, new THREE.Vector3(1.8 * d, 0.8 * d, 1.8 * d)); nuts.setMatrixAt(i, M);
      return;
    }
    const grip = b.t_mm / 1000 + (b.centered ? 0 : b.t_mm / 1000);   // chiều dày kẹp ước lượng (mô hình cũ)
    const len = grip + 1.6 * d;
    M.compose(c.clone().addScaledVector(nd, 0.2 * d), q, new THREE.Vector3(d, len, d)); shafts.setMatrixAt(i, M);
    M.compose(c.clone().addScaledVector(nd, -(grip / 2 + 0.35 * d)), q, new THREE.Vector3(1.7 * d, 0.65 * d, 1.7 * d)); heads.setMatrixAt(i, M);
    M.compose(c.clone().addScaledVector(nd, grip / 2 + 0.4 * d), q, new THREE.Vector3(1.8 * d, 0.8 * d, 1.8 * d)); nuts.setMatrixAt(i, M);
  });
  for (const im of [shafts, heads, nuts]) im.userData.bolts = true;
  boltGroup.add(shafts, heads, nuts);
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
function boltText(m) {
  const opts = Object.entries(m.bolts).filter(([, n]) => n != null);
  if (!m.bolt) return '—';
  // Chọn sẵn ở Python: ít con nhất, bằng nhau lấy đường kính nhỏ hơn.
  return `${m.bolt.count} × ${m.bolt.size}` +
    (opts.length > 1 ? ` <span class="muted">(${opts.map(([k, n]) => `${k}:${n}`).join(', ')})</span>` : '');
}

function varText(m, v) {
  if (!VAR_TEXT[m.rule] || !(v in VAR_TEXT[m.rule])) return m.side ? `Theo bản vẽ: thanh ${m.side === 'NGOAI' ? 'NGOÀI' : 'TRONG'}` : v;
  let t = VAR_TEXT[m.rule][v];
  if (m.default_up) t = t.replace('chĩa xuống', '§').replace('chĩa lên', 'chĩa xuống').replace('§', 'chĩa lên');
  return t;
}

function showInfo(m) {
  $('info').hidden = !m;
  if (!m) return;
  const s = sections[m.section];
  $('info').querySelector('h2').firstChild.textContent = 'Thanh ';
  $('iId').textContent = m.id;
  const rows = [
    ['Nhóm', m.group], ['Tiết diện', `${m.section} (JIS G3192 ${s.b}×${s.b}×${s.t})`], ['Type', m.type],
    ['Chiều dài', fmt(m.length, 3) + ' m'], ['A', fmt(m.A_cm2) + ' cm²'], ['Khối lượng', fmt(massOf(m), 1) + ' kg'],
    ['Bu lông', boltText(m)], ['Nút', `${m.node1 ?? '?'} → ${m.node2 ?? '?'}`],
    ['Quy tắc', m.rule === 'leg' ? 'Thanh cánh (lưng ra ngoài góc)' :
      m.rule === 'face' ? `Trên mặt cột ${m.face}` + (m.x_pair ? ' · cặp chữ X' : '') +
        (m.variant.startsWith('out') ? ' · lưng áp mặt NGOÀI cánh thanh cánh' : ' · lưng áp mặt TRONG cánh thanh cánh') :
      'Vách ngang / xà'],
    ...((m.bends && m.bends.length) ? [['Bẻ cánh cục bộ', m.bends.map((b) => `${Math.round(b.x1 - b.x0)} mm, ${Math.abs(b.theta_deg).toFixed(1)}° (vách ${b.plan})`).join('; ')]] : []),
    ...((m.cut1 || m.cut2) ? [['Vát cánh', [m.cut1, m.cut2].filter(Boolean).map((c) => c.note || `${c.a}x${c.b}`).join('; ')]] : []),
    ...(m.drawing && m.drawing.delta_mm ? [['Độ sâu 2 đầu (mm)', m.drawing.delta_mm.join(' / ')]] : []),
    ...(m.p1d ? [['Điểm bắt đã dời', `${m.p1d.join(', ')} → ${m.p2d.join(', ')}`]] : []),
    ['Hướng cánh', m.rule === 'leg' ? '—' : `${m.variant} · ${varText(m, m.variant)}` +
      (m.default_up ? ' (XAD: mặc định hướng lên)' : '') + (m.variant !== m.auto_variant ? ' <b>(đã sửa)</b>' : '')],
  ];
  $('iTable').innerHTML = rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('');
  const sel = $('iVariant');
  sel.disabled = m.rule === 'leg';
  $('applyGroup').disabled = $('resetVar').disabled = m.rule === 'leg';
  sel.innerHTML = m.rule === 'leg' ? '<option>—</option>' :
    Object.keys(m.frames || {}).filter((v) => !VARIANTS.includes(v)).map((v) => `<option value="${v}" selected>${varText(m, v)}</option>`).join('') +
    VARIANTS.filter((v) => m.frames && m.frames[v]).map((v) => `<option value="${v}" ${v === m.variant ? 'selected' : ''}>${v} · ${varText(m, v)}</option>`).join('');
  drawSection(m);
}

function showPlate(k) {
  const pl = DATA.plates[k];
  $('info').hidden = false;
  $('iId').textContent = '';
  $('info').querySelector('h2').firstChild.textContent = 'Bản mã ';
  const rows = [
    ['Loại', pl.kind === 'filler' ? 'Tấm đệm 45×45 nút giao chữ X' : pl.on_leg ? 'Bản mã áp cánh thanh cánh' : 'Bản mã'],
    ['Lý do', pl.reason || ''],
    ...(pl.leg_bolts ? [['Bu lông bắt thanh cánh', `${pl.leg_bolts} × M${pl.d_max_mm}`]] : []),
    ['Chiều dày', pl.t_mm + ' mm'], ['Diện tích', fmt(pl.area_m2 * 1e4, 0) + ' cm²'],
    ['Khối lượng', fmt(pl.mass_kg, 2) + ' kg'], ['Thanh nối', pl.members.join(', ')],
    ['Bu lông lớn nhất', `${pl.bolt_max} con / đầu thanh, d = ${pl.d_max_mm} mm`],
    ['Cạnh đường bao (mm)', pl.poly.map((p, i) => {
      const q = pl.poly[(i + 1) % pl.poly.length];
      return Math.round(Math.hypot(q[0] - p[0], q[1] - p[1]) * 1000);
    }).join(' · ')],
  ];
  $('iTable').innerHTML = rows.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join('');
  $('secSvg').innerHTML = '';
  $('iVariant').innerHTML = '<option>—</option>';
  $('iVariant').disabled = $('applyGroup').disabled = $('resetVar').disabled = true;
}

function showBolt(i) {
  const b = DATA.bolts[i];
  $('info').hidden = false;
  $('iId').textContent = '';
  $('info').querySelector('h2').firstChild.textContent = 'Bu lông ';
  const rows = [
    ['Đường kính', 'M' + b.d_mm],
    ['Chiều dài', b.L_mm != null ? b.L_mm + ' mm' : '—'],
    ['Nguồn chiều dài', b.L_from || '—'],
    ['Chiều dày kẹp', b.grip_mm != null ? b.grip_mm + ' mm' : '—'],
    ['Loại', b.kind || ''],
    ['Tọa độ mặt tựa đầu (mm)', b.p.map((v) => Math.round(v * 1000)).join(', ')],
  ];
  $('iTable').innerHTML = rows.map(([a, c]) => `<tr><td>${a}</td><td>${c}</td></tr>`).join('');
  $('secSvg').innerHTML = '';
  $('iVariant').innerHTML = '<option>—</option>';
  $('iVariant').disabled = $('applyGroup').disabled = $('resetVar').disabled = true;
}

// ---------------------------------------------------------------- đo khoảng cách
const measureGroup = new THREE.Group();
scene.add(measureGroup);
const measure = { on: false, pts: [] };
function setMeasure(on) {
  measure.on = on;
  $('btnMeasure').textContent = on ? 'Đang đo… (nhấn để tắt)' : 'Đo khoảng cách';
  renderer.domElement.style.cursor = on ? 'crosshair' : '';
}
function clearMeasure() {
  measure.pts = [];
  while (measureGroup.children.length) {
    const o = measureGroup.children.pop();
    if (o.element) o.element.remove();
  }
  $('measureOut').innerHTML = 'Đã xóa. Nhấn 2 điểm để đo.';
  requestRender();
}
function snapPoint(hit, ev) {
  // bắt vào đỉnh gần nhất của khối được nhấn nếu cách con trỏ < 14 px trên màn hình
  const r = renderer.domElement.getBoundingClientRect();
  const geo = hit.object.geometry, pos = geo && geo.attributes.position;
  let best = null;
  if (pos && !hit.object.isInstancedMesh && hit.face) {
    const cand = [hit.face.a, hit.face.b, hit.face.c];
    for (const ix of cand) {
      const v = new THREE.Vector3().fromBufferAttribute(pos, ix).applyMatrix4(hit.object.matrixWorld);
      const sp = v.clone().project(camera);
      const sx = (sp.x + 1) / 2 * r.width + r.left, sy = (1 - sp.y) / 2 * r.height + r.top;
      const d = Math.hypot(sx - ev.clientX, sy - ev.clientY);
      if (d < 14 && (!best || d < best.d)) best = { v, d };
    }
  }
  return best ? { p: best.v, snapped: true } : { p: hit.point.clone(), snapped: false };
}
function addMeasurePoint(p, snapped) {
  if (measure.pts.length === 2) clearMeasure();
  measure.pts.push(p);
  const dot = new THREE.Mesh(new THREE.SphereGeometry(0.012, 12, 8), new THREE.MeshBasicMaterial({ color: 0xff00aa }));
  dot.position.copy(p);
  measureGroup.add(dot);
  const f = (v) => v.toArray().map((x) => Math.round(x * 1000)).join(', ');
  if (measure.pts.length === 1) {
    $('measureOut').innerHTML = `Điểm 1${snapped ? ' (bắt đỉnh)' : ''}: (${f(p)}) mm. Nhấn điểm 2.`;
  } else {
    const [a, b] = measure.pts;
    const g = new THREE.BufferGeometry().setFromPoints([a, b]);
    measureGroup.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0xff00aa, depthTest: false })));
    const d = a.distanceTo(b) * 1000, dv = b.clone().sub(a).multiplyScalar(1000);
    const el = document.createElement('div');
    el.className = 'lbl mem';
    el.style.background = '#ff00aa'; el.style.color = '#fff';
    el.textContent = Math.round(d) + ' mm';
    const lab = new CSS2DObject(el);
    lab.position.copy(a.clone().lerp(b, 0.5));
    measureGroup.add(lab);
    $('measureOut').innerHTML = `<b>Khoảng cách: ${fmt(d, 1)} mm</b><br>ΔX ${fmt(dv.x, 1)} · ΔY ${fmt(dv.y, 1)} · ΔZ ${fmt(dv.z, 1)} mm` +
      `<br><span class="muted">Điểm 1 (${f(a)}), điểm 2 (${f(b)}) mm${snapped ? ' · điểm 2 bắt đỉnh' : ''}</span>`;
  }
  requestRender();
}
$('btnMeasure').addEventListener('click', () => setMeasure(!measure.on));
$('btnMeasureClear').addEventListener('click', clearMeasure);
window.addEventListener('keydown', (e) => {
  if (e.key === 'm' || e.key === 'M') setMeasure(!measure.on);
  if (e.key === 'Escape') clearMeasure();
});

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
  const objs = [...meshes.values()].filter((x) => x.visible && x.userData.pickable);
  if (plateGroup.visible) objs.push(...plateGroup.children);
  if (boltGroup.visible) objs.push(...boltGroup.children);
  const hit = ray.intersectObjects(objs)[0];
  if (measure.on) {
    if (hit) { const sp = snapPoint(hit, e); addMeasurePoint(sp.p, sp.snapped); }
    return;
  }
  if (hit && hit.object.userData.bolts && hit.instanceId !== undefined) { select(null); showBolt(hit.instanceId); return; }
  if (hit && hit.object.userData.plate !== undefined) { select(null); showPlate(hit.object.userData.plate); return; }
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
function platesStats() {
  const P = DATA.plates || [], B = DATA.bolts || [];
  const byT = {};
  for (const p of P) { const key = (p.kind === 'filler' ? 'Tấm đệm ' : 'Bản mã ') + p.t_mm; const s = (byT[key] ??= { n: 0, a: 0, m: 0 }); s.n++; s.a += p.area_m2; s.m += p.mass_kg; }
  const byD = {};
  for (const b of B) byD['M' + b.d_mm] = (byD['M' + b.d_mm] || 0) + 1;
  const pm = P.reduce((a, p) => a + p.mass_kg, 0);
  return `<h3>Bản mã (A × t × 7850)</h3><table><tr><th>Loại, dày (mm)</th><th>Số bản</th><th>Diện tích (m²)</th><th>Khối lượng (kg)</th></tr>` +
    Object.entries(byT).sort((a, b) => a[0].localeCompare(b[0], 'vi', { numeric: true })).map(([t, s]) => `<tr><td>${t}</td><td>${s.n}</td><td>${fmt(s.a, 3)}</td><td>${fmt(s.m, 1)}</td></tr>`).join('') +
    `<tr><th>Tổng</th><th>${P.length}</th><th></th><th>${fmt(pm, 1)}</th></tr></table>` +
    `<h3>Bu lông (không tính mối nối thanh cánh)</h3><p>${Object.entries(byD).map(([k, n]) => `${k}: ${n} con`).join(' · ')}</p>` +
    `<p class="muted">Bản mã: nút thanh cánh có ≥ 2 thanh cùng mặt tiếp xúc, hoặc thanh > 2 bu lông. Nút giao chữ X: 1 bu lông + tấm đệm 45×45. Bản mã tính theo hướng cánh tự động; đổi hướng trong app không tính lại bản mã.</p>`;
}
$('btnStats').addEventListener('click', () => {
  const rows = stats();
  const tot = rows.reduce((a, [, s]) => ({ c: a.c + s.count, l: a.l + s.len, m: a.m + s.mass }), { c: 0, l: 0, m: 0 });
  $('statsBody').innerHTML = `<h3>Thanh thép góc</h3><table><tr><th>Tiết diện</th><th>A (cm²)</th><th>Số thanh</th><th>Tổng dài (m)</th><th>Khối lượng (kg)</th></tr>` +
    rows.map(([k, s]) => `<tr><td>${k}</td><td>${fmt(s.A)}</td><td>${s.count}</td><td>${fmt(s.len)}</td><td>${fmt(s.mass, 1)}</td></tr>`).join('') +
    `<tr><th>Tổng</th><th></th><th>${tot.c}</th><th>${fmt(tot.l)}</th><th>${fmt(tot.m, 1)}</th></tr></table>
    ${platesStats()}`;
  $('statsDlg').showModal();
});
$('btnStatsCsv').addEventListener('click', () => {
  const rows = stats().map(([k, s]) => [k, s.A, s.count, s.len.toFixed(3), s.mass.toFixed(2)].join(','));
  download('khoi_luong_theo_tiet_dien.csv', ['section,A_cm2,count,length_m,mass_kg', ...rows].join('\n') + '\n');
});

// ---------------------------------------------------------------- controls
$('colorBy').addEventListener('change', (e) => { state.colorBy = e.target.value; refreshMaterials(); if (state.selected) drawSection(byId.get(state.selected)); });
$('showSteel').addEventListener('change', (e) => { steelGroup.visible = e.target.checked; requestRender(); });
$('showPlates').addEventListener('change', (e) => { plateGroup.visible = e.target.checked; requestRender(); });
$('showBolts').addEventListener('change', (e) => { boltGroup.visible = e.target.checked; requestRender(); });
$('showAxis').addEventListener('change', (e) => { axisGroup.visible = e.target.checked; requestRender(); });
$('showNodes').addEventListener('change', (e) => { ensureLabels(); nodeLabelGroup.visible = e.target.checked; requestRender(); });
$('showMemNo').addEventListener('change', (e) => { ensureLabels(); memLabelGroup.visible = e.target.checked; refreshMaterials(); });
for (const [id, key] of [['fSection', 'fSection'], ['fType', 'fType'], ['fGroup', 'fGroup']]) {
  $(id).addEventListener('change', (e) => { state[key] = e.target.value; refreshMaterials(); });
}
$('fGhost').addEventListener('change', (e) => { state.ghost = e.target.checked; refreshMaterials(); });

// ---------------------------------------------------------------- load
async function load() {
  // Bản độc lập (một file HTML) nhúng sẵn dữ liệu vào window.__SCENE__; bản thường tải qua fetch.
  DATA = window.__SCENE__ || await (await fetch('data/scene.json')).json();
  members = DATA.members;
  sections = DATA.sections;
  if (DATA.title) { document.querySelector('#panel h1').textContent = DATA.title; document.title = DATA.title; }
  byId = new Map(members.map((m) => [m.id, m]));
  const secNames = Object.keys(sections).sort((a, b) => sections[a].b - sections[b].b || a.localeCompare(b));
  secNames.forEach((s, i) => { sectionColors[s] = PALETTE[i % PALETTE.length]; });

  for (const m of members) {
    const mesh = new THREE.Mesh(buildGeometry(m), material(colorOf(m), false));
    mesh.userData = { id: m.id, pickable: true };
    meshes.set(m.id, mesh);
    steelGroup.add(mesh);
  }
  buildPlates();
  buildBolts();
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
  controls.update();
  resize();

  const tot = members.reduce((a, m) => a + massOf(m), 0);
  const ori = DATA.report.orientation;
  $('summary').innerHTML = `${members.length} thanh · ${DATA.nodes.length} nút · ${secNames.length} tiết diện<br>` +
    `Khối lượng thanh: <b>${fmt(tot, 0)} kg</b> · bản mã ${(DATA.plates || []).filter((p) => p.kind !== 'filler').length} bản, ` +
    `${fmt((DATA.plates || []).reduce((a, p) => a + p.mass_kg, 0), 0)} kg (kể cả tấm đệm)<br>` +
    `<span class="muted">Cặp chữ X: ${ori.x_members.outside.length} thanh ngoài, ${ori.x_members.inside.length} thanh trong · ` +
    `cấn: ${(ori.clash_other || []).length} cặp, chồng mép cùng mặt phẳng: ${(ori.clash_coplanar_overlap || []).length} cặp.</span>`;
  refreshMaterials();
  updateOvCount();
  window.__ready = true;
}

load().catch((e) => { $('summary').textContent = 'Lỗi tải dữ liệu: ' + e.message; console.error(e); });

// Chỉ vẽ lại khi có thay đổi (không vẽ liên tục) để nhẹ máy và tránh chớp màn hình.
let pending = false;
function requestRender() {
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => {
    pending = false;
    renderer.render(scene, camera);
    labelRenderer.render(scene, camera);
  });
}

// cho kiểm thử tự động
window.__app = { select, state, meshes, byId: () => byId, camera, controls, requestRender, addMeasurePoint, setMeasure };
