import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../../../test/renderWithProviders';
import type { FolioImport } from '../../../../../../services/api/folioImports';
import { ImportOutcome } from '.';

const base = {
  id: 'i1',
  source: 'markdown',
  space: 'eng',
  filename: 'docs.zip',
  options: {},
  created_at: '2026-10-21T10:00:00Z',
  finished_at: null,
} as const;

describe('ImportOutcome', () => {
  it('lists what each page became', async () => {
    mockFetch({});
    const item = {
      ...base,
      status: 'done',
      stats: { created: 1, updated: 0, published: 1, drafts: 1, failed: 1 },
      report: {
        run: [
          {
            external_id: 'a',
            title: 'Guía',
            action: 'created',
            node_id: 'n1',
            published: true,
            errors: [],
          },
          {
            external_id: 'b',
            title: 'Corta',
            action: 'created',
            node_id: 'n2',
            published: false,
            missing: ['description'],
            errors: [],
          },
          { external_id: 'c', title: 'Rota', action: 'failed', errors: ['The file is empty.'] },
        ],
      },
    } as unknown as FolioImport;
    renderWithProviders(<ImportOutcome item={item} />);
    expect(await screen.findByRole('link', { name: 'Guía' })).toHaveAttribute(
      'href',
      '/folio/p/n1',
    );
    expect(screen.getAllByText('published')).toHaveLength(2); // the total and Guía
    expect(screen.getByText('draft: missing description')).toBeInTheDocument();
    expect(screen.getByText('Rota').tagName).toBe('SPAN');
    expect(screen.getByText('The file is empty.')).toBeInTheDocument();
  });

  it('says when it runs and why it stopped', async () => {
    mockFetch({});
    const running = { ...base, status: 'running', stats: {}, report: {} } as unknown as FolioImport;
    const { unmount } = renderWithProviders(<ImportOutcome item={running} />);
    expect(await screen.findByText('Importing…')).toBeInTheDocument();
    unmount();
    const failed = {
      ...base,
      status: 'failed',
      stats: { error: 'The import stopped: storage is down' },
      report: {},
    } as unknown as FolioImport;
    renderWithProviders(<ImportOutcome item={failed} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('storage is down');
  });
});
