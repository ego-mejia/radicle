import { useQuery, useQueryClient } from '@tanstack/react-query';
import { createLink, useNavigate, useRouterState } from '@tanstack/react-router';
import {
  Home,
  Inbox,
  ListChecks,
  LogOut,
  Moon,
  Plus,
  Rss,
  Search,
  Shield,
  Star,
  Sun,
  UserRound,
} from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import * as S from '../../../../components/layout/AppSidebar/style';
import { SuiteSwitch } from '../../../../components/layout/SuiteSwitch';
import { Avatar } from '../../../../components/ui/Avatar';
import { Menu } from '../../../../components/ui/Menu';
import { useMe } from '../../../../hooks/useMe';
import { useThemeMode } from '../../../../hooks/useThemeMode';
import { logout } from '../../../../services/api/auth';
import {
  fetchFolioMe,
  fetchSpaces,
  fetchSubmissions,
  folioKeys,
  nodeIdFrom,
  type FolioNode,
} from '../../../../services/api/folio';
import { fetchMyTasks, taskKeys } from '../../../../services/api/folioWork';
import { NewSpaceDialog } from '../NewSpaceDialog';
import * as L from './style';

const NavLink = createLink(S.NavLink);

type Props = { open: boolean; onClose: () => void };

/** The space you are in: from the URL in a space, from the cached page while reading. */
function useCurrentSpace(): string | undefined {
  const client = useQueryClient();
  const path = useRouterState({ select: (s) => s.location.pathname });
  const space = /^\/folio\/s\/([^/]+)/.exec(path);
  if (space?.[1]) return decodeURIComponent(space[1]);
  const page = /^\/folio\/p\/([^/]+)/.exec(path);
  if (page?.[1]) return client.getQueryData<FolioNode>(folioKeys.node(nodeIdFrom(page[1])))?.space;
  return undefined;
}

/** Folio's sidebar (ADR 0044): the same column as Docket's, so the suite switch never moves.
 * It lists where you can go, never the pages of a space; inside a space it only highlights it. */
export function FolioSidebar({ open, onClose }: Props) {
  const { t } = useTranslation();
  const me = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { mode, setPreference } = useThemeMode();
  const [newSpace, setNewSpace] = useState(false);
  const current = useCurrentSpace();
  const { data: folio } = useQuery({ queryKey: folioKeys.me, queryFn: fetchFolioMe });
  const { data: spaces = [] } = useQuery({ queryKey: folioKeys.spaces, queryFn: fetchSpaces });
  const { data: tasks } = useQuery({
    queryKey: taskKeys.list('open'),
    queryFn: () => fetchMyTasks('open'),
    refetchInterval: 60_000,
  });
  const isAdmin = folio?.role === 'admin';
  const { data: pending } = useQuery({
    queryKey: folioKeys.submissions('pending'),
    queryFn: () => fetchSubmissions('pending'),
    enabled: isAdmin,
    refetchInterval: 60_000,
  });
  const dueSoon = (tasks ?? []).filter((x) => x.bucket === 'overdue' || x.bucket === 'today');
  const teamSpaces = spaces.filter((s) => s.kind !== 'personal');

  const signOut = async () => {
    await logout();
    queryClient.clear();
    await navigate({ to: '/login', search: { next: undefined } });
  };

  return (
    <>
      <S.Scrim $open={open} onClick={onClose} />
      <S.Aside $open={open} onClick={(e) => (e.target as HTMLElement).closest('a') && onClose()}>
        <S.Brand>
          <SuiteSwitch current="folio" />
        </S.Brand>

        <S.Section aria-label={t('nav.mainNav')}>
          <NavLink to="/folio" activeOptions={{ exact: true }}>
            <Home />
            <span>{t('folio.nav.home')}</span>
          </NavLink>
          <NavLink to="/folio/search" search={{}}>
            <Search />
            <span>{t('folio.nav.search')}</span>
            <L.Key aria-hidden>/</L.Key>
          </NavLink>
          <NavLink to="/folio/for-you">
            <Rss />
            <span>{t('folio.nav.forYou')}</span>
          </NavLink>
          <NavLink to="/folio/tasks">
            <ListChecks />
            <span>{t('folio.tasks.link')}</span>
            {dueSoon.length > 0 && (
              <L.Count title={t('folio.tasks.dueCount', { count: dueSoon.length })}>
                {dueSoon.length}
              </L.Count>
            )}
          </NavLink>
          {isAdmin && (
            <NavLink to="/folio/approvals">
              <Inbox />
              <span>{t('folio.approvals.link')}</span>
              {!!pending?.length && (
                <L.Count title={t('folio.approvals.pendingCount', { count: pending.length })}>
                  {pending.length}
                </L.Count>
              )}
            </NavLink>
          )}
          <NavLink to="/folio/favorites">
            <Star />
            <span>{t('folio.shortcuts.favorites')}</span>
          </NavLink>
        </S.Section>

        <S.Section aria-label={t('folio.nav.spaces')}>
          <S.SectionTitle>{t('folio.nav.spaces')}</S.SectionTitle>
          {teamSpaces.map((space) => (
            <NavLink
              key={space.key}
              to="/folio/s/$key"
              params={{ key: space.key }}
              data-status={space.key === current ? 'active' : undefined}
              aria-current={space.key === current ? 'page' : undefined}
            >
              <L.Tile $seed={space.key} aria-hidden>
                {space.icon || space.name.slice(0, 1).toUpperCase()}
              </L.Tile>
              <span>{space.name}</span>
            </NavLink>
          ))}
          {(isAdmin || folio?.role === 'creator') && (
            <L.Action type="button" onClick={() => setNewSpace(true)}>
              <Plus aria-hidden />
              <span>{t('folio.newSpace.button')}</span>
            </L.Action>
          )}
        </S.Section>

        <S.Spacer />
        {isAdmin && (
          <S.Section aria-label={t('folio.admin.link')}>
            <NavLink to="/folio/admin">
              <Shield />
              <span>{t('folio.nav.admin')}</span>
            </NavLink>
          </S.Section>
        )}
        <Menu
          align="start"
          trigger={
            <S.Profile aria-label={t('nav.profile')}>
              <Avatar handle={me.handle} name={me.display_name} size={28} />
              <div>
                {me.display_name}
                <small>@{me.handle}</small>
              </div>
            </S.Profile>
          }
          items={[
            {
              key: 'profile',
              label: t('nav.profile'),
              icon: <UserRound />,
              onSelect: () => void navigate({ to: '/me' }),
            },
            {
              key: 'theme',
              label: mode === 'dark' ? t('nav.lightMode') : t('nav.darkMode'),
              icon: mode === 'dark' ? <Sun /> : <Moon />,
              onSelect: () => setPreference(mode === 'dark' ? 'light' : 'dark'),
            },
            {
              key: 'logout',
              label: t('nav.logout'),
              icon: <LogOut />,
              onSelect: () => void signOut(),
            },
          ]}
        />
      </S.Aside>
      <NewSpaceDialog open={newSpace} onOpenChange={setNewSpace} />
    </>
  );
}
