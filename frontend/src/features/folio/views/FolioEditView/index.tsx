import { useTranslation } from 'react-i18next';
import { PageTitle } from '../../../../components/ui/PageTitle';

/** The full-screen editor for a page's draft. */
export function FolioEditView() {
  const { t } = useTranslation();
  return <PageTitle title={t('folio.editor.title')} />;
}
