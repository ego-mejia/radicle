import type { NodeViewProps } from '@tiptap/react';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { toFolioDoc } from '../../editor/schema';
import { DocContent } from '../DocContent';
import { COUNTDOWN } from './fixtures';
import { PluginBlockEditor } from '.';

const BLOCKS = { 'GET /api/v1/folio/plugin-blocks': { status: 200, body: { items: [COUNTDOWN] } } };
const ATTRS = { plugin: 'radicle.countdown', block: 'countdown' };

function block(data: Record<string, string> | null, selected = false) {
  const updateAttributes = vi.fn();
  const props = {
    node: { attrs: { ...ATTRS, data } },
    updateAttributes,
    selected,
  } as unknown as NodeViewProps;
  renderWithProviders(<PluginBlockEditor {...props} />);
  return updateAttributes;
}

describe('PluginBlockEditor', () => {
  it('asks for the fields a required value is missing from, and previews the block', async () => {
    mockFetch(BLOCKS);
    const update = block({ title: 'V1' });
    const date = await screen.findByLabelText('Fecha');
    await userEvent.type(date, '2026-12-15');
    expect(update).toHaveBeenLastCalledWith({ data: { title: 'V1', date: '2026-12-15' } });
    await userEvent.selectOptions(screen.getByLabelText('Tamaño (optional)'), 'M');
    expect(update).toHaveBeenLastCalledWith({ data: { title: 'V1', size: 'M' } });
    const frame = document.querySelector('iframe');
    expect(frame?.getAttribute('srcdoc')).toContain(
      'window.radicle={"data":{"title":"V1"},"lang":"en"}',
    );
    expect(frame).toHaveAttribute('sandbox', 'allow-scripts');
  });

  it('hides the fields once complete and not selected', async () => {
    mockFetch(BLOCKS);
    block({ date: '2026-12-15' });
    expect(await screen.findByTitle('Cuenta regresiva')).toBeInTheDocument();
    expect(screen.queryByLabelText('Fecha')).not.toBeInTheDocument();
  });

  it('is saved with its values', () => {
    const doc = {
      type: 'doc',
      content: [
        { type: 'pluginBlock', attrs: { plugin: null, block: null, data: null } },
        { type: 'pluginBlock', attrs: { ...ATTRS, data: { date: '2026-12-15' } } },
      ],
    };
    expect(toFolioDoc(doc).content).toEqual([
      { type: 'pluginBlock', attrs: { ...ATTRS, data: { date: '2026-12-15' } } },
    ]);
  });
});

describe('a plugin block for readers', () => {
  const doc = { type: 'doc', content: [{ type: 'pluginBlock', attrs: { ...ATTRS, data: {} } }] };

  it('draws it in the sandbox', async () => {
    mockFetch(BLOCKS);
    renderWithProviders(<DocContent doc={doc} />);
    expect(await screen.findByTitle('Cuenta regresiva')).toBeInTheDocument();
  });

  it('says the plugin is off when it is', async () => {
    mockFetch({ 'GET /api/v1/folio/plugin-blocks': { status: 200, body: { items: [] } } });
    renderWithProviders(<DocContent doc={doc} />);
    expect(await screen.findByRole('note')).toHaveTextContent(
      'This block comes from the plugin radicle.countdown, which is off.',
    );
  });
});
