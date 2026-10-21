import type { NodeViewProps } from '@tiptap/react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { toFolioDoc } from '../../editor/schema';
import { DB_ID, dbApi } from '../DatabaseView/fixtures';
import { DocContent } from '../DocContent';
import { DatabaseBlock } from '.';

const DOCS = {
  items: [{ id: DB_ID, title: 'Inventario', kind: 'database', space: 'ai-tools' }],
  next_cursor: null,
};

function block(attrs: { database: string | null; view: string | null }, selected = false) {
  const updateAttributes = vi.fn();
  const props = { node: { attrs }, updateAttributes, selected } as unknown as NodeViewProps;
  renderWithProviders(<DatabaseBlock {...props} />);
  return updateAttributes;
}

describe('DatabaseBlock', () => {
  it('asks which database, from those the author can see', async () => {
    const calls = dbApi(undefined, { 'GET /api/v1/folio/nodes': { status: 200, body: DOCS } });
    const update = block({ database: null, view: null });
    const picker = await screen.findByRole('combobox', { name: 'Database' });
    await screen.findByRole('option', { name: 'Inventario' });
    await userEvent.selectOptions(picker, 'Inventario');
    expect(update).toHaveBeenCalledWith({ database: DB_ID, view: null });
    expect(calls[0]?.path).toContain('kind');
  });

  it('once chosen, shows the view and, when selected, lets the author pick another', async () => {
    dbApi(undefined, { 'GET /api/v1/folio/nodes': { status: 200, body: DOCS } });
    const update = block({ database: DB_ID, view: null }, true);
    expect(await screen.findByText('Inventario', { selector: 'div' })).toBeInTheDocument();
    const views = await screen.findByRole('combobox', { name: 'View' });
    await userEvent.selectOptions(views, 'Board');
    expect(update).toHaveBeenCalledWith({ view: 'board' });
  });
});

describe('the databaseView block', () => {
  it('is saved only once it names a database', () => {
    const doc = {
      type: 'doc',
      content: [
        { type: 'databaseView', attrs: { database: null, view: null } },
        { type: 'databaseView', attrs: { database: DB_ID, view: null } },
      ],
    };
    expect(toFolioDoc(doc).content).toEqual([{ type: 'databaseView', attrs: { database: DB_ID } }]);
  });

  it('a reader without access sees a placeholder, not the rows', async () => {
    mockFetch({});
    renderWithProviders(
      <DocContent
        doc={{ type: 'doc', content: [{ type: 'databaseView', attrs: { database: DB_ID } }] }}
        childPages={[]}
      />,
    );
    await waitFor(() =>
      expect(screen.getByRole('note')).toHaveTextContent("You can't see this database."),
    );
  });
});
