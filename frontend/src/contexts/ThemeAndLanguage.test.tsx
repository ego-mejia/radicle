import { act, screen } from '@testing-library/react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'styled-components';
import { beforeEach, describe, expect, it } from 'vitest';
import { useThemeMode } from '../hooks/useThemeMode';
import i18n from '../i18n';
import { renderWithProviders } from '../test/renderWithProviders';

function Probe() {
  const { t } = useTranslation();
  const { mode, setPreference } = useThemeMode();
  const theme = useTheme();
  return (
    <div>
      <span data-testid="label">{t('nav.createTicket')}</span>
      <span data-testid="mode">{mode}</span>
      <span data-testid="bg">{theme.color.bg}</span>
      <button onClick={() => setPreference(mode === 'dark' ? 'light' : 'dark')}>toggle</button>
    </div>
  );
}

describe('theme and language', () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage('en');
  });

  it('switches between English and Spanish', async () => {
    renderWithProviders(<Probe />);
    expect(await screen.findByTestId('label')).toHaveTextContent('Create ticket');
    await act(() => i18n.changeLanguage('es'));
    expect(screen.getByTestId('label')).toHaveTextContent('Crear ticket');
    expect(document.documentElement.lang).toBe('es');
  });

  it('switches to the dark lime palette and remembers it', async () => {
    renderWithProviders(<Probe />);
    const button = await screen.findByRole('button', { name: 'toggle' });
    const before = screen.getByTestId('mode').textContent;
    await act(async () => button.click());
    const after = screen.getByTestId('mode').textContent;
    expect(after).not.toBe(before);
    expect(screen.getByTestId('bg')).toHaveTextContent(after === 'dark' ? '#0E0F11' : '#F5F6F8');
    expect(localStorage.getItem('radicle.theme')).toBe(after);
  });

  it('has every English key in Spanish', async () => {
    const en = await import('../i18n/locales/en.json');
    const es = await import('../i18n/locales/es.json');
    const keys = (obj: object, prefix = ''): string[] =>
      Object.entries(obj).flatMap(([k, v]) =>
        v && typeof v === 'object' ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
      );
    expect(keys(es.default).sort()).toEqual(keys(en.default).sort());
  });
});
