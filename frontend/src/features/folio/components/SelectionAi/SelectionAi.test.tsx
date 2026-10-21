import { Editor } from '@tiptap/core';
import { act, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { folioExtensions } from '../../editor/extensions';
import { SelectionAi } from '.';

const ID = '9f3c0000-0000-4000-8000-000000000001';
let editor: Editor | null = null;
afterEach(() => editor?.destroy());

function setup(available = true) {
  const calls = mockFetch({
    'GET /api/v1/folio/ai/availability': {
      status: 200,
      body: { available, reason: available ? null : 'off_in_space', message: null },
    },
    'POST /api/v1/folio/ai/rewrite': (_r, body) => {
      const { mode, language } = body as { mode: string; language: string | null };
      if (mode === 'translate')
        return { status: 200, body: { text: `Create the agent (${language})` } };
      return { status: 200, body: { text: 'Crea el agente.' } };
    },
  });
  editor = new Editor({
    extensions: folioExtensions(),
    content: '<p>Primero, hay que crear el agente en Admin.</p><p>Luego conéctalo.</p>',
  });
  // jsdom has no layout: place the selection anywhere.
  editor.view.coordsAtPos = () => ({ top: 100, bottom: 120, left: 10, right: 10 });
  renderWithProviders(<SelectionAi editor={editor as never} nodeId={ID} space="docs" />);
  const select = () =>
    act(() => {
      editor!.commands.setTextSelection({ from: 1, to: 43 });
    });
  return { calls, select };
}

describe('SelectionAi', () => {
  it('rewrites the selection and replaces it only when accepted', async () => {
    const { calls, select } = setup();
    await new Promise((r) => setTimeout(r, 0));
    select();
    await userEvent.click(await screen.findByRole('button', { name: 'Rewrite with AI' }));
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Clearer' }));
    expect(await screen.findByText('Crea el agente.')).toBeInTheDocument();
    expect(calls.at(-1)?.body).toMatchObject({
      node_id: ID,
      mode: 'clearer',
      text: 'Primero, hay que crear el agente en Admin.',
    });
    expect(editor!.getText()).toContain('Primero'); // nothing changed yet

    await userEvent.click(screen.getByRole('button', { name: 'Replace the selection' }));
    expect(editor!.getText({ blockSeparator: '|' })).toBe('Crea el agente.|Luego conéctalo.');
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('translates to the language you type, and discarding keeps the text', async () => {
    const { calls, select } = setup();
    await new Promise((r) => setTimeout(r, 0));
    select();
    await userEvent.click(await screen.findByRole('button', { name: 'Rewrite with AI' }));
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Translate' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Language' }), 'English{Enter}');
    expect(await screen.findByText('Create the agent (English)')).toBeInTheDocument();
    expect(calls.at(-1)?.body).toMatchObject({ mode: 'translate', language: 'English' });
    await userEvent.click(screen.getByRole('button', { name: 'Discard' }));
    expect(editor!.getText()).toContain('Primero, hay que crear');
  });

  it('is not offered with AI off in the space', async () => {
    const { calls, select } = setup(false);
    await new Promise((r) => setTimeout(r, 20));
    select();
    expect(calls.some((c) => c.path.includes('availability'))).toBe(true);
    expect(screen.queryByRole('button', { name: 'Rewrite with AI' })).toBeNull();
  });
});
