import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { FolioCard, FolioHome } from '../../../../services/api/folio';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { FolioHomeView } from '.';

function card(id: string, title: string, extra: Partial<FolioCard> = {}): FolioCard {
  return {
    id,
    kind: 'blog_post',
    title,
    slug: title.toLowerCase().replace(/ /g, '-'),
    icon: null,
    cover_asset_id: null,
    space: 'eng',
    space_name: 'Ingeniería',
    description: `About ${title}`,
    doc_type: null,
    labels: [],
    author: 'fernando',
    author_name: 'Fernando',
    published_at: '2026-10-20T10:00:00Z',
    reading_minutes: 6,
    status: 'published',
    ...extra,
  };
}

const HOME: FolioHome = {
  can_write: false,
  featured: card('n1', 'Welcome to Radicle', { kind: 'page', doc_type: 'get-started' }),
  announcement: card('n2', 'V1 ships in November'),
  ai_tools: [card('n3', 'Connect Claude over MCP', { space: 'ai-tools', space_name: 'AI Tools' })],
  latest_posts: [card('n4', 'Weekly changes')],
  spaces: [{ key: 'eng', name: 'Ingeniería', kind: 'team', icon: null, docs: 3 }],
  most_read: [card('n1', 'Welcome to Radicle'), card('n4', 'Weekly changes')],
};

describe('FolioHomeView', () => {
  it('renders every block of the bento', async () => {
    mockFetch({ 'GET /api/v1/folio/home': { status: 200, body: HOME } });
    renderWithProviders(<FolioHomeView />);
    const featured = await screen.findByRole('link', { name: 'Welcome to Radicle' });
    expect(featured).toHaveAttribute('href', '/folio/p/n1-welcome-to-radicle');
    expect(screen.getByText('get-started')).toBeInTheDocument();
    expect(screen.getByText('Fernando · Ingeniería · 6 min read')).toBeInTheDocument();
    expect(screen.getByRole('article', { name: 'Announcement' })).toHaveTextContent(
      'V1 ships in November',
    );
    expect(screen.getByRole('link', { name: 'Read Connect Claude over MCP' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Write' })).not.toBeInTheDocument();
  });

  it('lists the latest posts, the most read and the spaces', async () => {
    mockFetch({ 'GET /api/v1/folio/home': { status: 200, body: HOME } });
    renderWithProviders(<FolioHomeView />);
    const latest = await screen.findByRole('region', { name: 'Latest posts' });
    expect(latest).toHaveTextContent('Blog post');
    expect(latest).toHaveTextContent('Weekly changes');
    const mostRead = screen.getByRole('region', { name: 'Most read' });
    expect(mostRead).toHaveTextContent('01Welcome to Radicle');
    expect(mostRead).toHaveTextContent('02Weekly changes');
    expect(screen.getByRole('link', { name: /Ingeniería.*3 docs/ })).toHaveAttribute(
      'href',
      '/folio/s/eng',
    );
  });

  it('says so when nothing is published', async () => {
    const empty = { ...HOME, featured: null, announcement: null, ai_tools: [], most_read: [] };
    mockFetch({
      'GET /api/v1/folio/home': {
        status: 200,
        body: { ...empty, latest_posts: [], can_write: true },
      },
    });
    renderWithProviders(<FolioHomeView />);
    expect(await screen.findByText('Folio is waiting for its first doc')).toBeInTheDocument();
    expect(screen.getByText('Press Write to publish the first one.')).toBeInTheDocument();
  });
});
