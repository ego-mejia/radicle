import { beforeEach, describe, expect, it } from 'vitest';
import { migrateLegacyStorage } from './legacyStorage';

describe('migrateLegacyStorage', () => {
  beforeEach(() => localStorage.clear());

  it('moves pre-rename keys to their new names', () => {
    localStorage.setItem('radicle.theme', 'dark');
    localStorage.setItem('radicle:celebrated:PA:m1', '1');
    localStorage.setItem('other', 'x');
    migrateLegacyStorage(localStorage);
    expect(localStorage.getItem('gumball-factory.theme')).toBe('dark');
    expect(localStorage.getItem('gumball-factory:celebrated:PA:m1')).toBe('1');
    expect(localStorage.getItem('radicle.theme')).toBeNull();
    expect(localStorage.getItem('other')).toBe('x');
  });

  it('keeps a value already saved under the new name', () => {
    localStorage.setItem('radicle.lang', 'en');
    localStorage.setItem('gumball-factory.lang', 'es');
    migrateLegacyStorage(localStorage);
    expect(localStorage.getItem('gumball-factory.lang')).toBe('es');
    expect(localStorage.getItem('radicle.lang')).toBeNull();
  });
});
