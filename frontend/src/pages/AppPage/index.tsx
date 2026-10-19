import { Outlet, useParams } from '@tanstack/react-router';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CreateTicketContext, type CreateTicketDefaults } from '../../contexts/createTicket';
import { CreateTicketModal } from '../../features/tickets/components/CreateTicketModal';
import { useHotkey } from '../../hooks/useHotkey';
import { Sidebar } from './components/Sidebar';
import { Topbar } from './components/Topbar';
import * as S from './style';

/** Authenticated layout: sidebar, topbar, page content and the create-ticket modal. */
export function AppPage() {
  const { t } = useTranslation();
  const params = useParams({ strict: false }) as { key?: string };
  const routeProject =
    params.key && !params.key.includes('-') ? params.key : params.key?.split('-')[0];
  const [createDefaults, setCreateDefaults] = useState<CreateTicketDefaults | null>(null);
  const [navOpen, setNavOpen] = useState(false);

  const openCreate = useCallback(
    (defaults?: CreateTicketDefaults) =>
      setCreateDefaults({ project: routeProject?.toUpperCase(), ...defaults }),
    [routeProject],
  );
  const openCreateShortcut = useCallback(() => openCreate(), [openCreate]);
  useHotkey('c', openCreateShortcut);

  return (
    <CreateTicketContext.Provider value={openCreate}>
      <S.SkipLink href="#content">{t('nav.skip')}</S.SkipLink>
      <S.Shell>
        <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />
        <S.Main>
          <Topbar project={routeProject?.toUpperCase()} onMenu={() => setNavOpen(true)} />
          <S.Content id="content" tabIndex={-1}>
            <Outlet />
          </S.Content>
        </S.Main>
      </S.Shell>
      {createDefaults && (
        <CreateTicketModal defaults={createDefaults} onClose={() => setCreateDefaults(null)} />
      )}
    </CreateTicketContext.Provider>
  );
}
