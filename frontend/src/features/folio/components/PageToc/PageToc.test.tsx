import { act, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { PageToc } from '.';

const HEADINGS = [
  { level: 1, text: 'Antes de empezar', anchor: 'antes-de-empezar' },
  { level: 2, text: 'Crea el agente', anchor: 'crea-el-agente' },
];

type Callback = (entries: { isIntersecting: boolean; target: Element }[]) => void;

describe('PageToc', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('links every section and follows the one being read', async () => {
    let notify: Callback = () => {};
    vi.stubGlobal(
      'IntersectionObserver',
      class {
        constructor(callback: Callback) {
          notify = callback;
        }
        observe() {}
        disconnect() {}
      },
    );
    renderWithProviders(
      <>
        <h2 id="antes-de-empezar">Antes de empezar</h2>
        <h3 id="crea-el-agente">Crea el agente</h3>
        <PageToc headings={HEADINGS} />
      </>,
    );
    const toc = await screen.findByRole('navigation', { name: 'On this page' });
    const first = within(toc).getByRole('link', { name: 'Antes de empezar' });
    const second = within(toc).getByRole('link', { name: 'Crea el agente' });
    expect(second).toHaveAttribute('href', '#crea-el-agente');
    expect(first).toHaveAttribute('aria-current', 'location');
    act(() => {
      notify([
        { isIntersecting: false, target: document.getElementById('antes-de-empezar')! },
        { isIntersecting: true, target: document.getElementById('crea-el-agente')! },
      ]);
    });
    expect(second).toHaveAttribute('aria-current', 'location');
    expect(first).not.toHaveAttribute('aria-current');
  });

  it('renders nothing for a page without sections', async () => {
    renderWithProviders(
      <>
        <p>Sin secciones</p>
        <PageToc headings={[]} />
      </>,
    );
    expect(await screen.findByText('Sin secciones')).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).toBeNull();
  });
});
