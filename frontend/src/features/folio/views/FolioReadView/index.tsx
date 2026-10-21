import { useTranslation } from 'react-i18next';
import { PageTitle } from '../../../../components/ui/PageTitle';

/** Reading a page: magazine by default, focus mode on demand. */
export function FolioReadView() {
  const { t } = useTranslation();
  return <PageTitle title={t('folio.reader.title')} />;
}
