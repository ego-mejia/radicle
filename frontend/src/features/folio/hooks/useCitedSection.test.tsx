import { act, screen } from '@testing-library/react';
import {
  createMemoryHistory,
  createRootRoute,
  createRouter,
  RouterProvider,
} from '@tanstack/react-router';
import { render } from '@testing-library/react';
import { useRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useCitedSection } from './useCitedSection';

function Doc() {
  const ref = useRef<HTMLDivElement>(null);
  useCitedSection(ref, 1);
  return (
    <div ref={ref}>
      <h2 id="intro">Intro</h2>
      <p>Hola.</p>
      <h2 id="conecta-un-agente">Conecta un agente</h2>
      <p>Ve a Admin, Agentes.</p>
      <p>Luego copia el token.</p>
    </div>
  );
}

function renderAt(url: string) {
  const router = createRouter({
    routeTree: createRootRoute({ component: Doc }),
    history: createMemoryHistory({ initialEntries: [url] }),
  });
  return render(<RouterProvider router={router} />);
}

afterEach(() => vi.useRealTimers());

describe('useCitedSection', () => {
  it('marks the cited heading and its first paragraph for a few seconds', async () => {
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    vi.useFakeTimers({ shouldAdvanceTime: true });
    renderAt('/folio/p/x#conecta-un-agente');
    const heading = await screen.findByRole('heading', { name: 'Conecta un agente' });
    expect(heading.dataset.cited).toBe('true');
    expect(screen.getByText('Ve a Admin, Agentes.').dataset.cited).toBe('true');
    expect(screen.getByText('Luego copia el token.').dataset.cited).toBeUndefined();
    expect(screen.getByText('Intro').dataset.cited).toBeUndefined();
    expect(scroll).toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(6000));
    expect(heading.dataset.cited).toBeUndefined();
  });

  it('does nothing without a hash or with an unknown one', async () => {
    renderAt('/folio/p/x#nada');
    await screen.findByText('Intro');
    expect(document.querySelector('[data-cited]')).toBeNull();
  });
});
