// Chụp nhanh mô hình từ file HTML đã dựng (Playwright có sẵn, swiftshader).
// node tools/shot.mjs <file.html> <thư mục ra> '<json: [{"tag":"ten","t":[x,y,z],"c":[x,y,z]}]>'
//   t = điểm nhìn (m), c = vị trí camera (m). Ảnh: <thư mục ra>/<tag>.png (790x800, bỏ panel trái).
import { createRequire } from 'module';
import { resolve } from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const [,, html, out, json] = process.argv;
const views = JSON.parse(json);
const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1100, height: 800 }, deviceScaleFactor: 1 });
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
await page.goto('file://' + resolve(html));
await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
for (const v of views) {
  await page.evaluate((v) => {
    const x = window.__app;
    x.controls.target.set(...v.t); x.camera.position.set(...v.c);
    x.camera.near = 0.005; x.camera.updateProjectionMatrix(); x.controls.update(); x.requestRender();
  }, v);
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${out}/${v.tag}.png`, clip: { x: 310, y: 0, width: 790, height: 800 } });
}
console.log('ERRORS', errs.length ? errs : 'none');
await browser.close();
