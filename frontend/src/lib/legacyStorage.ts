// Before the rename to Gumball Factory (ADR 0046) local preferences were saved under
// "radicle." and "radicle:" keys. Copy them once to the new names so nobody loses their
// theme, language or board lanes. Imported first in main.tsx, before i18n reads its key.
const PREFIXES: [string, string][] = [
  ['radicle.', 'gumball-factory.'],
  ['radicle:', 'gumball-factory:'],
];

export function migrateLegacyStorage(storage: Storage): void {
  const keys = Array.from({ length: storage.length }, (_, i) => storage.key(i)).filter(
    (key): key is string => key !== null,
  );
  for (const key of keys) {
    const match = PREFIXES.find(([old]) => key.startsWith(old));
    if (!match) continue;
    const renamed = match[1] + key.slice(match[0].length);
    if (storage.getItem(renamed) === null) storage.setItem(renamed, storage.getItem(key) ?? '');
    storage.removeItem(key);
  }
}

try {
  migrateLegacyStorage(window.localStorage);
} catch {
  // Storage blocked (private mode, sandbox): nothing to migrate.
}
