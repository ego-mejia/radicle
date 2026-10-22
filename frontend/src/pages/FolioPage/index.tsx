import { useQuery } from '@tanstack/react-query';
import { Outlet } from '@tanstack/react-router';
import { Menu as MenuIcon, MessagesSquare } from 'lucide-react';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AppShell } from '../../components/layout/AppSidebar/style';
import { IconButton } from '../../components/ui/Button';
import { ChatPanel } from '../../features/folio/components/ChatPanel';
import { FolioSidebar } from '../../features/folio/components/FolioSidebar';
import { TopbarSearch } from '../../features/folio/components/TopbarSearch';
import { WriteButton } from '../../features/folio/views/FolioHomeView/components/WriteButton';
import { NotificationBell } from '../../features/notifications/components/NotificationBell';
import { useHotkey } from '../../hooks/useHotkey';
import { useSuiteShortcuts } from '../../hooks/useSuiteShortcuts';
import { fetchFolioMe, folioKeys } from '../../services/api/folio';
import { chatKeys, fetchChatAvailability } from '../../services/api/folioChat';
import * as S from './style';

/** Folio's shell (ADR 0044): the sidebar on the left, as in Docket, and a slim bar with
 * search, notifications and Write over the content. */
export function FolioPage() {
  const { t } = useTranslation();
  const [navOpen, setNavOpen] = useState(false);
  const { data: folio } = useQuery({ queryKey: folioKeys.me, queryFn: fetchFolioMe });
  useSuiteShortcuts();
  const { data: chat } = useQuery({
    queryKey: chatKeys.availability,
    queryFn: fetchChatAvailability,
    staleTime: 5 * 60_000,
  });
  const [chatOpen, setChatOpen] = useState(false);
  const toggleChat = useCallback(() => setChatOpen((open) => !open), []);
  const closeChat = useCallback(() => setChatOpen(false), []);
  useHotkey('a', toggleChat, !!chat?.available);
  const writer = folio?.role === 'admin' || folio?.role === 'creator';

  return (
    <>
      <S.SkipLink href="#content">{t('nav.skip')}</S.SkipLink>
      <AppShell>
        <FolioSidebar open={navOpen} onClose={() => setNavOpen(false)} />
        <S.Main>
          <S.Bar>
            <S.MenuButton>
              <IconButton label={t('folio.nav.menu')} onClick={() => setNavOpen(true)}>
                <MenuIcon />
              </IconButton>
            </S.MenuButton>
            <S.Search>
              <TopbarSearch />
            </S.Search>
            <S.Actions>
              {chat?.available && (
                <S.Ask
                  type="button"
                  onClick={toggleChat}
                  aria-expanded={chatOpen}
                  title={t('folio.chat.shortcut')}
                >
                  <MessagesSquare aria-hidden />
                  {t('folio.chat.open')}
                </S.Ask>
              )}
              <NotificationBell />
              {writer && <WriteButton />}
            </S.Actions>
          </S.Bar>
          <S.Content id="content" tabIndex={-1}>
            <Outlet />
          </S.Content>
        </S.Main>
      </AppShell>
      {chat?.available && <ChatPanel open={chatOpen} onClose={closeChat} />}
    </>
  );
}
