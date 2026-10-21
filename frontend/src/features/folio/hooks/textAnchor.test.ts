import { afterEach, describe, expect, it } from 'vitest';
import { anchorFromSelection, rangeOf } from './textAnchor';

function page(): HTMLElement {
  const root = document.createElement('div');
  root.innerHTML = '<h2>Agentes</h2><p>Crea el agente y <b>conéctalo</b> por MCP con su token.</p>';
  document.body.append(root);
  return root;
}

afterEach(() => {
  document.body.innerHTML = '';
});

describe('textAnchor', () => {
  it('turns a selection into a quote with its context and offset', () => {
    const root = page();
    const range = rangeOf(root, 'conéctalo por MCP');
    expect(range?.toString()).toBe('conéctalo por MCP');
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range!);
    const anchor = anchorFromSelection(root, selection);
    expect(anchor).toEqual({
      quote: 'conéctalo por MCP',
      prefix: 'AgentesCrea el agente y ',
      suffix: ' con su token.',
      offset: 24,
    });
  });

  it('ignores empty selections and text outside the page', () => {
    const root = page();
    const outside = document.createElement('p');
    outside.textContent = 'Fuera';
    document.body.append(outside);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    expect(anchorFromSelection(root, selection)).toBeNull();
    const range = document.createRange();
    range.selectNodeContents(outside);
    selection.addRange(range);
    expect(anchorFromSelection(root, selection)).toBeNull();
    expect(rangeOf(root, 'no está')).toBeNull();
  });
});
