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
    node('horizontalRule'),
    p(t('Fin')),
  ],
};
