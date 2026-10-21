import { Link } from '@tanstack/react-router';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { assetUrl } from '../../../../../../services/api/folio';
import type { DocNode, Heading } from '../../anchors';
import { toneOf } from '../Inline/tone';
import { DatabaseView } from '../../../DatabaseView';
import { EmbedCard } from '../../../EmbedCard';
import { Diagram } from '../../../Diagram';
import { Formula } from '../../../Formula';
import { VisualFrame } from '../../../VisualFrame';
import * as S from './style';

export type ChildPage = { id: string; title: string; slug: string };

type Props = {
  node: DocNode;
  headings: Heading[];
  childPages: ChildPage[];
  /** Renders nested blocks, stacked. */
  children: (nodes?: DocNode[]) => ReactNode;
};

function formatBytes(size: unknown): string {
  const n = Number(size);
  if (!Number.isFinite(n) || n <= 0) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function mediaSrc(attrs: DocNode['attrs']): string | undefined {
  if (attrs?.assetId) return assetUrl(String(attrs.assetId));
  return attrs?.src ? String(attrs.src) : undefined;
}

/** Panels, expands, columns, the table of contents, child pages and media. */
export function RichBlock({ node: n, headings, childPages, children }: Props) {
  const { t } = useTranslation();
  const a = n.attrs ?? {};
  switch (n.type) {
    case 'panel':
      return (
        <S.Panel $tone={toneOf(String(a.kind ?? 'info'))} data-kind={String(a.kind ?? 'info')}>
          {children(n.content)}
        </S.Panel>
      );
    case 'expand':
      return (
        <S.Expand>
          <summary>{String(a.title || t('folio.reader.details'))}</summary>
          {children(n.content)}
        </S.Expand>
      );
    case 'columns':
      return (
        <S.Columns $layout={String(a.layout ?? 'two')}>
          {(n.content ?? []).map((col, i) => (
            <div key={i}>{children(col.content)}</div>
          ))}
        </S.Columns>
      );
    case 'tableOfContents':
      if (!headings.length) return null;
      return (
        <S.Toc aria-label={t('folio.reader.toc')}>
          {headings.map((h) => (
            <S.TocLink key={h.anchor} href={`#${h.anchor}`} $depth={h.level - 1}>
              {h.text}
            </S.TocLink>
          ))}
        </S.Toc>
      );
    case 'childPages':
      if (!childPages.length) return null;
      return (
        <S.Toc aria-label={t('folio.reader.childPages')}>
          {childPages.map((c) => (
            <Link key={c.id} to="/folio/p/$page" params={{ page: `${c.id}-${c.slug}` }}>
              {c.title}
            </Link>
          ))}
        </S.Toc>
      );
    case 'image':
    case 'video': {
      const src = mediaSrc(a);
      if (!src) return null;
      return (
        <S.Figure $size={String(a.size ?? 'large')} $align={String(a.align ?? 'center')}>
          {n.type === 'image' ? (
            <img src={src} alt={a.alt ? String(a.alt) : ''} loading="lazy" />
          ) : (
            <video src={src} controls preload="metadata" />
          )}
          {a.caption ? <figcaption>{String(a.caption)}</figcaption> : null}
        </S.Figure>
      );
    }
    case 'visual':
      return (
        <VisualFrame
          code={String(a.code ?? '')}
          title={a.title ? String(a.title) : null}
          description={String(a.description ?? '')}
        />
      );
    case 'diagram':
      return (
        <Diagram source={String(a.source ?? '')} caption={a.caption ? String(a.caption) : null} />
      );
    case 'formula':
      return <Formula latex={String(a.latex ?? '')} />;
    case 'databaseView':
      return (
        <DatabaseView
          nodeId={String(a.database)}
          viewId={a.view ? String(a.view) : null}
          embedded
        />
      );
    case 'embed':
      return <EmbedCard url={String(a.url)} title={a.title ? String(a.title) : null} />;
    case 'file':
      return (
        <S.File href={assetUrl(String(a.assetId))} download={a.name ? String(a.name) : true}>
          {String(a.name || t('folio.reader.file'))}
          <small>{formatBytes(a.size)}</small>
        </S.File>
      );
    default:
      return null;
  }
}
