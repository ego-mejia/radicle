import { useParams } from '@tanstack/react-router';
import { lazy, Suspense } from 'react';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { nodeIdFrom } from '../../../../services/api/folio';

// TipTap is heavy: it loads only when someone opens the editor.
const PageEditor = lazy(() =>
  import('../../components/PageEditor').then((m) => ({ default: m.PageEditor })),
);

/** The full-screen editor for a page's draft. */
export function FolioEditView() {
  const { page } = useParams({ from: '/folio/folio/p/$page/edit' });
  return (
    <Suspense fallback={<PageSpinner />}>
      <PageEditor nodeId={nodeIdFrom(page)} />
    </Suspense>
  );
}
