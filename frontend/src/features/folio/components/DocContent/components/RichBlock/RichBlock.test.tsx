import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../../../test/renderWithProviders';
import { b, doc, p, t } from '../../testDoc';
import { DocContent } from '../..';

// The rich blocks of backend/tests/unit/folio_docs.py EVERY_BLOCK.
const RICH = doc(
  b('heading', { level: 1 }, t('Conecta un agente')),
  b('heading', { level: 2 }, t('Antes de empezar')),
  b('panel', { kind: 'warning' }, p(t('Ojo con el token.'))),
  b('expand', { title: 'Más' }, p(t('Detalles ocultos'))),
  b(
    'columns',
    { layout: 'two' },
    b('column', {}, p(t('izquierda'))),
    b('column', {}, p(t('derecha'))),
  ),
  b('tableOfContents', {}),
  b('childPages', {}),
  b('image', { assetId: 'a1', alt: 'Diagrama', caption: 'El flujo', size: 'large' }),
  b('file', { assetId: 'f1', name: 'guia.pdf', size: 2048 }),
  b('video', { src: '/v.mp4', caption: 'Demo' }),
);

describe('RichBlock', () => {
  it('renders panels, expands, columns, the index, child pages and media', async () => {
    const children = [{ id: 'c1', title: 'Hija', slug: 'hija' }];
    renderWithProviders(<DocContent doc={RICH} childPages={children} />);
    const panel = (await screen.findByText('Ojo con el token.')).closest('aside');
    expect(panel).toHaveAttribute('data-kind', 'warning');
    expect(screen.getByText('Más').tagName).toBe('SUMMARY');
    expect(screen.getByText('izquierda')).toBeInTheDocument();
    expect(screen.getByText('derecha')).toBeInTheDocument();

    const toc = screen.getByRole('navigation', { name: 'On this page' });
    expect(within(toc).getByRole('link', { name: 'Antes de empezar' })).toHaveAttribute(
      'href',
      '#antes-de-empezar',
    );
    const pages = screen.getByRole('navigation', { name: 'Pages in here' });
    expect(within(pages).getByRole('link', { name: 'Hija' })).toHaveAttribute(
      'href',
      '/folio/p/c1-hija',
    );

    expect(screen.getByRole('img', { name: 'Diagrama' })).toHaveAttribute(
      'src',
      '/api/v1/folio/assets/a1',
    );
    expect(screen.getByText('El flujo')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /guia\.pdf/ })).toHaveAttribute(
      'href',
      '/api/v1/folio/assets/f1',
    );
    expect(screen.getByText('2 KB')).toBeInTheDocument();
    expect(screen.getByText('Demo')).toBeInTheDocument();
  });

  it('leaves out media without a source and empty child page lists', async () => {
    renderWithProviders(
      <DocContent doc={doc(p(t('Hola')), b('image', { alt: 'Nada' }), b('childPages', {}))} />,
    );
    expect(await screen.findByText('Hola')).toBeInTheDocument();
    expect(screen.queryByRole('img')).toBeNull();
    expect(screen.queryByRole('navigation')).toBeNull();
  });
  it('puts two or three sides next to each other, each with its heading', async () => {
    const side = (title: string, text: string) => b('comparisonSide', { title }, p(t(text)));
    renderWithProviders(
      <DocContent
        doc={doc(b('comparison', {}, side('Antes', 'lento'), side('Después', 'rápido')))}
      />,
    );
    const before = await screen.findByRole('heading', { name: 'Antes' });
    expect(before.closest('section')).toHaveTextContent('lento');
    expect(screen.getByRole('heading', { name: 'Después' }).closest('section')).toHaveTextContent(
      'rápido',
    );
  });
});
