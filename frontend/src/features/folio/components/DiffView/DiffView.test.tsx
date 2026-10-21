import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { blockText } from './text';
import { DiffView } from '.';

const para = (text: string) => ({ type: 'paragraph', content: [{ type: 'text', text }] });

describe('DiffView', () => {
  it('shows metadata changes and added and removed blocks', async () => {
    renderWithProviders(
      <DiffView
        diff={{
          from_version: 1,
          to_version: 2,
          title: { field: 'title', before: 'Guía', after: 'Guía de MCP' },
          metadata: [{ field: 'labels', before: ['mcp'], after: ['mcp', 'agentes'] }],
          blocks: [
            { op: 'equal', block: para('Intro') },
            { op: 'removed', block: para('Viejo') },
            { op: 'added', block: para('Nuevo') },
          ],
        }}
      />,
    );
    expect(await screen.findByText('Guía de MCP')).toBeInTheDocument();
    expect(screen.getByText('mcp, agentes')).toBeInTheDocument();
    expect(screen.getByLabelText('Added')).toHaveTextContent('Nuevo');
    expect(screen.getByLabelText('Removed')).toHaveTextContent('Viejo');
  });

  it('says when nothing changed', async () => {
    renderWithProviders(
      <DiffView diff={{ from_version: 1, to_version: 1, title: null, metadata: [], blocks: [] }} />,
    );
    expect(await screen.findByText(/metadata did not change/i)).toBeInTheDocument();
  });

  it('reads headings and lists as text', () => {
    expect(
      blockText({ type: 'heading', attrs: { level: 2 }, content: [{ type: 'text', text: 'A' }] }),
    ).toBe('## A');
    expect(
      blockText({ type: 'bulletList', content: [{ type: 'listItem', content: [para('uno')] }] }),
    ).toBe('• uno');
  });
});
