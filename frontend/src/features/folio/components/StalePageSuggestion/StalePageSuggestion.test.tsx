import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import type { FolioNode } from '../../../../services/api/folio';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { StalePageSuggestion } from '.';

const NODE = {
  id: '11111111-1111-1111-1111-111111111111',
  slug: 'automatizacion',
  title: 'Automatización',
  status: 'outdated',
  can_edit: true,
  version: 3,
  verified_until: '2026-08-01',
} as unknown as FolioNode;

beforeEach(() => window.localStorage.clear());

describe('StalePageSuggestion', () => {
  it('tells an editor the page went stale and how to update it', async () => {
    renderWithProviders(<StalePageSuggestion node={NODE} />);
    expect(await screen.findByText('This page went stale.')).toBeInTheDocument();
    expect(screen.getByText(/Its verification expired on Aug 1, 2026/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Update it' })).toHaveAttribute(
      'href',
      `/folio/p/${NODE.id}-automatizacion/edit`,
    );
    expect(screen.getByRole('link', { name: 'See changes' })).toBeInTheDocument();
  });

  it('remembers a dismissal until the next version', async () => {
    const { unmount } = renderWithProviders(<StalePageSuggestion node={NODE} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Dismiss' }));
    expect(screen.queryByText('This page went stale.')).toBeNull();
    unmount();
    renderWithProviders(<StalePageSuggestion node={{ ...NODE, version: 4 }} />);
    expect(await screen.findByText('This page went stale.')).toBeInTheDocument();
  });

  it('stays quiet for readers and for pages that are fine', async () => {
    renderWithProviders(
      <>
        <StalePageSuggestion node={{ ...NODE, can_edit: false }} />
        <StalePageSuggestion node={{ ...NODE, status: 'verified' } as FolioNode} />
        <p>listo</p>
      </>,
    );
    await screen.findByText('listo');
    expect(screen.queryByText('This page went stale.')).toBeNull();
  });
});
