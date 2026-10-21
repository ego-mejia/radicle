import { useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from '@tanstack/react-router';
import { lazy, Suspense, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useToast } from '../../../../hooks/useToast';
import { folioKeys, nodeIdFrom, nodePath, type FolioNode } from '../../../../services/api/folio';
import { PublishDialog, type Published } from '../../components/PublishDialog';

// TipTap is heavy: it loads only when someone opens the editor.
const PageEditor = lazy(() =>
  import('../../components/PageEditor').then((m) => ({ default: m.PageEditor })),
);

/** The full-screen editor for a page's draft, and publishing it. */
export function FolioEditView() {
  const { t } = useTranslation();
  const { page } = useParams({ from: '/folio/folio/p/$page/edit' });
  const nodeId = nodeIdFrom(page);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const toast = useToast();
  const [publishing, setPublishing] = useState(false);
  const node = () => queryClient.getQueryData<FolioNode>(folioKeys.node(nodeId));

  const published = (result: Published) => {
    if ('status' in result) toast(t('folio.publish.sent'));
    else toast(t('folio.publish.done', { version: result.number }));
    const current = node();
    if (current) void navigate({ to: nodePath(current) });
  };

  return (
    <Suspense fallback={<PageSpinner />}>
      <PageEditor nodeId={nodeId} collab onPublish={() => setPublishing(true)} />
      <PublishDialog
        nodeId={nodeId}
        title={node()?.title ?? ''}
        space={node()?.space}
        open={publishing}
        onOpenChange={setPublishing}
        onPublished={published}
      />
    </Suspense>
  );
}
