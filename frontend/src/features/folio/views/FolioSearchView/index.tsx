import { useTranslation } from 'react-i18next';
import { PageTitle } from '../../../../components/ui/PageTitle';

/** Hybrid search with filters and the RQL bar. */
export function FolioSearchView() {
  const { t } = useTranslation();
  return <PageTitle title={t('folio.searchPage.title')} />;
}
