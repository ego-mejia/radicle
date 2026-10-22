import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { FolioSpace } from '../../../../services/api/folio';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SpaceHero } from '.';

const SPACE = {
  id: 's1',
  key: 'eng',
  name: 'Ingeniería',
  description: 'Cómo construimos Radicle.',
  kind: 'team',
  icon: null,
  cover_asset_id: null,
  created_at: '2026-10-01T00:00:00Z',
  permissions: ['view', 'create', 'admin'],
  verify_days: 90,
  ai_enabled: true,
  show_readers: false,
} as FolioSpace;

const OVERVIEW = {
  pages: 12,
  folders: 3,
  sections: [
    { key: 'specs', doc_types: ['build-spec'], visible: true, count: 5 },
    { key: 'decisions', doc_types: ['decision-log'], visible: true, count: 3 },
    { key: 'guides', doc_types: ['how-to'], visible: false, count: 4 },
    { key: 'docs', doc_types: ['reference'], visible: true, count: 0 },
  ],
  participants: [{ handle: 'fernando', name: 'Fernando', kind: 'human', role: 'admin' }],
  everyone_role: 'reader',
};

function mock() {
  return mockFetch({
    'GET /api/v1/folio/spaces/eng/overview': { status: 200, body: OVERVIEW },
    'GET /api/v1/folio/watch/space/s1': { status: 200, body: { watching: false } },
    'PUT /api/v1/folio/watch/space/s1': { status: 204, body: null },
  });
}

describe('SpaceHero', () => {
  it('shows the space, its counts, people and the visible sections', async () => {
    const calls = mock();
    renderWithProviders(<SpaceHero space={SPACE} active="all" onWrite={() => undefined} />);
    expect(await screen.findByRole('heading', { name: 'Ingeniería' })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: /Specs 5/ })).toHaveAttribute(
      'href',
      '/folio/s/eng/specs',
    );
    expect(screen.queryByRole('link', { name: /Guides/ })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /All 8/ })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Manage' })).toHaveAttribute(
      'href',
      '/folio/s/eng/admin',
    );
    await userEvent.click(screen.getByRole('button', { name: /Follow/ }));
    expect(calls.some((c) => c.method === 'PUT' && c.path.includes('/watch/space/s1'))).toBe(true);
  });

  it('in a section, shows the path back and searches inside it', async () => {
    mock();
    const typed: string[] = [];
    renderWithProviders(
      <SpaceHero space={SPACE} active="decisions" onSearch={(q) => typed.push(q)} />,
    );
    expect(
      await screen.findByRole('heading', { name: 'Architecture decisions' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ingeniería' })).toHaveAttribute(
      'href',
      '/folio/s/eng',
    );
    await userEvent.type(screen.getByRole('searchbox'), 'pg');
    expect(typed.at(-1)).toBe('pg');
    expect(screen.queryByRole('button', { name: /Follow/ })).not.toBeInTheDocument();
  });
});
