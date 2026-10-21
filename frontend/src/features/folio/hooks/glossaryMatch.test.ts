import { describe, expect, it } from 'vitest';
import type { GlossaryTerm } from '../../../services/api/folioAi';
import { glossaryMatches } from './glossaryMatch';

const term = (id: string, name: string, aliases: string[] = []) =>
  ({
    id,
    term: name,
    aliases,
    definition: `${name}.`,
    status: 'approved',
    source: null,
  }) as unknown as GlossaryTerm;

describe('glossaryMatches', () => {
  it('finds the first whole-word occurrence of each term or alias', () => {
    const root = document.createElement('div');
    root.innerHTML =
      '<p>Abre <strong>Docket</strong> y busca en docketing.</p><p>Usa RQL en tickets.</p>';
    const found = glossaryMatches(root, [
      term('a', 'Docket'),
      term('b', 'Radicle Query Language', ['rql']),
      term('c', 'Folio'),
    ]);
    expect(found.map((m) => [m.term.id, m.range.toString()]).sort()).toEqual([
      ['a', 'Docket'],
      ['b', 'RQL'],
    ]);
  });

  it('lets the longer name win when two overlap', () => {
    const root = document.createElement('div');
    root.textContent = 'Conecta Folio MCP hoy.';
    const found = glossaryMatches(root, [term('a', 'Folio'), term('b', 'Folio MCP')]);
    expect(found.map((m) => m.range.toString())).toEqual(['Folio MCP']);
  });
});
