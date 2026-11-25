// Chạy thử app web bằng Playwright (không cần server): node tests/e2e/smoke.mjs <thư_mục_ảnh>
import { createRequire } from 'module';
import { readFileSync, existsSync } from 'fs';
import { join, extname, resolve } from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const WEB = resolve(new URL('../../web', import.meta.url).pathname);
const OUT = process.argv[2] || '.';
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json' };
const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
await page.route('http://app.local/**', (route) => {
  let p = new URL(route.request().url()).pathname;
  if (p === '/') p = '/index.html';
  const f = join(WEB, p);
  if (!existsSync(f)) return route.fulfill({ status: 404, body: 'nf' });
  route.fulfill({ status: 200, contentType: MIME[extname(f)] || 'application/octet-stream', body: readFileSync(f) });
});
await page.goto('http://app.local/');
await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
const info = await page.evaluate(() => ({ meshes: window.__app.meshes.size, summary: document.getElementById('summary').innerText }));
console.log(JSON.stringify(info));
await page.waitForTimeout(500);
await page.screenshot({ path: join(OUT, 'app_overview.png') });
// Chọn thanh 569 (CĐ) và xem thông tin, phóng gần chân cột
await page.evaluate(() => {
  const a = window.__app; a.select(569);
  a.controls.target.set(-2.3, -2.3, 21); a.camera.position.set(-0.2, -5.5, 22.2); a.controls.update(); a.requestRender();
});
await page.waitForTimeout(500);
await page.screenshot({ path: join(OUT, 'app_base_detail.png') });
const rows = await page.evaluate(() => document.getElementById('iTable').innerText);
console.log(rows);
// Thanh xiên bị lật ra ngoài + tô theo hướng cánh, đoạn thân giữa
await page.selectOption('#colorBy', 'variant');
await page.evaluate(() => {
  const a = window.__app; a.select(833);
  const m = a.byId().get(833); const c = m.p1.map((v, i) => (v + m.p2[i]) / 2);
  a.controls.target.set(...c); a.camera.position.set(c[0] + 2.5, c[1] - 6, c[2] + 1.5); a.controls.update(); a.requestRender();
});
await page.waitForTimeout(500);
await page.screenshot({ path: join(OUT, 'app_variant.png') });
// Bảng khối lượng
await page.click('#btnStats');
const stats = await page.evaluate(() => document.getElementById('statsBody').innerText);
console.log(stats);
console.log('ERRORS:', errors.length ? errors : 'none');
await browser.close();
