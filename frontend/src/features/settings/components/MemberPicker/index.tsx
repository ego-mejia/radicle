import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Users } from 'lucide-react';
import { useEffect, useId, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../components/ui/Avatar';
import { Button } from '../../../../components/ui/Button';
import { Select } from '../../../../components/ui/Input';
import { accessKeys, putGroupRole } from '../../../../services/api/access';
import { fetchMemberCandidates, putMember } from '../../../../services/api/projects';
import type { ProjectRole } from '../../../../services/api/types';
import { useSettingsMutation } from '../../hooks/useSettingsMutation';
import * as S from './style';

const ROLES: ProjectRole[] = ['admin', 'member', 'viewer'];

type Choice =
  | { kind: 'person'; handle: string; display_name: string; userKind: 'human' | 'agent' | 'system' }
  | { kind: 'group'; name: string; description: string };

const labelOf = (c: Choice) => (c.kind === 'person' ? c.display_name : c.name);

/** Search people, agents and groups, pick a role and add them to the project. */
export function MemberPicker({ projectKey }: { projectKey: string }) {
  const { t } = useTranslation();
  const listId = useId();
  const queryClient = useQueryClient();
  const [text, setText] = useState('');
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [choice, setChoice] = useState<Choice | null>(null);
  const [role, setRole] = useState<ProjectRole>('member');
  useEffect(() => {
    const id = setTimeout(() => setQuery(text), 150);
    return () => clearTimeout(id);
  }, [text]);
  const { data } = useQuery({
    queryKey: ['member-candidates', projectKey, query],
    queryFn: () => fetchMemberCandidates(projectKey, query),
    enabled: open,
    placeholderData: (previous) => previous,
  });
  const options: Choice[] = [
    ...(data?.people ?? []).map((p): Choice => ({
      kind: 'person',
      handle: p.handle,
      display_name: p.display_name,
      userKind: p.kind,
    })),
    ...(data?.groups ?? []).map((g): Choice => ({
      kind: 'group',
      name: g.name,
      description: g.description,
    })),
  ];
  const add = useSettingsMutation(
    projectKey,
    async (c: Choice): Promise<void> => {
      if (c.kind === 'person') await putMember(projectKey, c.handle, role);
      else await putGroupRole(projectKey, c.name, role);
    },
    () => {
      setChoice(null);
      setText('');
      void queryClient.invalidateQueries({ queryKey: ['member-candidates', projectKey] });
      void queryClient.invalidateQueries({ queryKey: accessKeys.groupRoles(projectKey) });
    },
  );
  const pick = (c: Choice) => {
    setChoice(c);
    setText(labelOf(c));
    setOpen(false);
  };
  const people = options.filter((o) => o.kind === 'person');
  const groups = options.filter((o) => o.kind === 'group');
  const row = (c: Choice, i: number) => (
    <S.Option
      key={c.kind === 'person' ? `p:${c.handle}` : `g:${c.name}`}
      id={`${listId}-${i}`}
      role="option"
      aria-selected={i === active}
      onMouseDown={(e) => e.preventDefault()}
      onMouseEnter={() => setActive(i)}
      onClick={() => pick(c)}
    >
      {c.kind === 'person' ? (
        <>
          <Avatar handle={c.handle} name={c.display_name} kind={c.userKind} size={24} />
          <span>
            {c.display_name} <small>@{c.handle}</small>
          </span>
          {c.userKind === 'agent' && <S.Tag>{t('settings.picker.agent')}</S.Tag>}
        </>
      ) : (
        <>
          <S.GroupIcon>
            <Users size={14} />
          </S.GroupIcon>
          <span>
            {c.name} {c.description && <small>{c.description}</small>}
          </span>
          <S.Tag>{t('settings.picker.group')}</S.Tag>
        </>
      )}
    </S.Option>
  );

  return (
    <S.Bar
      onSubmit={(e) => {
        e.preventDefault();
        if (choice) add.mutate(choice);
      }}
    >
      <S.Combo>
        <S.Search
          role="combobox"
          aria-label={t('settings.picker.label')}
          aria-expanded={open}
          aria-controls={listId}
          aria-activedescendant={open && options.length ? `${listId}-${active}` : undefined}
          placeholder={t('settings.picker.placeholder')}
          value={text}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onChange={(e) => {
            setText(e.target.value);
            setChoice(null);
            setActive(0);
            setOpen(true);
          }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') {
              e.preventDefault();
              setOpen(true);
              setActive((a) => Math.min(a + 1, options.length - 1));
            } else if (e.key === 'ArrowUp') {
              e.preventDefault();
              setActive((a) => Math.max(a - 1, 0));
            } else if (e.key === 'Enter' && open && options[active]) {
              e.preventDefault();
              pick(options[active]!);
            } else if (e.key === 'Escape') setOpen(false);
          }}
        />
        {open && (
          <S.List id={listId} role="listbox">
            {options.length === 0 && <S.Empty>{t('settings.picker.empty')}</S.Empty>}
            {people.length > 0 && <S.Heading>{t('settings.picker.people')}</S.Heading>}
            {people.map((c, i) => row(c, i))}
            {groups.length > 0 && <S.Heading>{t('settings.picker.groups')}</S.Heading>}
            {groups.map((c, i) => row(c, people.length + i))}
          </S.List>
        )}
      </S.Combo>
      <Select
        value={role}
        onChange={(e) => setRole(e.target.value as ProjectRole)}
        aria-label={t('settings.role')}
      >
        {ROLES.map((r) => (
          <option key={r} value={r}>
            {t(`projects.roles.${r}`)}
          </option>
        ))}
      </Select>
      <Button type="submit" variant="primary" disabled={!choice || add.isPending}>
        {t('common.add')}
      </Button>
    </S.Bar>
  );
}
