import {build} from 'esbuild'
import {readdir} from 'node:fs/promises'
for (const service of await readdir('services')) {
  const dir = 'services/'+service+'/frontend'
  await build({entryPoints:[dir+'/main.jsx'],bundle:true,minify:true,outfile:dir+'/dist/app.js',define:{'process.env.NODE_ENV':'"production"'}})
}
