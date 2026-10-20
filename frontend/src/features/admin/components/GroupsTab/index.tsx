import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronRight, Trash2, Users, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../components/ui/Avatar';
import { Button, IconButton } from '../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { Field } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { SettingsCard, SettingsParts as S } from '../../../../components/ui/SettingsCard';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  accessKeys,
  addGroupMember,
  createGroup,
  deleteGroup,
  fetchGroup,
  fetchGroups,
  removeGroupMember,
} from '../../../../services/api/access';
import * as G from './style';

function GroupMembers({ name }: { name: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [handle, setHandle] = useState('');
  const { data } = useQuery({ queryKey: accessKeys.group(name), queryFn: () => fetchGroup(name) });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: accessKeys.groups });
  const add = useMutation({
    mutationFn: (h: string) => addGroupMember(name, h),
    onSuccess: () => {
      setHandle('');
      refresh();
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const remove = useMutation({
    mutationFn: (h: string) => removeGroupMember(name, h),
    onSuccess: refresh,
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  return (
    <S.Rows>
      {data?.members.map((m) => (
        <S.Row key={m.handle}>
          <S.Grow>
            <Avatar handle={m.handle} name={m.display_name} kind={m.kind} size={22} />
            {m.display_name} <small>@{m.handle}</small>
          </S.Grow>
          <IconButton
            label={t('admin.removeFromGroup', { handle: m.handle, group: name })}
            onClick={() => remove.mutate(m.handle)}
          >
            <X />
          </IconButton>
        </S.Row>
      ))}
      <S.Inline
        onSubmit={(e) => {
          e.preventDefault();
          if (handle.trim()) add.mutate(handle.trim().replace(/^@/, ''));
        }}
      >
        <Field label={t('admin.addToGroup', { group: name })}>
          <Input value={handle} onChange={(e) => setHandle(e.target.value)} placeholder="@handle" />
        </Field>
        <Button type="submit" size="sm" disabled={!handle.trim()}>
          {t('common.add')}
        </Button>
      </S.Inline>
    </S.Rows>
  );
}

/** Instance groups: humans and agents that join projects together. */
export function GroupsTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [open, setOpen] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const { data: groups = [] } = useQuery({ queryKey: accessKeys.groups, queryFn: fetchGroups });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: accessKeys.groups });
  const create = useMutation({
    mutationFn: () => createGroup({ name: name.trim(), description }),
    onSuccess: (g) => {
      setName('');
      setDescription('');
      setOpen(g.name);
      refresh();
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const remove = useMutation({
    mutationFn: deleteGroup,
    onSuccess: refresh,
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  return (
    <SettingsCard title={t('admin.groups')} help={t('admin.groupsHelp')}>
      <S.Rows>
        {groups.map((g) => {
          const expanded = open === g.name;
          return (
            <G.Group key={g.name} $open={expanded}>
              <G.Header>
                <G.Toggle
                  type="button"
                  onClick={() => setOpen(expanded ? null : g.name)}
                  aria-expanded={expanded}
                >
                  <G.Chevron $open={expanded}>
                    <ChevronRight size={16} />
                  </G.Chevron>
                  <G.Icon>
                    <Users size={16} />
                  </G.Icon>
                  <G.Text>
                    <strong>{g.name}</strong>
                    {g.description && <small>{g.description}</small>}
                  </G.Text>
                  <G.Count>{t('settings.groupMembers', { count: g.member_count })}</G.Count>
                </G.Toggle>
                <IconButton
                  label={t('admin.deleteGroup', { group: g.name })}
                  onClick={() => setDeleting(g.name)}
                >
                  <Trash2 />
                </IconButton>
              </G.Header>
              {expanded && (
                <G.Members>
                  <GroupMembers name={g.name} />
                </G.Members>
              )}
            </G.Group>
          );
        })}
      </S.Rows>
      <S.Inline
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) create.mutate();
        }}
      >
        <Field label={t('admin.groupName')}>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="legal-team" />
        </Field>
        <Field label={t('admin.groupDescription')}>
          <Input value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <Button type="submit" variant="primary" disabled={!name.trim()}>
          {t('admin.newGroup')}
        </Button>
      </S.Inline>
      <ConfirmDialog
        open={Boolean(deleting)}
        title={t('admin.deleteGroup', { group: deleting ?? '' })}
        message={t('admin.deleteGroupConfirm')}
        confirmLabel={t('common.delete')}
        onConfirm={() => {
          if (deleting) remove.mutate(deleting);
          setDeleting(null);
        }}
        onCancel={() => setDeleting(null)}
      />
    </SettingsCard>
  );
}
