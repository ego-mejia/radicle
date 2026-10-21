import { useTranslation } from 'react-i18next';
import { PageTitle } from '../../../../components/ui/PageTitle';

/** A page's versions, their diff and restore. */
export function FolioHistoryView() {
  const { t } = useTranslation();
  return <PageTitle title={t('folio.history.title')} />;
}
