import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, Outlet, useNavigate } from '@tanstack/react-router';
import { Inbox, LogOut, Shield, UserRound } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { SuiteSwitch } from '../../components/layout/SuiteSwitch';
import { Avatar } from '../../components/ui/Avatar';
import { Menu } from '../../components/ui/Menu';
import { TopbarSearch } from '../../features/folio/components/TopbarSearch';
import { useMe } from '../../hooks/useMe';
import { useSuiteShortcuts } from '../../hooks/useSuiteShortcuts';
import { logout } from '../../services/api/auth';
import { fetchFolioMe, fetchSubmissions, folioKeys } from '../../services/api/folio';
import * as S from './style';

/** Folio's shell (Folio 0.5): the suite switch, search (from phase 1) and your avatar. */
export function FolioPage() {
  const { t } = useTranslation();
  const me = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: folio } = useQuery({ queryKey: folioKeys.me, queryFn: fetchFolioMe });
  const { data: pending } = useQuery({
    queryKey: folioKeys.submissions('pending'),
    queryFn: () => fetchSubmissions('pending'),
    enabled: folio?.role === 'admin',
    refetchInterval: 60_000,
  });
  useSuiteShortcuts();

  const signOut = async () => {
    await logout();
    queryClient.clear();
    await navigate({ to: '/login', search: { next: undefined } });
  };

  return (
    <>
      <S.SkipLink href="#content">{t('nav.skip')}</S.SkipLink>
      <S.Shell>
        <S.Bar>
          <S.BarInner>
            <SuiteSwitch current="folio" />
            <S.Search>
              <TopbarSearch />
            </S.Search>
            {folio?.role === 'admin' && (
              <S.AdminLink as={Link} to="/folio/approvals">
                <Inbox aria-hidden />
                {t('folio.approvals.link')}
                {!!pending?.length && (
                  <S.Count title={t('folio.approvals.pendingCount', { count: pending.length })}>
                    {pending.length}
                  </S.Count>
                )}
              </S.AdminLink>
            )}
            {folio?.role === 'admin' && (
              <S.AdminLink as={Link} to="/folio/admin">
                <Shield aria-hidden />
                {t('folio.admin.link')}
              </S.AdminLink>
            )}
            <Menu
              align="end"
              trigger={
                <S.Profile aria-label={t('nav.profile')}>
                  <Avatar handle={me.handle} name={me.display_name} size={36} />
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
                  key: 'logout',
                  label: t('nav.logout'),
                  icon: <LogOut />,
                  onSelect: () => void signOut(),
                },
              ]}
            />
          </S.BarInner>
        </S.Bar>
        <S.Content id="content" tabIndex={-1}>
          <Outlet />
        </S.Content>
      </S.Shell>
    </>
  );
}
