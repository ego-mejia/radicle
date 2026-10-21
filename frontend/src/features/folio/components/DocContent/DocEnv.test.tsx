import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { DocEnvContext } from './env';
import { b, doc, p } from './testDoc';
import { DocContent } from '.';

const page = doc(
  p({ type: 'ticket', attrs: { key: 'PA-4' } }),
  b('image', { assetId: 'a1', alt: 'Diagrama' }),
  b('file', { assetId: 'f1', name: 'guia.pdf', size: 2048 }),
  b('pageList', { label: 'mcp' }),
  b('embed', { url: 'https://example.com/doc', title: 'Un doc' }),
  b('childPages', {}),
);
const children = [{ id: 'c1', title: 'Hija', slug: 'hija' }];

describe('DocContent read through a public link', () => {
  it('serves files through the link and asks the API for nothing', async () => {
    const calls = mockFetch({});
    renderWithProviders(
      <DocEnvContext.Provider
        value={{
          assetUrl: (id) => `/pub/tok/assets/${id}`,
          isPublic: true,
          pageLink: (c) => <a href={`/pub/tok/${c.id}`}>{c.title}</a>,
        }}
      >
        <DocContent doc={page} childPages={children} />
      </DocEnvContext.Provider>,
    );
    expect(await screen.findByAltText('Diagrama')).toHaveAttribute('src', '/pub/tok/assets/a1');
    expect(screen.getByRole('link', { name: /guia\.pdf/ })).toHaveAttribute(
      'href',
      '/pub/tok/assets/f1',
    );
    expect(screen.getByText('PA-4')).toBeVisible();
    expect(screen.getByRole('note')).toHaveTextContent(/open it in Radicle/);
    expect(screen.getByRole('link', { name: /Un doc/ })).toHaveAttribute(
      'href',
      'https://example.com/doc',
    );
    expect(screen.getByRole('link', { name: 'Hija' })).toHaveAttribute('href', '/pub/tok/c1');
    await new Promise((r) => setTimeout(r, 20));
    expect(calls).toEqual([]);
  });
});
