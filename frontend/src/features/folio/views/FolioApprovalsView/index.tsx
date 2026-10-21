import { useTranslation } from 'react-i18next';
import { PageTitle } from '../../../../components/ui/PageTitle';

/** The approval queue: what agents sent to publish. */
export function FolioApprovalsView() {
  const { t } = useTranslation();
  return <PageTitle title={t('folio.approvals.title')} />;
}
