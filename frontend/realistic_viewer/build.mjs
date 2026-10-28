import {build} from 'esbuild';
import {copyFile, mkdir, readFile, writeFile} from 'node:fs/promises';
const out = new URL('../../src/archimind/_viewer_assets/', import.meta.url);
await mkdir(out, {recursive:true});
await build({entryPoints:[new URL('./src/main.js',import.meta.url).pathname], outfile:new URL('viewer.js',out).pathname,
  bundle:true, format:'esm', platform:'browser', target:['es2022'], minify:true, legalComments:'linked', logLevel:'info'});
for (const file of ['viewer.html','viewer.css','standalone.js','index.html','standalone-room.js','room.html']) {
  await copyFile(new URL(`./src/${file}`,import.meta.url),new URL(file,out));
}
await writeFile(new URL('THIRD_PARTY_NOTICES.txt',out), 'Three.js 0.186.1 (including addons), MIT license.\n\n'+await readFile(new URL('./node_modules/three/LICENSE',import.meta.url),'utf8'));
