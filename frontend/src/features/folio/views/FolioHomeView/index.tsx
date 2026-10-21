import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { fetchFolioMe, folioKeys } from '../../../../services/api/folio';

/** Folio's home until spaces and pages arrive in phase 1. */
export function FolioHomeView() {
  const { t } = useTranslation();
  const { data: me } = useQuery({ queryKey: folioKeys.me, queryFn: fetchFolioMe });
  return (
    <>
      <PageTitle title={t('folio.homeTitle')} subtitle={t('folio.homeSubtitle')} />
      <EmptyState
        plant="seed"
        title={t('folio.emptyTitle')}
        text={me ? t('folio.emptyText', { role: t(`folio.roles.${me.role}`) }) : undefined}
      />
    </>
  );
}
