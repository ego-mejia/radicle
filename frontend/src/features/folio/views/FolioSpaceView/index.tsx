import { useTranslation } from 'react-i18next';
import { PageTitle } from '../../../../components/ui/PageTitle';

/** A space: its cover, the page tree and its blog posts. */
export function FolioSpaceView() {
  const { t } = useTranslation();
  return <PageTitle title={t('folio.space.title')} />;
}
