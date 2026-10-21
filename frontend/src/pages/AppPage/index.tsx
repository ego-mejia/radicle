import { Assistant } from '../../features/assistant/components/Assistant';
import { MilestoneCelebration } from '../../features/milestones/components/MilestoneCelebration';
import { Outlet, useParams } from '@tanstack/react-router';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CreateTicketContext, type CreateTicketDefaults } from '../../contexts/createTicket';
import { CreateTicketModal } from '../../features/tickets/components/CreateTicketModal';
import { ShortcutsContext } from '../../contexts/shortcuts';
import { useHotkey } from '../../hooks/useHotkey';
import { usePreferences } from '../../hooks/usePreferences';
import { useSuiteShortcuts } from '../../hooks/useSuiteShortcuts';
import { useThemeMode } from '../../hooks/useThemeMode';
import { GlobalShortcuts } from './components/GlobalShortcuts';
import { Sidebar } from './components/Sidebar';
import { Topbar } from './components/Topbar';
import * as S from './style';

/** Authenticated layout: sidebar, topbar, page content and the create-ticket modal. */
export function AppPage() {
  const { t, i18n } = useTranslation();
  const { prefs } = usePreferences();
  const { setPreference } = useThemeMode();
  // Server preferences win once, when they load; later changes go both ways.
  useEffect(() => {
    if (!prefs) return;
    setPreference(prefs.theme as 'system' | 'light' | 'dark');
    if (prefs.language) void i18n.changeLanguage(prefs.language);
    document.documentElement.dataset.density = prefs.density;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefs]);
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
  useSuiteShortcuts();

  return (
    <ShortcutsContext.Provider value={prefs?.shortcuts ?? true}>
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
        <GlobalShortcuts />
        <Assistant />
        <MilestoneCelebration />
      </CreateTicketContext.Provider>
    </ShortcutsContext.Provider>
  );
}
