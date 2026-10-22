import { Link } from '@tanstack/react-router';
import { Fragment, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import type { DocNode, Heading } from '../../anchors';
import { useDocEnv } from '../../env';
import { toneOf } from '../Inline/tone';
import { DatabaseView } from '../../../DatabaseView';
import { EmbedCard } from '../../../EmbedCard';
import { Diagram } from '../../../Diagram';
import { Formula } from '../../../Formula';
import { VisualFrame } from '../../../VisualFrame';
import { ChartBlock } from '../../../ChartBlock';
import type { ChartKind } from '../../../ChartBlock/components/ChartView';
import { type ChartData, tableData } from '../../../ChartBlock/tableData';
import { PageList } from '../../../PageList';
import { TicketTable } from '../../../TicketTable';
import { TicketProgress } from '../../../TicketProgress';
import { Timeline, type TimelineItem } from '../../../Timeline';
import { WhiteboardEmbed } from '../../../WhiteboardEmbed';
import { CalendarEmbed } from '../../../CalendarEmbed';
import { PluginFrame } from '../../../PluginFrame';
import * as S from './style';

export type ChildPage = { id: string; title: string; slug: string };

const ACCOUNT_ONLY = new Set([
  'whiteboard',
  'calendar',
  'pluginBlock',
  'databaseView',
  'pageList',
  'ticketTable',
  'ticketProgress',
]);

type Props = {
  node: DocNode;
  /** The block just before, for a chart drawn from the table above it. */
  previous?: DocNode;
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

function mediaSrc(attrs: DocNode['attrs'], assetUrl: (id: string) => string): string | undefined {
  if (attrs?.assetId) return assetUrl(String(attrs.assetId));
  return attrs?.src ? String(attrs.src) : undefined;
}

/** Panels, expands, columns, the table of contents, child pages and media. */
export function RichBlock({ node: n, previous, headings, childPages, children }: Props) {
  const { t } = useTranslation();
  const env = useDocEnv();
  const a = n.attrs ?? {};
  // Live data read with the reader's account: a stranger gets a note instead.
  if (env.isPublic && ACCOUNT_ONLY.has(n.type))
    return <S.LiveOnly role="note">{t('folio.public.liveOnly')}</S.LiveOnly>;
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
          {childPages.map((c) =>
            env.pageLink ? (
              <Fragment key={c.id}>{env.pageLink(c)}</Fragment>
            ) : (
              <Link key={c.id} to="/folio/p/$page" params={{ page: `${c.id}-${c.slug}` }}>
                {c.title}
              </Link>
            ),
          )}
        </S.Toc>
      );
    case 'image':
    case 'video': {
      const src = mediaSrc(a, env.assetUrl);
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
    case 'whiteboard':
      return <WhiteboardEmbed nodeId={String(a.whiteboard)} />;
    case 'pluginBlock':
      return (
        <PluginFrame
          plugin={String(a.plugin)}
          block={String(a.block)}
          data={(a.data as Record<string, string> | null) ?? null}
        />
      );
    case 'calendar':
      return (
        <CalendarEmbed
          calendarId={String(a.calendar)}
          view={a.view === 'week' ? 'week' : 'month'}
        />
      );
    case 'databaseView':
      return (
        <DatabaseView
          nodeId={String(a.database)}
          viewId={a.view ? String(a.view) : null}
          embedded
        />
      );
    case 'chart':
      return (
        <ChartBlock
          kind={String(a.kind ?? 'bar') as ChartKind}
          title={a.title ? String(a.title) : null}
          data={a.source === 'table' ? tableData(previous) : ((a.data as ChartData) ?? null)}
        />
      );
    case 'timeline':
      return <Timeline items={(a.items as TimelineItem[]) ?? []} />;
    case 'pageList':
      return (
        <PageList
          label={String(a.label ?? '')}
          space={a.space ? String(a.space) : null}
          limit={a.limit ? Number(a.limit) : null}
          order={a.order === 'title' ? 'title' : null}
        />
      );
    case 'ticketTable':
      return (
        <TicketTable
          rql={String(a.rql ?? '')}
          title={a.title ? String(a.title) : null}
          limit={a.limit ? Number(a.limit) : null}
        />
      );
    case 'ticketProgress':
      return <TicketProgress title={a.title ? String(a.title) : null} />;
    case 'comparison':
      return (
        <S.Compare $sides={(n.content ?? []).length}>
          {(n.content ?? []).map((side, i) => (
            <section key={i}>
              {side.attrs?.title ? <h4>{String(side.attrs.title)}</h4> : null}
              {children(side.content)}
            </section>
          ))}
        </S.Compare>
      );
    case 'embed':
      return <EmbedCard url={String(a.url)} title={a.title ? String(a.title) : null} />;
    case 'file':
      return (
        <S.File href={env.assetUrl(String(a.assetId))} download={a.name ? String(a.name) : true}>
          {String(a.name || t('folio.reader.file'))}
          <small>{formatBytes(a.size)}</small>
        </S.File>
      );
    default:
      return null;
  }
}
