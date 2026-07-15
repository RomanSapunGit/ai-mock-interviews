import { createReadStream } from 'node:fs'
import { join } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// onnxruntime-web (used by @ricky0123/vad-web for live speech detection)
// dynamically import()s a .mjs loader next to its .wasm binary at runtime.
// Vite's dev server refuses to serve files under public/ through its module
// pipeline ("should not be imported from source code"), so those specific
// requests need to bypass it and be handed back as plain JS before Vite's
// own middleware rejects them.
function serveVadLoaderScripts() {
  return {
    name: 'serve-vad-loader-scripts',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url?.split('?')[0]
        if (url && url.startsWith('/vad/') && url.endsWith('.mjs')) {
          res.setHeader('Content-Type', 'text/javascript')
          createReadStream(join(server.config.publicDir, url)).pipe(res)
          return
        }
        next()
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), serveVadLoaderScripts()],
})
