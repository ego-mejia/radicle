import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { anchorFor, headingsOf } from './anchors';
import { b, doc, p, t } from './testDoc';
import { DocContent } from '.';

// The text blocks of backend/tests/unit/folio_docs.py EVERY_BLOCK.
const TEXT_BLOCKS = doc(
  b('heading', { level: 1 }, t('Conecta un agente')),
  p(
    t('Texto '),
    t('negrita', 'bold'),
    t(' y '),
    t('código', 'code'),
    t(' con '),
    {
      type: 'text',
      text: 'link',
      marks: [{ type: 'link', attrs: { href: 'https://radicle.dev' } }],
    },
    { type: 'hardBreak' },
    { type: 'mention', attrs: { handle: 'fernando' } },
    t(' '),
    { type: 'status', attrs: { text: 'Listo', color: 'green' } },
  ),
  b('heading', { level: 2 }, t('Antes de empezar')),
  b('bulletList', {}, b('listItem', {}, p(t('uno'))), b('listItem', {}, p(t('dos')))),
  b('orderedList', { start: 3 }, b('listItem', {}, p(t('primero')))),
  b(
    'taskList',
    {},
    b('taskItem', { checked: true }, p(t('hecho'))),
    b('taskItem', { checked: false }, p(t('pendiente'))),
  ),
  b('blockquote', {}, p(t('Una cita'))),
  b('codeBlock', { language: 'python' }, t("print('hola')")),
  b(
    'table',
    {},
    b('tableRow', {}, b('tableHeader', {}, p(t('Campo'))), b('tableHeader', {}, p(t('Regla')))),
    b('tableRow', {}, b('tableCell', {}, p(t('Título'))), b('tableCell', {}, p(t('1 a 200')))),
  ),
  b('horizontalRule', {}),
  b('heading', { level: 2 }, t('Antes de empezar')),
);

describe('anchors', () => {
  it('match the backend: accents dropped, repeats numbered', () => {
    const taken = new Set<string>();
    expect(anchorFor('Conéctalo desde Claude Code', taken)).toBe('conectalo-desde-claude-code');
    expect(anchorFor('Conéctalo desde Claude Code', taken)).toBe('conectalo-desde-claude-code-2');
    expect(anchorFor('¿?', taken)).toBe('section');
    expect(headingsOf(TEXT_BLOCKS).map((h) => h.anchor)).toEqual([
      'conecta-un-agente',
      'antes-de-empezar',
      'antes-de-empezar-2',
    ]);
  });
});

describe('DocContent', () => {
  it('renders the text blocks with their marks', async () => {
    renderWithProviders(<DocContent doc={TEXT_BLOCKS} />);
    const [h1] = await screen.findAllByRole('heading', { name: 'Conecta un agente' });
    if (!h1) throw new Error('no heading');
    expect(h1.tagName).toBe('H2');
    expect(h1).toHaveAttribute('id', 'conecta-un-agente');
    const repeated = screen.getAllByRole('heading', { name: 'Antes de empezar' });
    expect(repeated.map((h) => h.id)).toEqual(['antes-de-empezar', 'antes-de-empezar-2']);
    expect(screen.getByText('negrita').closest('strong')).not.toBeNull();
    expect(screen.getByText('código').closest('code')).not.toBeNull();
    expect(screen.getByRole('link', { name: 'link' })).toHaveAttribute('target', '_blank');
    expect(screen.getByText('@fernando')).toBeInTheDocument();
    expect(screen.getByText('Listo')).toBeInTheDocument();
    expect(screen.getByText('primero').closest('ol')).toHaveAttribute('start', '3');
    const tasks = screen.getAllByRole('checkbox');
    expect(tasks.map((c) => (c as HTMLInputElement).checked)).toEqual([true, false]);
    expect(screen.getByText('Una cita').closest('blockquote')).not.toBeNull();
    expect(screen.getByText("print('hola')").closest('pre')).toHaveAttribute(
      'data-language',
      'python',
    );
    expect(screen.getByRole('columnheader', { name: 'Campo' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: '1 a 200' })).toBeInTheDocument();
    expect(screen.getByRole('separator')).toBeInTheDocument();
  });

  it('skips blocks it does not know', async () => {
    renderWithProviders(<DocContent doc={doc(p(t('Hola')), b('mystery', {}))} />);
    expect(await screen.findByText('Hola')).toBeInTheDocument();
  });
});
