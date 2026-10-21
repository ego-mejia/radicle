import i18n from 'i18next';
import { describe, expect, it } from 'vitest';
import '../../../../i18n';
import { columnName, viewName } from './labels';

describe('default database names', () => {
  it('shows the untouched defaults in the reader language', async () => {
    await i18n.changeLanguage('es');
    expect(viewName({ id: 'table', name: 'Table' }, i18n.t)).toBe('Tabla');
    expect(columnName({ key: 'name', name: 'Name' }, i18n.t)).toBe('Nombre');
  });

  it('keeps names someone chose', async () => {
    await i18n.changeLanguage('es');
    expect(viewName({ id: 'table', name: 'Inventario' }, i18n.t)).toBe('Inventario');
    expect(viewName({ id: 'board', name: 'Table' }, i18n.t)).toBe('Table');
    expect(columnName({ key: 'herramienta', name: 'Name' }, i18n.t)).toBe('Name');
  });
});
