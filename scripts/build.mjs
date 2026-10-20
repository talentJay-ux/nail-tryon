import {readFileSync,writeFileSync} from 'node:fs';
const page=new URL('../index.html',import.meta.url);
const source=readFileSync(new URL('postprocess.js',import.meta.url),'utf8').replace(/\nif\(typeof module[^\n]+\n?$/,'');
const html=readFileSync(page,'utf8').replace(/\/\* BEGIN DECODER \*\/[\s\S]*?\/\* END DECODER \*\//,`/* BEGIN DECODER */\n${source}/* END DECODER */`);
writeFileSync(page,html);
