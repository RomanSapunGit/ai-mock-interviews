// Copies the VAD model/worklet/wasm binaries out of node_modules into
// public/vad/ so Vite can serve them as static assets at a fixed absolute
// path (baseAssetPath/onnxWASMBasePath). These are large binaries (the wasm
// variants alone are 13-27MB each) so they're not committed to git; this
// script regenerates them from node_modules on every `npm install`.
import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const destDir = join(root, 'public', 'vad');
mkdirSync(destDir, { recursive: true });

const files = [
  ['@ricky0123/vad-web/dist/silero_vad_legacy.onnx', 'silero_vad_legacy.onnx'],
  ['@ricky0123/vad-web/dist/vad.worklet.bundle.min.js', 'vad.worklet.bundle.min.js'],
  // Each .wasm binary has a same-named .mjs loader stub that onnxruntime-web
  // dynamically import()s from the same base path at runtime (this is
  // separate from Vite's own bundling) — both must be present or it 404s.
  ['onnxruntime-web/dist/ort-wasm-simd-threaded.wasm', 'ort-wasm-simd-threaded.wasm'],
  ['onnxruntime-web/dist/ort-wasm-simd-threaded.mjs', 'ort-wasm-simd-threaded.mjs'],
  ['onnxruntime-web/dist/ort-wasm-simd-threaded.jsep.wasm', 'ort-wasm-simd-threaded.jsep.wasm'],
  ['onnxruntime-web/dist/ort-wasm-simd-threaded.jsep.mjs', 'ort-wasm-simd-threaded.jsep.mjs'],
  ['onnxruntime-web/dist/ort-wasm-simd-threaded.jspi.wasm', 'ort-wasm-simd-threaded.jspi.wasm'],
  ['onnxruntime-web/dist/ort-wasm-simd-threaded.jspi.mjs', 'ort-wasm-simd-threaded.jspi.mjs'],
  ['onnxruntime-web/dist/ort-wasm-simd-threaded.asyncify.wasm', 'ort-wasm-simd-threaded.asyncify.wasm'],
  ['onnxruntime-web/dist/ort-wasm-simd-threaded.asyncify.mjs', 'ort-wasm-simd-threaded.asyncify.mjs'],
];

for (const [src, destName] of files) {
  copyFileSync(join(root, 'node_modules', src), join(destDir, destName));
}

console.log(`Copied ${files.length} VAD assets to public/vad/`);
