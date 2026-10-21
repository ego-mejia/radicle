import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../../../test/renderWithProviders';
import { block } from '../../../HomeGrid/fixtures';
import { HomePreview } from '.';

const TEXT = { id: 'txt', type: 'text', x: 0, y: 0, w: 12, h: 2, config: { markdown: 'Hola' } };

describe('HomePreview', () => {
  it('draws the unsaved layout the way the home does', async () => {
    const calls = mockFetch({
      'POST /api/v1/folio/admin/home/preview': {
        status: 200,
        body: { blocks: [block('text', 0, 0, 12, { title: 'Bienvenida', markdown: 'Hola' })] },
      },
    });
    renderWithProviders(<HomePreview blocks={[TEXT]} />);
    expect(await screen.findByRole('region', { name: 'Bienvenida' })).toHaveTextContent('Hola');
    expect(calls[0]?.body).toEqual({ columns: 12, blocks: [TEXT] });
  });

  it('says what is wrong with the layout', async () => {
    mockFetch({
      'POST /api/v1/folio/admin/home/preview': {
        status: 422,
        body: { status: 422, title: '', detail: 'The layout has problems: bad RQL', errors: [] },
      },
    });
    renderWithProviders(<HomePreview blocks={[TEXT]} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('The layout has problems: bad RQL');
  });
});
