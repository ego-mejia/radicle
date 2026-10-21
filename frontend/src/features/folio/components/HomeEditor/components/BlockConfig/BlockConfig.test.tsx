import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { HomeLayoutBlock } from '../../../../../../services/api/folio';
import { mockFetch, renderWithProviders } from '../../../../../../test/renderWithProviders';
import { BlockConfig } from '.';

function block(type: string, config: Record<string, unknown> = {}): HomeLayoutBlock {
  return { id: type, type, x: 0, y: 0, w: 6, h: 2, config };
}

describe('BlockConfig', () => {
  it('sets the space, label, kind and how many for a posts block', async () => {
    mockFetch({
      'GET /api/v1/folio/spaces': {
        status: 200,
        body: { items: [{ key: 'ai-tools', name: 'AI Tools' }] },
      },
    });
    const onChange = vi.fn();
    renderWithProviders(<BlockConfig block={block('posts')} errors={[]} onChange={onChange} />);
    await userEvent.selectOptions(
      await screen.findByLabelText('Space'),
      await screen.findByRole('option', { name: 'AI Tools' }),
    );
    expect(onChange).toHaveBeenLastCalledWith({ space: 'ai-tools' });
    await userEvent.type(screen.getByLabelText('Label'), 'm');
    expect(onChange).toHaveBeenLastCalledWith({ label: 'm' });
    await userEvent.selectOptions(screen.getByLabelText('Shows'), 'all');
    expect(onChange).toHaveBeenLastCalledWith({ kind: 'all' });
    await userEvent.type(screen.getByLabelText('How many (1 to 12)'), '4');
    expect(onChange).toHaveBeenLastCalledWith({ limit: 4 });
  });

  it('shows where the RQL is wrong', async () => {
    const errors = [{ field: 'config.rql', message: 'Unknown field spaec', position: 0 }];
    renderWithProviders(
      <BlockConfig
        block={block('query', { rql: 'spaec = x' })}
        errors={errors}
        onChange={vi.fn()}
      />,
    );
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unknown field spaec (at character 1)',
    );
    expect(screen.getByLabelText('RQL query')).toHaveValue('spaec = x');
  });

  it('pins a page found by search, and unpins it', async () => {
    mockFetch({
      'GET /api/v1/folio/search': {
        status: 200,
        body: {
          items: [
            { node_id: 'n1', title: 'Welcome', space: 'eng' },
            { node_id: 'n1', title: 'Welcome', space: 'eng' },
          ],
        },
      },
      'GET /api/v1/folio/nodes/n1': { status: 200, body: { id: 'n1', title: 'Welcome' } },
    });
    function Harness() {
      const [config, setConfig] = useState<Record<string, unknown>>({ node: null });
      return (
        <BlockConfig
          block={block('featured', config)}
          errors={[]}
          onChange={(c) => setConfig({ ...config, ...c })}
        />
      );
    }
    renderWithProviders(<Harness />);
    expect(await screen.findByText('Shows the newest labelled one.')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Pin a page or post'), 'wel');
    const hits = await screen.findAllByRole('button', { name: /Welcome/ });
    expect(hits).toHaveLength(1);
    await userEvent.click(hits[0] as HTMLElement);
    expect(await screen.findByText('Pinned: Welcome')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Use the newest' }));
    expect(screen.getByText('Shows the newest labelled one.')).toBeInTheDocument();
  });

  it('edits a text block', async () => {
    const onChange = vi.fn();
    renderWithProviders(<BlockConfig block={block('text')} errors={[]} onChange={onChange} />);
    await userEvent.type(await screen.findByLabelText('Text (Markdown)'), '#');
    expect(onChange).toHaveBeenLastCalledWith({ markdown: '#' });
  });
});
