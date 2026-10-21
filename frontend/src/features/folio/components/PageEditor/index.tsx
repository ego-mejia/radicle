import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Placeholder } from '@tiptap/extensions';
import { EditorContent, useEditor, type Editor } from '@tiptap/react';
import { ArrowLeft } from 'lucide-react';
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
import { EditorProse } from '../EditorProse';
import { SelectionComment } from '../SelectionComment';
import { PageHeader } from './components/PageHeader';
import { mediaBlocks } from './media';
import * as S from './style';
import { useAutosave } from '../../hooks/useAutosave';
import { useComments } from '../../hooks/useComments';

type Props = {
  nodeId: string;
  /** Opens the publish dialog; the button stays hidden without it. */
  onPublish?: (editor: Editor) => void;
  /** More editor extensions, like the slash menu or uploads. */
  extensions?: ReturnType<typeof folioExtensions>;
};

/** Writes a page's draft full screen: icon and title on top, the body below, saved as you go. */
export function PageEditor({ nodeId, onPublish, extensions }: Props) {
  const node = useQuery({ queryKey: folioKeys.node(nodeId), queryFn: () => fetchNode(nodeId) });
  const draft = useQuery({
    queryKey: folioKeys.draft(nodeId),
    queryFn: () => fetchDraft(nodeId),
    staleTime: Infinity, // the editor owns the draft while it is open
  });
  if (!node.data || !draft.data) return <PageSpinner />;
  return (
    <Loaded
      node={node.data}
      draft={draft.data}
      onPublish={onPublish}
      extensions={extensions ?? []}
    />
  );
}

type LoadedProps = {
  node: FolioNode;
  draft: FolioDraft;
  onPublish?: Props['onPublish'];
  extensions: ReturnType<typeof folioExtensions>;
};

function Loaded({ node, draft, onPublish, extensions }: LoadedProps) {
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
      ...folioExtensions(),
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
  const editor = useEditor({
    extensions: allExtensions,
    content: draft.content_json,
    onUpdate: ({ editor: e }) => body.change(toFolioDoc(e.getJSON())),
  });
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

  const states = [body.state, header.state];
  const state = states.includes('error')
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
        <S.SaveState role="status" $error={state === 'error'}>
          {t(`folio.editor.state.${state}`)}
        </S.SaveState>
        {onPublish && editor && (
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
        <S.Page>
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
