import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useRouterState } from '@tanstack/react-router';
import { Menu as MenuIcon, Moon, Plus, Sun } from 'lucide-react';
import { useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../components/ui/Button';
import { Input } from '../../../../components/ui/Input';
import { NotificationBell } from '../../../../features/notifications/components/NotificationBell';
import { useCreateTicket } from '../../../../hooks/useCreateTicket';
import { useHotkey } from '../../../../hooks/useHotkey';
import { useThemeMode } from '../../../../hooks/useThemeMode';
import { asTicketKey } from '../../../../lib/format';
import { fetchProjects, projectKeys } from '../../../../services/api/projects';
import * as S from './style';

type Props = { project?: string; onMenu: () => void };

const PAGES: Record<string, string> = {
  board: 'nav.board',
  list: 'nav.list',
  milestones: 'nav.milestones',
  settings: 'nav.settings',
};

export function Topbar({ project, onMenu }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { mode, setPreference } = useThemeMode();
  const openCreate = useCreateTicket();
  const [query, setQuery] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);
  const { data: projects = [] } = useQuery({
    queryKey: projectKeys.list(false),
    queryFn: () => fetchProjects(false),
  });

  const focusSearch = useCallback(() => searchRef.current?.focus(), []);
  useHotkey('/', focusSearch);

  const current = projects.find((p) => p.key === project);
  const segments = pathname.split('/').filter(Boolean);
  const page = segments[0] === 'p' ? PAGES[segments[2] ?? ''] : undefined;
  const ticketKey = segments[0] === 't' ? segments[1]?.toUpperCase() : undefined;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = query.trim();
    if (!text) return;
    const key = asTicketKey(text);
    if (key) {
      void navigate({ to: '/t/$key', params: { key } });
    } else {
      const target = project ?? projects[0]?.key;
      if (target)
        void navigate({ to: '/p/$key/list', params: { key: target }, search: { q: text } });
    }
    setQuery('');
    searchRef.current?.blur();
  };

  return (
    <S.Bar>
      <S.MenuButton>
        <IconButton label={t('nav.mainNav')} onClick={onMenu}>
          <MenuIcon />
        </IconButton>
      </S.MenuButton>
      <S.Crumbs aria-label={t('nav.breadcrumb')}>
        <Link to="/">{t('nav.projects')}</Link>
        {current && (
          <>
            <span aria-hidden>/</span>
            <Link to="/p/$key/board" params={{ key: current.key }} search={{}}>
              {current.name}
            </Link>
          </>
        )}
        {page && (
          <>
            <span aria-hidden>/</span>
            <strong>{t(page)}</strong>
          </>
        )}
        {ticketKey && (
          <>
            <span aria-hidden>/</span>
            <strong>{ticketKey}</strong>
          </>
        )}
      </S.Crumbs>
      <S.Search onSubmit={submit} role="search" data-tour="topbar.search">
        <Input
          ref={searchRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('nav.searchPlaceholder')}
          aria-label={t('common.search')}
        />
      </S.Search>
      <S.Actions>
        <Button
          variant="primary"
          onClick={() => openCreate()}
          title="C"
          data-tour="topbar.create-ticket"
        >
          <Plus />
          <span className="label">{t('nav.createTicket')}</span>
        </Button>
        <NotificationBell />
        <IconButton
          label={mode === 'dark' ? t('nav.lightMode') : t('nav.darkMode')}
          onClick={() => setPreference(mode === 'dark' ? 'light' : 'dark')}
        >
          {mode === 'dark' ? <Sun /> : <Moon />}
        </IconButton>
      </S.Actions>
    </S.Bar>
  );
}
