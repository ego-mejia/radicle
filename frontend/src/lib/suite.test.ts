import { beforeEach, describe, expect, it } from 'vitest';
import { appOf, lastRoute, rememberRoute } from './suite';

describe('suite routes', () => {
  beforeEach(() => localStorage.clear());

  it('tells the app of a path', () => {
    expect(appOf('/folio')).toBe('folio');
    expect(appOf('/folio/admin')).toBe('folio');
    expect(appOf('/foliox')).toBe('docket');
    expect(appOf('/p/PA/board')).toBe('docket');
  });

  it('remembers the last page of each app per user', () => {
    expect(lastRoute('folio', 'luis')).toBe('/folio');
    rememberRoute('luis', '/p/PA/board?area=Legal');
    rememberRoute('luis', '/folio/admin');
    expect(lastRoute('docket', 'luis')).toBe('/p/PA/board?area=Legal');
    expect(lastRoute('folio', 'luis')).toBe('/folio/admin');
    expect(lastRoute('docket', 'ana')).toBe('/');
  });
});
