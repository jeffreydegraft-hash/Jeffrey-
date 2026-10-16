/* Run Shopify Theme Check on a theme folder; print offenses for the files given (or all). */
import path from 'node:path';
import { themeCheckRun } from '@shopify/theme-check-node';
const [root, ...only] = process.argv.slice(2);
const res = await themeCheckRun(path.resolve(root), undefined, (m) => {});
const offenses = res.offenses || res;
const want = only.map((f) => path.resolve(root, f));
let n = 0;
for (const o of offenses) {
  const file = o.uri.replace('file://', '');
  if (want.length && !want.includes(file)) continue;
  n++;
  console.log(`${['ERROR', 'WARN', 'INFO'][o.severity] || o.severity} ${path.relative(path.resolve(root), file)}:${o.start?.line + 1} ${o.check}: ${o.message}`);
}
console.log(`${n} offense(s)${want.length ? ' in checked files' : ''} of ${offenses.length} total`);
