import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RotateCcw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { SettingsCard } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  accessKeys,
  fetchPermissions,
  putPermissions,
  resetPermissions,
} from '../../../../services/api/access';
import { authKeys } from '../../../../services/api/auth';
import { projectKeys } from '../../../../services/api/projects';
import type { ProjectDetail } from '../../../../services/api/types';
import * as S from './style';

/** Checkboxes per role; admins can always do everything. */
export function PermissionsSection({
  project,
  editable,
}: {
  project: ProjectDetail;
  editable: boolean;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const { data } = useQuery({
    queryKey: accessKeys.permissions(project.key),
    queryFn: () => fetchPermissions(project.key),
  });
  const done = (next: Awaited<ReturnType<typeof fetchPermissions>>) => {
    queryClient.setQueryData(accessKeys.permissions(project.key), next);
    void queryClient.invalidateQueries({ queryKey: projectKeys.detail(project.key) });
    void queryClient.invalidateQueries({ queryKey: authKeys.me });
  };
  const change = useMutation({
    mutationFn: (v: { role: 'member' | 'viewer'; permission: string; allowed: boolean }) =>
      putPermissions(project.key, { [v.role]: { [v.permission]: v.allowed } }),
    onSuccess: done,
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const reset = useMutation({
    mutationFn: () => resetPermissions(project.key),
    onSuccess: done,
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  if (!data) return <PageSpinner />;
  return (
    <SettingsCard title={t('settings.permissions')} help={t('settings.permissionsHelp')}>
      <S.Table>
        <thead>
          <tr>
            <th scope="col">{t('settings.permission')}</th>
            <th scope="col">{t('projects.roles.admin')}</th>
            <th scope="col">{t('projects.roles.member')}</th>
            <th scope="col">{t('projects.roles.viewer')}</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr key={row.permission}>
              <th scope="row">
                {t(`permissions.${row.permission}`, row.description)}
                <code>{row.permission}</code>
              </th>
              <td>
                <input type="checkbox" checked disabled aria-label={`${row.permission} admin`} />
              </td>
              {(['member', 'viewer'] as const).map((role) => {
                const value = row[role];
                const changed = value !== row[`${role}_default`];
                return (
                  <S.Cell key={role} $changed={changed}>
                    <input
                      type="checkbox"
                      aria-label={`${row.permission} ${role}`}
                      checked={value}
                      disabled={!editable || change.isPending}
                      onChange={(e) =>
                        change.mutate({
                          role,
                          permission: row.permission,
                          allowed: e.target.checked,
                        })
                      }
                    />
                  </S.Cell>
                );
              })}
            </tr>
          ))}
        </tbody>
      </S.Table>
      {editable && (
        <Button size="sm" onClick={() => reset.mutate()}>
          <RotateCcw />
          {t('settings.restoreDefaults')}
        </Button>
      )}
    </SettingsCard>
  );
}
