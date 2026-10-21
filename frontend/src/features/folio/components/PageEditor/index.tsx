import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Placeholder } from '@tiptap/extensions';
import { EditorContent, useEditor, type Editor } from '@tiptap/react';
import { ArrowLeft, History } from 'lucide-react';
import { useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  assetUrl,
  fetchDraft,
  fetchNode,
  folioKeys,
  nodePath,
  patchNode,
  saveDraft,
  uploadAsset,
  type FolioDraft,
  type FolioNode,
} from '../../../../services/api/folio';
import { folioExtensions } from '../../editor/extensions';
import { toFolioDoc } from '../../editor/schema';
import { BLOCKS } from '../../editor/blocks';
import { SlashCommand } from '../../editor/slash';
import { FolioUploads } from '../../editor/uploads';
import { pickFiles } from '../../hooks/pickFiles';
import { AiMenu } from '../AiMenu';
import { EditorProse } from '../EditorProse';
import { SelectionComment } from '../SelectionComment';
import { PageHeader } from './components/PageHeader';
import { mediaBlocks } from './media';
import * as S from './style';
import { useAutosave } from '../../hooks/useAutosave';
import { useComments } from '../../hooks/useComments';
import { useCollab, type Collab, type Me } from '../../hooks/useCollab';
import { collabExtensions } from '../../editor/collab';
import { colorFor } from '../../editor/presence';
import { useMe } from '../../../../hooks/useMe';
import { Presence } from './components/Presence';
import { Pointers } from './components/Pointers';

type Props = {
  nodeId: string;
  /** Opens the publish dialog; the button stays hidden without it. */
  onPublish?: (editor: Editor) => void;
  /** More editor extensions, like the slash menu or uploads. */
  extensions?: ReturnType<typeof folioExtensions>;
  /** Edit together in real time (Folio 2.2) instead of saving the draft alone. */
  collab?: boolean;
};

/** Writes a page's draft full screen: icon and title on top, the body below, saved as you go. */
export function PageEditor({ nodeId, onPublish, extensions, collab = false }: Props) {
  const node = useQuery({ queryKey: folioKeys.node(nodeId), queryFn: () => fetchNode(nodeId) });
  const draft = useQuery({
    queryKey: folioKeys.draft(nodeId),
    queryFn: () => fetchDraft(nodeId),
    staleTime: Infinity, // the editor owns the draft while it is open
  });
  if (!node.data || !draft.data) return <PageSpinner />;
  const Body = collab ? WithRoom : Loaded;
  return (
    <Body node={node.data} draft={draft.data} onPublish={onPublish} extensions={extensions ?? []} />
  );
}

type LoadedProps = {
  node: FolioNode;
  draft: FolioDraft;
  onPublish?: Props['onPublish'];
  extensions: ReturnType<typeof folioExtensions>;
  room?: { collab: Collab; me: Me };
};

/** Joins the document's room, then edits it with everyone in it. */
function WithRoom(props: Omit<LoadedProps, 'room'>) {
  const user = useMe();
  const [me] = useState<Me>(() => ({
    name: user.display_name,
    handle: user.handle,
    color: colorFor(user.handle),
  }));
  const collab = useCollab(props.node.id, me);
  // The editor waits for the room's content: built on an empty document, it would write
  // that empty document into the room and mix it with what is there.
  if (!collab.synced) return <PageSpinner />;
  return <Loaded {...props} room={{ collab, me }} />;
}

function Loaded({ node, draft, onPublish, extensions, room }: LoadedProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(node.title);
  const [icon, setIcon] = useState(node.icon);
  const [cover, setCover] = useState(node.cover_asset_id);
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const failed = (error: unknown) => toast(errorMessage(error), 'error');
  const upload = (file: File) => uploadAsset(node.id, file);
  const editorRef = useRef<Editor | null>(null);
  const bodyEl = useRef<HTMLDivElement>(null);
  const pageEl = useRef<HTMLDivElement>(null);
  const discussion = useComments(node.id);

  const body = useAutosave(async (doc: Record<string, unknown>) => {
    const saved = await saveDraft(node.id, { content_json: doc });
    queryClient.setQueryData(folioKeys.draft(node.id), saved);
  });
  const header = useAutosave(async (patch: { title?: string; icon?: string | null }) => {
    const saved = await patchNode(node.id, patch);
    queryClient.setQueryData(folioKeys.node(node.id), saved);
  });

  const allExtensions = useMemo(
    () => [
      ...folioExtensions({ shared: !!room }),
      ...(room ? collabExtensions(room.collab, room.me) : []),
      Placeholder.configure({ placeholder: t('folio.editor.bodyPlaceholder') }),
      SlashCommand.configure({
        items: [...BLOCKS, ...mediaBlocks(() => editorRef.current, upload, failed)],
      }),
      FolioUploads.configure({ upload, onError: failed }),
      ...extensions,
    ],
    // The editor is built once; the language does not change while writing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  const editor = useEditor(
    {
      extensions: allExtensions,
      // Shared: the content comes from the room, and the room saves it.
      content: room ? undefined : draft.content_json,
      onUpdate: room ? undefined : ({ editor: e }) => body.change(toFolioDoc(e.getJSON())),
    },
    // Shared: built once. Who's in changes often, and rebuilding would lose the cursor.
    room ? [] : undefined,
  );
  editorRef.current = editor;

  const changeCover = async (assetId: string | null) => {
    try {
      const saved = await patchNode(node.id, { cover_asset_id: assetId });
      queryClient.setQueryData(folioKeys.node(node.id), saved);
      setCover(assetId);
    } catch (error) {
      failed(error);
    }
  };
  const pickCover = async () => {
    const [file] = await pickFiles('image/*', false);
    if (!file) return;
    try {
      await changeCover((await upload(file)).id);
    } catch (error) {
      failed(error);
    }
  };

  const states = [room ? roomState(room.collab) : body.state, header.state];
  const state = states.includes('offline')
    ? 'offline'
    : states.includes('error')
      ? 'error'
      : states.includes('saving') || states.includes('unsaved')
        ? 'saving'
        : 'saved';

  return (
    <S.Screen>
      <S.Bar>
        <S.Back to={node.version ? nodePath(node) : `/folio/s/${node.space}`}>
          <ArrowLeft aria-hidden size={16} />
          {t('folio.editor.back')}
        </S.Back>
        <S.Crumb>{[node.space, ...node.breadcrumbs.map((b) => b.title)].join(' / ')}</S.Crumb>
        {room && <Presence peers={room.collab.peers} />}
        {node.kind === 'live_doc' && (
          <S.Back to={`${nodePath(node)}/history`}>
            <History aria-hidden size={16} />
            {t('folio.editor.history')}
          </S.Back>
        )}
        {editor && <AiMenu editor={editor} nodeId={node.id} space={node.space} />}
        <S.SaveState role="status" $error={state === 'error' || state === 'offline'}>
          {t(`folio.editor.state.${state}`)}
        </S.SaveState>
        {onPublish && editor && node.kind !== 'live_doc' && (
          <Button
            variant="primary"
            onClick={async () => {
              await Promise.all([body.flush(), header.flush()]);
              onPublish(editor);
            }}
          >
            {t('folio.editor.publish')}
          </Button>
        )}
      </S.Bar>
      <S.Scroll>
        {cover && (
          <S.Cover>
            <img src={assetUrl(cover)} alt="" />
            <S.CoverTools>
              <Button size="sm" onClick={() => void pickCover()}>
                {t('folio.editor.changeCover')}
              </Button>
              <Button size="sm" onClick={() => void changeCover(null)}>
                {t('folio.editor.removeCover')}
              </Button>
            </S.CoverTools>
          </S.Cover>
        )}
        <S.Page ref={pageEl}>
          {room && (
            <Pointers
              container={pageEl}
              awareness={room.collab.provider.awareness}
              peers={room.collab.peers}
            />
          )}
          <PageHeader
            tools={
              !cover && (
                <Button size="sm" variant="ghost" onClick={() => void pickCover()}>
                  {t('folio.editor.addCover')}
                </Button>
              )
            }
            title={title}
            icon={icon}
            // Each save sends title and icon together, so the latest save keeps both.
            onTitle={(value) => {
              setTitle(value);
              if (value.trim()) header.change({ title: value.trim(), icon });
            }}
            onIcon={(value) => {
              setIcon(value);
              header.change({ title: title.trim() || node.title, icon: value });
            }}
            onDone={() => editor?.commands.focus('start')}
          />
          <EditorProse>
            <div ref={bodyEl}>
              <EditorContent editor={editor} />
            </div>
          </EditorProse>
          {node.version != null && (
            <SelectionComment
              container={bodyEl}
              mentions={discussion.mentions}
              onComment={async (anchor, text) => {
                await Promise.all([body.flush(), header.flush()]);
                await discussion.add.mutateAsync({ body: text, anchor });
              }}
            />
          )}
        </S.Page>
      </S.Scroll>
    </S.Screen>
  );
}

/** Saved once the room has the document; offline while it reconnects. */
function roomState(collab: Collab): 'saved' | 'saving' | 'offline' {
  if (collab.status === 'disconnected') return 'offline';
  return collab.status === 'connected' && collab.synced ? 'saved' : 'saving';
}
