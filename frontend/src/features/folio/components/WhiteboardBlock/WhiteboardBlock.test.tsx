import type { NodeViewProps } from '@tiptap/react';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { toFolioDoc } from '../../editor/schema';
import { DocContent } from '../DocContent';
import { WhiteboardBlock } from '.';

// Excalidraw draws on a canvas jsdom doesn't have: a stand-in shows what it is given.
vi.mock('@excalidraw/excalidraw', () => ({
  Excalidraw: (props: {
    initialData: { elements: { id: string }[] };
    viewModeEnabled: boolean;
  }) => (
    <div data-testid="excalidraw" data-readonly={props.viewModeEnabled}>
      {props.initialData.elements.map((e) => e.id).join(',')}
    </div>
  ),
  CaptureUpdateAction: { NEVER: 'NEVER' },
  exportToBlob: vi.fn(),
  exportToSvg: vi.fn(),
}));

const WB = '0b7e2c41-5a3d-4f6e-9c8b-1d2e3f4a5b6c';
const DOCS = {
  items: [{ id: WB, title: 'Arquitectura', kind: 'whiteboard', space: 'docs' }],
  next_cursor: null,
};
const BOARD = {
  node_id: WB,
  title: 'Arquitectura',
  space: 'docs',
  can_edit: false,
  elements: [{ id: 'box', type: 'rectangle', version: 1, index: 'a0' }],
  updated_at: '2026-10-21T10:00:00Z',
};

function block(attrs: { whiteboard: string | null }, selected = false) {
  const updateAttributes = vi.fn();
  const props = { node: { attrs }, updateAttributes, selected } as unknown as NodeViewProps;
  renderWithProviders(<WhiteboardBlock {...props} />);
  return updateAttributes;
}

describe('WhiteboardBlock', () => {
  it('asks which whiteboard, from those the author can see', async () => {
    const calls = mockFetch({ 'GET /api/v1/folio/nodes': { status: 200, body: DOCS } });
    const update = block({ whiteboard: null });
    const picker = await screen.findByRole('combobox', { name: 'Choose a whiteboard' });
    await screen.findByRole('option', { name: 'Arquitectura' });
    await userEvent.selectOptions(picker, 'Arquitectura');
    expect(update).toHaveBeenCalledWith({ whiteboard: WB });
    expect(decodeURIComponent(calls[0]?.path ?? '')).toContain('kind = whiteboard');
  });

  it('is saved only once it names a whiteboard', () => {
    const doc = {
      type: 'doc',
      content: [
        { type: 'whiteboard', attrs: { whiteboard: null } },
        { type: 'whiteboard', attrs: { whiteboard: WB } },
      ],
    };
    expect(toFolioDoc(doc).content).toEqual([{ type: 'whiteboard', attrs: { whiteboard: WB } }]);
  });
});

describe('the whiteboard block for readers', () => {
  const doc = { type: 'doc', content: [{ type: 'whiteboard', attrs: { whiteboard: WB } }] };

  it('shows the scene read only, with a link to the whiteboard', async () => {
    mockFetch({ [`GET /api/v1/folio/whiteboards/${WB}`]: { status: 200, body: BOARD } });
    renderWithProviders(<DocContent doc={doc} />);
    const board = await screen.findByTestId('excalidraw');
    expect(board).toHaveTextContent('box');
    expect(board).toHaveAttribute('data-readonly', 'true');
    expect(screen.getByRole('link', { name: 'Arquitectura' })).toBeInTheDocument();
  });

  it('without access shows a placeholder', async () => {
    mockFetch({});
    renderWithProviders(<DocContent doc={doc} />);
    expect(await screen.findByRole('note')).toHaveTextContent("You can't see this whiteboard.");
    expect(screen.queryByTestId('excalidraw')).not.toBeInTheDocument();
  });
});
