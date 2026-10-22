import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { block, card } from './fixtures';
import { HomeGrid } from '.';
import { inGridOrder } from './order';

vi.mock('../DocsChat', () => ({ DocsChat: () => <p>chat</p> }));
vi.mock('../CalendarEmbed', () => ({
  CalendarEmbed: (p: { calendarId: string; view: string }) => (
    <p>
      {p.calendarId} {p.view}
    </p>
  ),
}));

const SPACE = { key: 'eng', name: 'Ingeniería', kind: 'team' as const, icon: null, docs: 3 };

describe('HomeGrid', () => {
  it('draws each block type with what the API resolved', async () => {
    const { container } = renderWithProviders(
      <HomeGrid
        blocks={[
          block('featured', 0, 0, 7, { cards: [card('n1', 'Welcome', { doc_type: 'guide' })] }),
          block('announcement', 7, 0, 5, { cards: [card('n2', 'V1 ships')] }),
          block('posts', 0, 2, 4, { title: 'AI Tools', cards: [card('n3', 'MCP')] }),
          block('query', 4, 2, 4, { cards: [card('n4', 'Runbook')] }),
          block('for_you', 8, 2, 4, { cards: [card('n5', 'Followed')] }),
          block('most_read', 0, 4, 6, { cards: [card('n6', 'Popular')] }),
          block('spaces', 6, 4, 3, { spaces: [SPACE] }),
          block('text', 9, 4, 3, { title: 'Hello', markdown: '**Bienvenidos**' }),
          block('search', 0, 6, 12),
          block('chat', 0, 8, 12),
          block('calendar', 0, 12, 8, { calendar: 'c1', view: 'week' }),
        ]}
      />,
    );
    expect(await screen.findByRole('link', { name: 'Welcome' })).toHaveTextContent('guide');
    expect(screen.getByRole('article', { name: 'Announcement' })).toHaveTextContent('V1 ships');
    expect(screen.getByRole('region', { name: 'AI Tools' })).toHaveTextContent('MCP');
    expect(screen.getByRole('region', { name: 'Docs' })).toHaveTextContent('Runbook');
    expect(screen.getByRole('region', { name: 'For you' })).toHaveTextContent('Followed');
    expect(screen.getByRole('region', { name: 'Most read' })).toHaveTextContent('01Popular');
    expect(screen.getByRole('link', { name: /Ingeniería.*3 docs/ })).toHaveAttribute(
      'href',
      '/folio/s/eng',
    );
    expect(screen.getByRole('region', { name: 'Hello' }).querySelector('strong')).toHaveTextContent(
      'Bienvenidos',
    );
    expect(screen.getByRole('search', { name: 'Search the docs' })).toBeInTheDocument();
    expect(container.querySelector('[data-block="chat"]')).toHaveTextContent('chat');
    expect(container.querySelector('[data-block="calendar"]')).toHaveTextContent('c1 week');
  });

  it('lays blocks out top to bottom, then left to right', async () => {
    const order = inGridOrder([block('a', 6, 4, 6), block('b', 0, 4, 6), block('c', 0, 0, 12)]);
    expect(order.map((b) => b.type)).toEqual(['c', 'b', 'a']);
    renderWithProviders(
      <HomeGrid
        blocks={[
          block('text', 6, 4, 6, { title: 'Right', markdown: 'r' }),
          block('text', 0, 0, 12, { title: 'Top', markdown: 't' }),
          block('text', 0, 4, 6, { title: 'Left', markdown: 'l' }),
        ]}
      />,
    );
    const names = (await screen.findAllByRole('region')).map((r) => r.getAttribute('aria-label'));
    expect(names).toEqual(['Top', 'Left', 'Right']);
  });
});
