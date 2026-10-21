import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { Download, Shapes } from 'lucide-react';
import { Suspense, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useMe } from '../../../../hooks/useMe';
import type { FolioNode } from '../../../../services/api/folio';
import { fetchWhiteboard, whiteboardKeys } from '../../../../services/api/folioWhiteboards';
import { colorFor } from '../../editor/presence';
import { useCollab, type Me } from '../../hooks/useCollab';
import type { SceneElement } from '../../whiteboard/sync';
import { NodeMenu } from '../NodeMenu';
import { Presence } from '../PageEditor/components/Presence';
import type { BoardExport } from '../WhiteboardBoard';
import { LazyWhiteboardBoard } from '../WhiteboardBoard/lazy';
import * as S from './style';

/** How often readers see what those drawing saved. */
const REFRESH_MS = 10_000;

type PageProps = { node: FolioNode; spaceName?: string };
type FrameProps = PageProps & {
  exporter: BoardExport | null;
  presence?: React.ReactNode;
  children: React.ReactNode;
};

function download(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/** The page around the canvas: path, export buttons, menu and title. */
function Frame({ node, spaceName, exporter, presence, children }: FrameProps) {
  const { t } = useTranslation();
  const save = async (kind: 'png' | 'svg') => {
    if (exporter) download(await exporter[kind](), `${node.slug || 'whiteboard'}.${kind}`);
  };
  return (
    <S.Page>
      <S.Bar>
        <S.Crumbs aria-label={t('folio.reader.path')}>
          <Link to="/folio/s/$key" params={{ key: node.space }}>
            {spaceName ?? node.space}
          </Link>
          {node.breadcrumbs.map((b) => (
            <span key={b.id}>
              <span aria-hidden>/</span>
              <Link to="/folio/p/$page" params={{ page: `${b.id}-${b.slug}` }}>
                {b.title}
              </Link>
            </span>
          ))}
        </S.Crumbs>
        {presence}
        <Button size="sm" disabled={!exporter} onClick={() => void save('png')}>
          <Download aria-hidden />
          {t('folio.whiteboard.exportPng')}
        </Button>
        <Button size="sm" disabled={!exporter} onClick={() => void save('svg')}>
          <Download aria-hidden />
          {t('folio.whiteboard.exportSvg')}
        </Button>
        {node.can_edit && <NodeMenu node={node} />}
      </S.Bar>
      <S.Body>
        <S.Title>
          {node.icon ? <span aria-hidden>{node.icon}</span> : <Shapes aria-hidden />}
          {node.title}
        </S.Title>
        <S.Board>
          <Suspense fallback={<PageSpinner />}>{children}</Suspense>
        </S.Board>
      </S.Body>
    </S.Page>
  );
}

/** Those who may draw join the room and see who else is in it. */
function Drawing(props: PageProps) {
  const user = useMe();
  const [me] = useState<Me>(() => ({
    name: user.display_name,
    handle: user.handle,
    color: colorFor(user.handle),
  }));
  const collab = useCollab(props.node.id, me);
  const [exporter, setExporter] = useState<BoardExport | null>(null);
  return (
    <Frame {...props} exporter={exporter} presence={<Presence peers={collab.peers} />}>
      {collab.synced ? (
        <LazyWhiteboardBoard elements={[]} collab={collab} onExport={setExporter} />
      ) : (
        <PageSpinner />
      )}
    </Frame>
  );
}

/** Readers see what was last saved, refreshed every few seconds. */
function Viewing(props: PageProps) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const [exporter, setExporter] = useState<BoardExport | null>(null);
  const board = useQuery({
    queryKey: whiteboardKeys.whiteboard(props.node.id),
    queryFn: () => fetchWhiteboard(props.node.id),
    refetchInterval: REFRESH_MS,
  });
  return (
    <Frame {...props} exporter={exporter}>
      {board.isPending ? (
        <PageSpinner />
      ) : board.isError ? (
        <EmptyState title={t('folio.whiteboard.unavailable')} text={errorMessage(board.error)} />
      ) : (
        <LazyWhiteboardBoard
          elements={board.data.elements as SceneElement[]}
          onExport={setExporter}
        />
      )}
    </Frame>
  );
}

/** A whiteboard's own page: its path, its title and the canvas, drawn together. */
export function WhiteboardPage(props: PageProps) {
  return props.node.can_edit ? <Drawing {...props} /> : <Viewing {...props} />;
}
