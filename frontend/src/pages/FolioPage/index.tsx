import { useQueryClient } from '@tanstack/react-query';
import { Outlet, useNavigate } from '@tanstack/react-router';
import { LogOut, UserRound } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { SuiteSwitch } from '../../components/layout/SuiteSwitch';
import { Avatar } from '../../components/ui/Avatar';
import { Input } from '../../components/ui/Input';
import { Menu } from '../../components/ui/Menu';
import { useMe } from '../../hooks/useMe';
import { useSuiteShortcuts } from '../../hooks/useSuiteShortcuts';
import { logout } from '../../services/api/auth';
import * as S from './style';

/** Folio's shell (Folio 0.5): the suite switch, search (from phase 1) and your avatar. */
export function FolioPage() {
  const { t } = useTranslation();
  const me = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
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
              <Input
                type="search"
                disabled
                aria-label={t('folio.search')}
                placeholder={t('folio.searchSoon')}
              />
            </S.Search>
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
