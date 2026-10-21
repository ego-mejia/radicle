import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { FolioHome } from '../../../../services/api/folio';
import { block, card } from '../../components/HomeGrid/fixtures';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { FolioHomeView } from '.';

const HOME: FolioHome = {
  can_write: false,
  featured: null,
  announcement: null,
  ai_tools: [],
  latest_posts: [],
  spaces: [],
  most_read: [],
  blocks: [
    block('featured', 0, 0, 7, { cards: [card('n1', 'Welcome to Radicle', { kind: 'page' })] }),
    block('announcement', 7, 0, 5, { cards: [card('n2', 'V1 ships in November')] }),
    block('posts', 0, 4, 5, { cards: [card('n4', 'Weekly changes')] }),
  ],
};

describe('FolioHomeView', () => {
  it('renders the published layout from the API', async () => {
    mockFetch({ 'GET /api/v1/folio/home': { status: 200, body: HOME } });
    renderWithProviders(<FolioHomeView />);
    const featured = await screen.findByRole('link', { name: 'Welcome to Radicle' });
    expect(featured).toHaveAttribute('href', '/folio/p/n1-welcome-to-radicle');
    expect(screen.getByRole('article', { name: 'Announcement' })).toHaveTextContent(
      'V1 ships in November',
    );
    expect(screen.getByRole('region', { name: 'Latest posts' })).toHaveTextContent(
      'Weekly changes',
    );
    expect(screen.queryByRole('button', { name: 'Write' })).not.toBeInTheDocument();
  });

  it('says so when nothing is published', async () => {
    const body = { ...HOME, can_write: true, blocks: [block('search', 0, 0, 12)] };
    mockFetch({ 'GET /api/v1/folio/home': { status: 200, body } });
    renderWithProviders(<FolioHomeView />);
    expect(await screen.findByText('Folio is waiting for its first doc')).toBeInTheDocument();
    expect(screen.getByText('Press Write to publish the first one.')).toBeInTheDocument();
    expect(screen.getByRole('search', { name: 'Search the docs' })).toBeInTheDocument();
  });
});
