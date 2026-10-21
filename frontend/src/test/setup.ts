import '@testing-library/jest-dom/vitest';
import '../i18n';

// Node 25 ships a global `localStorage` that shadows jsdom's and is unusable without
// --localstorage-file. Swap in an in-memory Storage when that happens.
if (typeof globalThis.localStorage?.clear !== 'function') {
  const store = new Map<string, string>();
  const memoryStorage: Storage = {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key) => store.get(key) ?? null,
    key: (index) => [...store.keys()][index] ?? null,
    removeItem: (key) => void store.delete(key),
    setItem: (key, value) => void store.set(key, String(value)),
  };
  Object.defineProperty(globalThis, 'localStorage', { value: memoryStorage, configurable: true });
}

// jsdom does not implement scrolling; the router calls it on navigation.
window.scrollTo = () => undefined;

// jsdom has no layout. CodeMirror measures text ranges when the cursor moves; an empty
// answer lets editors take typed text in tests.
if (typeof Range.prototype.getClientRects !== 'function') {
  const empty = Object.assign([] as DOMRect[], { item: () => null }) as unknown as DOMRectList;
  Range.prototype.getClientRects = () => empty;
  Range.prototype.getBoundingClientRect = () => new DOMRect(0, 0, 0, 0);
}
