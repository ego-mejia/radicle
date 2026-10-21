import { fireEvent, screen, waitFor } from '@testing-library/react';
import { useRef } from 'react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { GlossaryTooltips } from '.';

const TERMS = [
  {
    id: 't1',
    term: 'Docket',
    aliases: [],
    definition: 'El tracker de tickets de Radicle.',
    status: 'approved',
    source: { id: '9f3c0000-0000-4000-8000-000000000001', title: 'Guía de Docket', slug: 'guia' },
    updated_at: '2026-10-21T10:00:00Z',
  },
];

// jsdom has no layout: every range sits at (10, 10) to (60, 30).
const rect = { left: 10, right: 60, top: 10, bottom: 30, width: 50, height: 20, x: 10, y: 10 };
const original = {
  rects: Range.prototype.getClientRects,
  box: Range.prototype.getBoundingClientRect,
};
beforeEach(() => {
  Range.prototype.getClientRects = () => [rect] as unknown as DOMRectList;
  Range.prototype.getBoundingClientRect = () => rect as DOMRect;
});
afterEach(() => {
  Range.prototype.getClientRects = original.rects;
  Range.prototype.getBoundingClientRect = original.box;
});

function Page() {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <>
      <div ref={ref} data-testid="content">
        <p>Abre Docket para ver tus tickets.</p>
      </div>
      <GlossaryTooltips container={ref} version={1} />
    </>
  );
}

describe('GlossaryTooltips', () => {
  it('shows an approved term with its definition and source on hover', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/glossary': { status: 200, body: { items: TERMS } },
    });
    renderWithProviders(<Page />);
    const content = await screen.findByTestId('content');
    await waitFor(() => expect(calls.some((c) => c.path === '/api/v1/folio/glossary')).toBe(true));
    await waitFor(() => {
      fireEvent.mouseMove(content, { clientX: 20, clientY: 20 });
      expect(screen.getByRole('tooltip')).toBeInTheDocument();
    });
    expect(screen.getByRole('tooltip')).toHaveTextContent('El tracker de tickets de Radicle.');
    expect(screen.getByRole('link', { name: 'Source: Guía de Docket' })).toHaveAttribute(
      'href',
      '/folio/p/9f3c0000-0000-4000-8000-000000000001-guia',
    );
    fireEvent.mouseLeave(screen.getByRole('tooltip'));
    expect(screen.queryByRole('tooltip')).toBeNull();
  });

  it('shows nothing away from the terms', async () => {
    mockFetch({ 'GET /api/v1/folio/glossary': { status: 200, body: { items: TERMS } } });
    renderWithProviders(<Page />);
    const content = await screen.findByTestId('content');
    await new Promise((r) => setTimeout(r, 20));
    fireEvent.mouseMove(content, { clientX: 300, clientY: 300 });
    expect(screen.queryByRole('tooltip')).toBeNull();
  });
});
