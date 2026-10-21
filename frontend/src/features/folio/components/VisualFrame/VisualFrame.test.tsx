import { act, fireEvent, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useThemeMode } from '../../../../hooks/useThemeMode';
import { darkTheme, lightTheme } from '../../../../styles/theme';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { VisualFrame } from '.';
import { THEME_MESSAGE, VISUAL_CSP } from './visualDocument';

const SVG = '<svg viewBox="0 0 10 10"><rect fill="var(--rdc-accent)"/></svg>';

function Switch() {
  const { setPreference } = useThemeMode();
  return <button onClick={() => setPreference('dark')}>dark</button>;
}

async function frame(): Promise<HTMLIFrameElement> {
  return (await screen.findByTitle('Raíz')) as HTMLIFrameElement;
}

describe('VisualFrame', () => {
  it('runs the code sandboxed, without the page origin, and with no network', async () => {
    renderWithProviders(<VisualFrame code={SVG} title="Raíz" description="Un cuadro lima" />);
    const iframe = await frame();
    // allow-same-origin would give it Folio's cookies, storage and DOM.
    expect(iframe.getAttribute('sandbox')).toBe('allow-scripts');
    expect(iframe).toHaveAttribute('referrerpolicy', 'no-referrer');
    const doc = iframe.getAttribute('srcdoc') ?? '';
    expect(VISUAL_CSP).toContain("default-src 'none'");
    // The policy comes before anything the visual brings.
    expect(doc.indexOf(`content="${VISUAL_CSP}"`)).toBeGreaterThan(0);
    expect(doc.indexOf('Content-Security-Policy')).toBeLessThan(doc.indexOf(SVG));
    expect(doc).toContain(`--rdc-accent:${lightTheme.color.accent}`);
    expect(screen.getByText('Un cuadro lima')).toHaveAttribute(
      'id',
      iframe.getAttribute('aria-describedby'),
    );
  });

  it('switches theme by message, without reloading the visual', async () => {
    renderWithProviders(
      <>
        <Switch />
        <VisualFrame code={SVG} title="Raíz" description="Un cuadro lima" />
      </>,
    );
    const iframe = await frame();
    const before = iframe.getAttribute('srcdoc');
    const post = vi.spyOn(iframe.contentWindow as Window, 'postMessage');
    fireEvent.click(screen.getByRole('button', { name: 'dark' }));
    expect(iframe.getAttribute('srcdoc')).toBe(before);
    const sent = post.mock.calls.at(-1)?.[0] as {
      type: string;
      mode: string;
      tokens: Record<string, string>;
    };
    expect(sent.type).toBe(THEME_MESSAGE);
    expect(sent.mode).toBe('dark');
    expect(sent.tokens['--rdc-text']).toBe(darkTheme.color.text);
  });

  it('follows the height the visual reports, only from its own frame, up to 2,000 px', async () => {
    renderWithProviders(<VisualFrame code={SVG} title="Raíz" description="Un cuadro lima" />);
    const iframe = await frame();
    const report = (height: number, source: MessageEventSource | null) =>
      act(() => {
        window.dispatchEvent(
          new MessageEvent('message', { data: { type: 'radicle:height', height }, source }),
        );
      });
    report(320, iframe.contentWindow);
    expect(iframe.style.height).toBe('320px');
    report(900, window); // another frame can't resize it
    expect(iframe.style.height).toBe('320px');
    report(99_999, iframe.contentWindow);
    expect(iframe.style.height).toBe('2000px');
  });

  it('can preview the other mode', async () => {
    renderWithProviders(<VisualFrame code={SVG} title="Raíz" description="x" mode="dark" />);
    const doc = (await frame()).getAttribute('srcdoc') ?? '';
    expect(doc).toContain(`--rdc-bg:${darkTheme.color.bg}`);
    expect(doc).toContain(`--rdc-on-accent:${darkTheme.color.onAccent}`);
    // The frame's color-scheme follows the theme, or Chrome paints it white in dark mode.
    expect(doc).toContain('<html data-theme="dark"');
    expect(doc).toContain(':root[data-theme="dark"]{color-scheme:dark}');
  });
});
