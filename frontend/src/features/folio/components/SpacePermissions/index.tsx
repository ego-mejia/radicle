import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Trash2 } from 'lucide-react';
import { type FormEvent, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Input } from '../../../../components/ui/Input';
import { Spinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  fetchSpaceGrants,
  setSpaceGrants,
  spaceKeys,
  type SpaceGrant,
  type SpacePermission,
} from '../../../../services/api/folioSpaces';
import * as S from './style';

const PERMISSIONS: SpacePermission[] = [
  'view',
  'comment',
  'create',
  'delete_own',
  'delete_any',
  'export',
  'admin',
];
type Kind = SpaceGrant['grantee_type'];

/** Who may do what in the space (RAD-57, Manage › Permissions). `admin` includes the rest. */
export function SpacePermissions({ space }: { space: string }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const client = useQueryClient();
  const grants = useQuery({
    queryKey: spaceKeys.grants(space),
    queryFn: () => fetchSpaceGrants(space),
  });
  const [rows, setRows] = useState<SpaceGrant[]>([]);
  const [kind, setKind] = useState<Kind>('user');
  const [name, setName] = useState('');
  useEffect(() => {
    if (grants.data) setRows(grants.data);
  }, [grants.data]);
  const save = useMutation({
    mutationFn: () => setSpaceGrants(space, rows),
    onSuccess: (saved) => {
      client.setQueryData(spaceKeys.grants(space), saved);
      void client.invalidateQueries({ queryKey: spaceKeys.overview(space) });
      toast(t('folio.permissions.saved'));
    },
  });

  if (!grants.data) return <Spinner />;
  const who = (g: SpaceGrant) =>
    g.grantee_type === 'everyone'
      ? t('folio.permissions.everyone')
      : g.grantee_type === 'group'
        ? t('folio.permissions.group', { name: g.grantee })
        : `@${g.grantee}`;
  const toggle = (i: number, p: SpacePermission) =>
    setRows(
      rows.map((g, j) =>
        j !== i
          ? g
          : {
              ...g,
              permissions: g.permissions.includes(p)
                ? g.permissions.filter((x) => x !== p)
                : [...g.permissions, p],
            },
      ),
    );
  const add = (event: FormEvent) => {
    event.preventDefault();
    const grantee = kind === 'everyone' ? null : name.trim().replace(/^@/, '');
    if (kind !== 'everyone' && !grantee) return;
    setRows([...rows, { grantee_type: kind, grantee, permissions: ['view'] }]);
    setName('');
  };

  return (
    <S.Card>
      <S.Intro>
        <b>{t('folio.permissions.title')}</b>
        <span>{t('folio.permissions.hint')}</span>
      </S.Intro>
      <S.Scroll>
        <table>
          <thead>
            <tr>
              <th>{t('folio.permissions.who')}</th>
              {PERMISSIONS.map((p) => (
                <th key={p}>{t(`folio.permissions.p.${p}`)}</th>
              ))}
              <th aria-label={t('folio.permissions.remove')} />
            </tr>
          </thead>
          <tbody>
            {rows.map((g, i) => (
              <tr key={`${g.grantee_type}-${g.grantee ?? ''}`}>
                <td>{who(g)}</td>
                {PERMISSIONS.map((p) => (
                  <td key={p}>
                    <input
                      type="checkbox"
                      aria-label={`${who(g)}: ${t(`folio.permissions.p.${p}`)}`}
                      checked={
                        g.permissions.includes(p) ||
                        (p !== 'admin' && g.permissions.includes('admin'))
                      }
                      disabled={p !== 'admin' && g.permissions.includes('admin')}
                      onChange={() => toggle(i, p)}
                    />
                  </td>
                ))}
                <td>
                  <S.Remove
                    type="button"
                    aria-label={t('folio.permissions.removeWho', { who: who(g) })}
                    onClick={() => setRows(rows.filter((_, j) => j !== i))}
                  >
                    <Trash2 aria-hidden />
                  </S.Remove>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </S.Scroll>
      <S.Add onSubmit={add}>
        <select
          aria-label={t('folio.permissions.kind')}
          value={kind}
          onChange={(e) => setKind(e.target.value as Kind)}
        >
          <option value="user">{t('folio.permissions.kinds.user')}</option>
          <option value="group">{t('folio.permissions.kinds.group')}</option>
          <option value="everyone">{t('folio.permissions.kinds.everyone')}</option>
        </select>
        {kind !== 'everyone' && (
          <Input
            aria-label={t('folio.permissions.name')}
            placeholder={kind === 'user' ? '@luis' : 'equipo-legal'}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        )}
        <Button type="submit">{t('folio.permissions.add')}</Button>
      </S.Add>
      {save.error && <S.Error role="alert">{errorMessage(save.error)}</S.Error>}
      <div>
        <Button variant="primary" onClick={() => save.mutate()} disabled={save.isPending}>
          {t('folio.permissions.save')}
        </Button>
      </div>
    </S.Card>
  );
}
