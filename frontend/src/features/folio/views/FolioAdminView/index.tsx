import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Globe, Trash2, User, Users } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../components/ui/Button';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { Field } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { SettingsCard, SettingsParts as S } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  type FolioGrant,
  type FolioGrantIn,
  fetchFolioGrants,
  fetchFolioMe,
  folioKeys,
  removeFolioGrant,
  setFolioGrant,
} from '../../../../services/api/folio';
import * as F from './style';

const ROLES: FolioGrant['role'][] = ['reader', 'creator', 'admin'];
const ICONS = { everyone: <Globe />, group: <Users />, user: <User /> };

function GrantRow({ grant }: { grant: FolioGrant }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: folioKeys.grants });
    void queryClient.invalidateQueries({ queryKey: folioKeys.me });
  };
  const change = useMutation({
    mutationFn: (role: FolioGrant['role']) =>
      setFolioGrant({ grantee_type: grant.grantee_type, grantee: grant.grantee, role }),
    onSuccess: refresh,
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const remove = useMutation({
    mutationFn: () => removeFolioGrant(grant.id),
    onSuccess: refresh,
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const name =
    grant.grantee_type === 'everyone'
      ? t('folio.admin.everyone')
      : grant.grantee_type === 'user'
        ? `@${grant.grantee}`
        : grant.grantee;
  return (
    <S.Row>
      <S.Grow>
        <F.Kind aria-hidden>{ICONS[grant.grantee_type]}</F.Kind>
        {name}
        <small>{t(`folio.admin.kinds.${grant.grantee_type}`)}</small>
      </S.Grow>
      <F.Role>
        <Select
          aria-label={t('folio.admin.roleOf', { name })}
          value={grant.role}
          onChange={(e) => change.mutate(e.target.value as FolioGrant['role'])}
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {t(`folio.roles.${r}`)}
            </option>
          ))}
        </Select>
      </F.Role>
      <IconButton label={t('folio.admin.remove', { name })} onClick={() => remove.mutate()}>
        <Trash2 />
      </IconButton>
    </S.Row>
  );
}

function AddGrant() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [type, setType] = useState<FolioGrantIn['grantee_type']>('group');
  const [grantee, setGrantee] = useState('');
  const [role, setRole] = useState<FolioGrant['role']>('creator');
  const add = useMutation({
    mutationFn: () =>
      setFolioGrant({
        grantee_type: type,
        grantee: type === 'everyone' ? null : grantee.trim().replace(/^@/, ''),
        role,
      }),
    onSuccess: () => {
      setGrantee('');
      void queryClient.invalidateQueries({ queryKey: folioKeys.grants });
      toast(t('folio.admin.saved'));
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const ready = type === 'everyone' || grantee.trim() !== '';
  return (
    <S.Inline
      onSubmit={(e) => {
        e.preventDefault();
        if (ready) add.mutate();
      }}
    >
      <Field label={t('folio.admin.type')}>
        <Select value={type} onChange={(e) => setType(e.target.value as typeof type)}>
          {(['group', 'user', 'everyone'] as const).map((k) => (
            <option key={k} value={k}>
              {t(`folio.admin.kinds.${k}`)}
            </option>
          ))}
        </Select>
      </Field>
      {type !== 'everyone' && (
        <Field label={t(`folio.admin.granteeLabel.${type}`)}>
          <Input
            value={grantee}
            onChange={(e) => setGrantee(e.target.value)}
            placeholder={type === 'user' ? '@handle' : 'equipo-docs'}
          />
        </Field>
      )}
      <Field label={t('folio.admin.role')}>
        <Select value={role} onChange={(e) => setRole(e.target.value as FolioGrant['role'])}>
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {t(`folio.roles.${r}`)}
            </option>
          ))}
        </Select>
      </Field>
      <Button type="submit" size="sm" disabled={!ready || add.isPending}>
        {t('common.add')}
      </Button>
    </S.Inline>
  );
}

/** Folio, Admin, Global roles (Folio 0.5): who reads, creates or administers Folio. */
export function FolioAdminView() {
  const { t } = useTranslation();
  const { data: me } = useQuery({ queryKey: folioKeys.me, queryFn: fetchFolioMe });
  const isAdmin = me?.role === 'admin';
  const { data: grants } = useQuery({
    queryKey: folioKeys.grants,
    queryFn: fetchFolioGrants,
    enabled: isAdmin,
  });
  if (me && !isAdmin) return <EmptyState plant="seed" title={t('folio.admin.forbidden')} />;
  return (
    <>
      <PageTitle title={t('folio.admin.title')} subtitle={t('folio.admin.subtitle')} />
      <SettingsCard title={t('folio.admin.grants')} help={t('folio.admin.help')}>
        {grants ? (
          <S.Rows>
            {grants.map((g) => (
              <GrantRow key={g.id} grant={g} />
            ))}
            {grants.length === 0 && <S.Muted>{t('folio.admin.none')}</S.Muted>}
            <AddGrant />
          </S.Rows>
        ) : (
          <PageSpinner />
        )}
      </SettingsCard>
    </>
  );
}
