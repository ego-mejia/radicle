import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SpaceSectionsEditor } from '.';

const OVERVIEW = {
  pages: 3,
  folders: 0,
  sections: [
    { key: 'specs', doc_types: ['build-spec'], visible: true, count: 2 },
    { key: 'decisions', doc_types: ['decision-log'], visible: true, count: 1 },
    { key: 'guides', doc_types: ['how-to'], visible: true, count: 0 },
    { key: 'docs', doc_types: ['reference'], visible: true, count: 0 },
  ],
  participants: [],
  everyone_role: null,
};

describe('SpaceSectionsEditor', () => {
  it('hides and reorders sections, then saves them in order', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/spaces/eng/overview': { status: 200, body: OVERVIEW },
      'PUT /api/v1/folio/spaces/eng/sections': { status: 200, body: OVERVIEW.sections },
    });
    renderWithProviders(<SpaceSectionsEditor space="eng" />);
    await userEvent.click(await screen.findByLabelText('Docs'));
    await userEvent.click(screen.getByRole('button', { name: 'Move Guides up' }));
    await userEvent.click(screen.getByRole('button', { name: 'Save sections' }));
    const put = calls.find((c) => c.method === 'PUT');
    expect(put?.body).toEqual({
      sections: [
        { key: 'specs', visible: true },
        { key: 'guides', visible: true },
        { key: 'decisions', visible: true },
        { key: 'docs', visible: false },
      ],
    });
  });

  it('shows why saving failed', async () => {
    mockFetch({
      'GET /api/v1/folio/spaces/eng/overview': { status: 200, body: OVERVIEW },
      'PUT /api/v1/folio/spaces/eng/sections': {
        status: 403,
        body: { status: 403, detail: 'Only the admins of Ingeniería can change it.', errors: [] },
      },
    });
    renderWithProviders(<SpaceSectionsEditor space="eng" />);
    await userEvent.click(await screen.findByRole('button', { name: 'Save sections' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Only the admins');
  });
});
