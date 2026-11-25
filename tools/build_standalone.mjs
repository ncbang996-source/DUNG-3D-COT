// Đóng gói app thành MỘT file HTML (three.js + dữ liệu nhúng sẵn), mở trực tiếp bằng trình duyệt.
//   npm install            (lần đầu, cài esbuild)
//   node tools/build_standalone.mjs        -> dist/NC111-32_3D.html
import { build } from 'esbuild';
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const WEB = resolve(ROOT, 'web');
const vendor = {
  name: 'vendor-three',
  setup(b) {
    b.onResolve({ filter: /^three$/ }, () => ({ path: resolve(WEB, 'vendor/three/three.module.js') }));
    b.onResolve({ filter: /^three\/addons\// }, (a) => ({ path: resolve(WEB, 'vendor/three/addons', a.path.slice('three/addons/'.length)) }));
  },
};
const out = await build({
  entryPoints: [resolve(WEB, 'app.js')], bundle: true, format: 'iife', minify: true,
  write: false, plugins: [vendor], legalComments: 'none', target: 'es2020',
});
const js = out.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
const css = readFileSync(resolve(WEB, 'style.css'), 'utf8');
const SCENE = process.argv[2] ? resolve(process.argv[2]) : resolve(WEB, 'data/scene.json');
const data = readFileSync(SCENE, 'utf8').replace(/<\//g, '<\\/');
let html = readFileSync(resolve(WEB, 'index.html'), 'utf8');
html = html.replace(/<link rel="stylesheet" href="style.css">/, () => `<style>\n${css}</style>`);
html = html.replace(/<script type="importmap">[\s\S]*?<\/script>\n?/, '');
html = html.replace(/<script type="module" src="app.js"><\/script>/,
  () => `<script>window.__SCENE__ = ${data};</script>\n<script>/* three.js r160 (MIT) */\n${js}</script>`);
mkdirSync(resolve(ROOT, 'dist'), { recursive: true });
const dst = process.argv[3] ? resolve(process.argv[3]) : resolve(ROOT, 'dist/NC111-32_3D.html');
writeFileSync(dst, html);
console.log(`Đã ghi ${dst} (${(html.length / 1024).toFixed(0)} KB)`);
