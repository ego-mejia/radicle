// A document with every phase 1 block: the same as the server's EVERY_BLOCK
// (backend/tests/unit/folio_docs.py), so both sides test the same shapes.

import type { JSONContent } from '@tiptap/core';

type Mark = NonNullable<JSONContent['marks']>[number];
const t = (text: string, marks?: Mark[]): JSONContent =>
  marks ? { type: 'text', text, marks } : { type: 'text', text };
const p = (...content: JSONContent[]): JSONContent => ({ type: 'paragraph', content });
const node = (type: string, attrs?: Record<string, unknown>, ...content: JSONContent[]) => {
  const out: JSONContent = { type };
  if (attrs) out.attrs = attrs;
  if (content.length) out.content = content;
  return out;
};

export const EVERY_BLOCK: JSONContent = {
  type: 'doc',
  content: [
    node('heading', { level: 1 }, t('Conecta un agente')),
    p(
      t('Texto '),
      t('negrita', [{ type: 'bold' }]),
      t(' y '),
      t('código', [{ type: 'code' }]),
      t(' con '),
      t('link', [{ type: 'link', attrs: { href: 'https://radicle.dev' } }]),
      { type: 'hardBreak' },
      { type: 'mention', attrs: { handle: 'fernando' } },
      t(' '),
      { type: 'status', attrs: { text: 'Listo', color: 'green' } },
      t(' '),
      { type: 'ticket', attrs: { key: 'PA-4' } },
    ),
    node('heading', { level: 2 }, t('Antes de empezar')),
    node(
      'bulletList',
      undefined,
      node('listItem', undefined, p(t('uno'))),
      node('listItem', undefined, p(t('dos'))),
    ),
    node('orderedList', { start: 1 }, node('listItem', undefined, p(t('primero')))),
    node(
      'taskList',
      undefined,
      node('taskItem', { checked: true }, p(t('hecho'))),
      node('taskItem', { checked: false }, p(t('pendiente'))),
    ),
    node('blockquote', undefined, p(t('Una cita'))),
    node('codeBlock', { language: 'python' }, t("print('hola')")),
    node(
      'table',
      undefined,
      node(
        'tableRow',
        undefined,
        node('tableHeader', undefined, p(t('Campo'))),
        node('tableHeader', undefined, p(t('Regla'))),
      ),
      node(
        'tableRow',
        undefined,
        node('tableCell', undefined, p(t('Título'))),
        node('tableCell', { background: '#ECF8C8' }, p(t('1 a 200'))),
      ),
    ),
    node('panel', { kind: 'warning' }, p(t('Ojo con el token.'))),
    node('expand', { title: 'Más' }, p(t('Detalles'))),
    node(
      'columns',
      { layout: 'two' },
      node('column', undefined, p(t('izquierda'))),
      node('column', undefined, p(t('derecha'))),
    ),
    node('tableOfContents'),
    node('childPages'),
    node('image', {
      src: '/api/v1/folio/assets/1',
      alt: 'Diagrama',
      caption: 'El flujo',
      size: 'large',
      align: 'center',
    }),
    node('file', { assetId: 'a1', name: 'spec.pdf', mimeType: 'application/pdf', size: 1024 }),
    node('video', { src: 'https://example.com/v.mp4', caption: 'Demo' }),
    node('embed', { url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', title: 'La demo' }),
    node('databaseView', { database: '6f1c3a52-9d2e-4b8a-a1f0-3c5e7d9b2a14', view: 'board' }),
    node('whiteboard', { whiteboard: '0b7e2c41-5a3d-4f6e-9c8b-1d2e3f4a5b6c' }),
    node('visual', {
      format: 'svg',
      code: '<svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="4" fill="var(--accent)"/></svg>',
      title: 'Raíz',
      description: 'Un círculo lima: la semilla de Radicle.',
    }),
    node('diagram', { language: 'mermaid', source: 'graph TD\n  A-->B', caption: 'Flujo' }),
    node('chart', {
      kind: 'bar',
      title: 'Tickets por área',
      data: [
        ['Área', 'Abiertos', 'Cerrados'],
        ['Legal', 3, 5],
        ['Backend', 7, 2.5],
      ],
    }),
    node('timeline', {
      items: [
        { date: '2026-11-01', title: 'Beta', text: 'Equipo interno', status: 'done' },
        { title: 'Lanzamiento' },
      ],
    }),
    node('formula', { latex: 'E = mc^2' }),
    p(t('En línea '), { type: 'inlineFormula', attrs: { latex: 'a^2 + b^2' } }),
    node('chart', { kind: 'line', source: 'table' }),
    node(
      'comparison',
      undefined,
      node('comparisonSide', { title: 'Antes' }, p(t('rápido'))),
      node('comparisonSide', undefined, p(t('más rápido'))),
    ),
    node('pageList', { label: 'onboarding', limit: 5, space: 'docs', order: 'title' }),
    node('ticketTable', { rql: 'project = PA AND status != Done', title: 'Pendientes', limit: 10 }),
    node('horizontalRule'),
    p(t('Fin')),
  ],
};
