import * as Dialog from '@radix-ui/react-dialog';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from '@tanstack/react-router';
import {
  Filter,
  FolderKanban,
  Moon,
  Plus,
  Settings,
  Ticket as TicketIcon,
  Languages,
} from 'lucide-react';
import { useContext, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CreateTicketContext } from '../../../../contexts/createTicket';
import { useMe } from '../../../../hooks/useMe';
import { useThemeMode } from '../../../../hooks/useThemeMode';
import { asTicketKey } from '../../../../lib/format';
import { recentTickets } from '../../../../lib/ticketCommands';
import { searchTickets } from '../../../../services/api/tickets';
import { fetchFilters, workKeys } from '../../../../services/api/work';
import * as S from './style';

type Item = {
  id: string;
  group: 'tickets' | 'projects' | 'filters' | 'actions' | 'recent';
  label: string;
  hint?: string;
  icon: React.ReactNode;
  run: () => void;
};

function useDebounced(value: string, ms: number): string {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

/** ⌘K: tickets (by key or title), projects, saved filters and actions in one list. */
export function CommandPalette({ onClose }: { onClose: () => void }) {
  const { t, i18n } = useTranslation();
  const me = useMe();
  const navigate = useNavigate();
  const params = useParams({ strict: false }) as { key?: string };
  const openCreate = useContext(CreateTicketContext);
  const { mode, setPreference } = useThemeMode();
  const [text, setText] = useState('');
  const [active, setActive] = useState(0);
  const term = useDebounced(text.trim(), 150);
  const project = params.key?.split('-')[0]?.toUpperCase();

  const { data: found } = useQuery({
    queryKey: ['palette', term],
    queryFn: () =>
      searchTickets(`title ~ ${JSON.stringify(term)} ORDER BY updated DESC`, undefined, 6),
    enabled: term.length >= 2 && !asTicketKey(term),
  });
  const { data: filters } = useQuery({
    queryKey: workKeys.filters(),
    queryFn: () => fetchFilters(),
  });

  const items = useMemo<Item[]>(() => {
    const go = (fn: () => void) => () => {
      onClose();
      fn();
    };
    const lower = term.toLowerCase();
    const matches = (s: string) => !lower || s.toLowerCase().includes(lower);
    const list: Item[] = [];
    // The exact key and the recents follow the typed text right away, not the debounce.
    const key = asTicketKey(text.trim());
    if (key) {
      list.push({
        id: `key-${key}`,
        group: 'tickets',
        label: t('palette.open', { key }),
        icon: <TicketIcon />,
        run: go(() => void navigate({ to: '/t/$key', params: { key } })),
      });
    }
    if (!text.trim()) {
      for (const r of recentTickets()) {
        list.push({
          id: `recent-${r.key}`,
          group: 'recent',
          label: r.title,
          hint: r.key,
          icon: <TicketIcon />,
          run: go(() => void navigate({ to: '/t/$key', params: { key: r.key } })),
        });
      }
    }
    for (const ticket of found?.items ?? []) {
      list.push({
        id: `t-${ticket.key}`,
        group: 'tickets',
        label: ticket.title,
        hint: ticket.key,
        icon: <TicketIcon />,
        run: go(() => void navigate({ to: '/t/$key', params: { key: ticket.key } })),
      });
    }
    for (const p of me.projects ?? []) {
      if (!matches(`${p.key} ${p.name}`)) continue;
      list.push({
        id: `p-${p.key}`,
        group: 'projects',
        label: p.name,
        hint: p.key,
        icon: <FolderKanban />,
        run: go(() => void navigate({ to: '/p/$key/board', params: { key: p.key }, search: {} })),
      });
    }
    for (const f of filters ?? []) {
      if (!matches(f.name)) continue;
      const target = f.project ?? project ?? me.projects?.[0]?.key;
      if (!target) continue;
      list.push({
        id: `f-${f.id}`,
        group: 'filters',
        label: f.name,
        hint: f.rql,
        icon: <Filter />,
        run: go(
          () =>
            void navigate({ to: '/p/$key/list', params: { key: target }, search: { q: f.rql } }),
        ),
      });
    }
    const actions: Item[] = [
      {
        id: 'a-create',
        group: 'actions',
        label: t('palette.create'),
        hint: 'c',
        icon: <Plus />,
        run: go(() => openCreate()),
      },
      {
        id: 'a-theme',
        group: 'actions',
        label: mode === 'dark' ? t('palette.light') : t('palette.dark'),
        icon: <Moon />,
        run: go(() => setPreference(mode === 'dark' ? 'light' : 'dark')),
      },
      {
        id: 'a-language',
        group: 'actions',
        label: i18n.language.startsWith('es') ? 'English' : 'Español',
        icon: <Languages />,
        run: go(() => void i18n.changeLanguage(i18n.language.startsWith('es') ? 'en' : 'es')),
      },
      ...(project
        ? [
            {
              id: 'a-settings',
              group: 'actions' as const,
              label: t('palette.settings', { key: project }),
              icon: <Settings />,
              run: go(
                () =>
                  void navigate({ to: '/p/$key/settings', params: { key: project }, search: {} }),
              ),
            },
          ]
        : []),
    ];
    list.push(...actions.filter((a) => matches(a.label)));
    return list;
  }, [
    text,
    term,
    found,
    filters,
    me.projects,
    project,
    mode,
    t,
    i18n,
    navigate,
    onClose,
    openCreate,
    setPreference,
  ]);

  useEffect(() => setActive(0), [text]);
  const groups = ['recent', 'tickets', 'projects', 'filters', 'actions'] as const;

  return (
    <Dialog.Root open onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <S.Overlay />
        <S.Content aria-describedby={undefined}>
          <Dialog.Title className="sr-only">{t('palette.title')}</Dialog.Title>
          <S.Input
            autoFocus
            role="combobox"
            aria-expanded
            aria-controls="palette-list"
            aria-activedescendant={items[active] ? `palette-${items[active]!.id}` : undefined}
            placeholder={t('palette.placeholder')}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                e.preventDefault();
                setActive((i) => Math.min(items.length - 1, i + 1));
              } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setActive((i) => Math.max(0, i - 1));
              } else if (e.key === 'Enter') {
                e.preventDefault();
                items[active]?.run();
              }
            }}
          />
          <S.List id="palette-list" role="listbox" aria-label={t('palette.title')}>
            {items.length === 0 && <S.Empty>{t('palette.empty')}</S.Empty>}
            {groups.map((group) => {
              const inGroup = items.filter((i) => i.group === group);
              if (!inGroup.length) return null;
              return (
                <div key={group} role="group" aria-label={t(`palette.groups.${group}`)}>
                  <S.Group>{t(`palette.groups.${group}`)}</S.Group>
                  {inGroup.map((item) => {
                    const index = items.indexOf(item);
                    return (
                      <S.Item
                        key={item.id}
                        id={`palette-${item.id}`}
                        role="option"
                        aria-selected={index === active}
                        $active={index === active}
                        onMouseEnter={() => setActive(index)}
                        onClick={item.run}
                      >
                        {item.icon}
                        <span>{item.label}</span>
                        {item.hint && <S.Hint>{item.hint}</S.Hint>}
                      </S.Item>
                    );
                  })}
                </div>
              );
            })}
          </S.List>
        </S.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
