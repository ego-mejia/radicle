import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, createLink } from '@tanstack/react-router';
import { FolderKanban, Inbox, LayoutDashboard, LogOut, Shield, UserRound } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Logo } from '../../../../components/icons/Logo';
import { Avatar } from '../../../../components/ui/Avatar';
import { Menu } from '../../../../components/ui/Menu';
import { useMe } from '../../../../hooks/useMe';
import { logout } from '../../../../services/api/auth';
import { fetchProjects, projectKeys } from '../../../../services/api/projects';
import * as S from './style';

const Brand = createLink(S.Brand);
const NavLink = createLink(S.NavLink);

type Props = { open: boolean; onClose: () => void };

export function Sidebar({ open, onClose }: Props) {
  const { t } = useTranslation();
  const me = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: projects = [] } = useQuery({
    queryKey: projectKeys.list(false),
    queryFn: () => fetchProjects(false),
  });

  const signOut = async () => {
    await logout();
    queryClient.clear();
    await navigate({ to: '/login', search: { next: undefined } });
  };

  return (
    <>
      <S.Scrim $open={open} onClick={onClose} />
      <S.Aside $open={open} onClick={(e) => (e.target as HTMLElement).closest('a') && onClose()}>
        <Brand to="/">
          <Logo size={26} />
          {t('app.name')}
        </Brand>

        <S.Section aria-label={t('nav.mainNav')}>
          <NavLink to="/" activeOptions={{ exact: true }} data-tour="nav.projects">
            <FolderKanban />
            <span>{t('nav.projects')}</span>
          </NavLink>
          <NavLink to="/me/tickets" search={{ t: undefined }} data-tour="nav.my-tickets">
            <Inbox />
            <span>{t('nav.myTickets')}</span>
          </NavLink>
          <NavLink to="/dashboards" data-tour="nav.dashboards">
            <LayoutDashboard />
            <span>{t('nav.dashboards')}</span>
          </NavLink>
          {me.is_instance_admin && (
            <NavLink to="/admin" search={{ tab: undefined }} data-tour="nav.admin">
              <Shield />
              <span>{t('nav.admin')}</span>
            </NavLink>
          )}
        </S.Section>

        {projects.length > 0 && (
          <S.Section aria-label={t('nav.projects')}>
            <S.SectionTitle>{t('nav.projects')}</S.SectionTitle>
            {projects.map((project) => (
              <NavLink
                key={project.key}
                to="/p/$key/board"
                params={{ key: project.key }}
                search={{}}
                activeOptions={{ includeSearch: false }}
              >
                <S.ProjectKey>{project.key}</S.ProjectKey>
                <span>{project.name}</span>
              </NavLink>
            ))}
          </S.Section>
        )}

        <S.Spacer />
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
              key: 'logout',
              label: t('nav.logout'),
              icon: <LogOut />,
              onSelect: () => void signOut(),
            },
          ]}
        />
      </S.Aside>
    </>
  );
}
