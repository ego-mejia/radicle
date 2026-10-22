import { useQuery } from '@tanstack/react-query';
import { useParams } from '@tanstack/react-router';
import { ArrowLeft } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { fetchSpace, folioKeys } from '../../../../services/api/folio';
import { ExportMenu } from '../../components/ExportMenu';
import { SpacePage } from '../../components/SpacePage';
import { SpaceSectionsEditor } from '../../components/SpaceSectionsEditor';
import { SpaceSettings } from '../../components/SpaceSettings';
import * as S from './style';

type Tab = 'pages' | 'sections' | 'settings';

/** "Manage" (RAD-57): the space's admin mode, with its pages and tree, which sections the
 * portada shows, and its settings. */
export function FolioSpaceAdminView() {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const { key } = useParams({ strict: false }) as { key: string };
  const [tab, setTab] = useState<Tab>('pages');
  const space = useQuery({ queryKey: folioKeys.space(key), queryFn: () => fetchSpace(key) });
  if (space.isPending) return <PageSpinner />;
  if (space.isError)
    return <EmptyState title={t('folio.space.notFound')} text={errorMessage(space.error)} />;
  const s = space.data;
  const isAdmin = s.permissions.includes('admin');
  const tabs: { id: Tab; label: string }[] = [
    { id: 'pages', label: t('folio.spaceAdmin.tabs.pages') },
    ...(isAdmin
      ? [
          { id: 'sections' as const, label: t('folio.spaceAdmin.tabs.sections') },
          { id: 'settings' as const, label: t('folio.spaceAdmin.tabs.settings') },
        ]
      : []),
  ];

  return (
    <S.Wrap>
      <S.Head>
        <S.Back to={`/folio/s/${s.key}`}>
          <ArrowLeft aria-hidden />
          {t('folio.spaceAdmin.back', { space: s.name })}
        </S.Back>
        <h1>{t('folio.spaceAdmin.title', { space: s.name })}</h1>
        <Tabs label={t('folio.spaceAdmin.tabsLabel')} tabs={tabs} value={tab} onChange={setTab} />
      </S.Head>
      {tab === 'pages' && <SpacePage spaceKey={s.key} />}
      {tab === 'sections' && (
        <S.Body>
          <SpaceSectionsEditor space={s.key} />
        </S.Body>
      )}
      {tab === 'settings' && (
        <S.Body>
          <S.Settings>
            <p>{t('folio.spaceAdmin.settingsHint')}</p>
            <S.Row>
              <SpaceSettings space={s} />
              {s.permissions.includes('export') && <ExportMenu target={{ space: s.key }} />}
            </S.Row>
          </S.Settings>
        </S.Body>
      )}
    </S.Wrap>
  );
}
