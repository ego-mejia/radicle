// Deep-merge a JSON fragment into a locale file: node scripts/merge-locale.mjs <locale> <fragment.json>
import { readFileSync, writeFileSync } from 'node:fs';

const [locale, fragmentPath] = process.argv.slice(2);
const file = new URL(`../src/i18n/locales/${locale}.json`, import.meta.url);
const merge = (a, b) => {
  for (const [k, v] of Object.entries(b)) {
    a[k] = v && typeof v === 'object' && !Array.isArray(v) ? merge(a[k] ?? {}, v) : v;
  }
  return a;
};
const current = JSON.parse(readFileSync(file, 'utf8'));
writeFileSync(
  file,
  JSON.stringify(merge(current, JSON.parse(readFileSync(fragmentPath, 'utf8'))), null, 2) + '\n',
);
