import { useInfiniteQuery } from '@tanstack/react-query';
import { Download } from 'lucide-react';
import { Fragment, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { formatDateTime } from '../../../../lib/format';
import {
  AUDIT_GROUPS,
  auditCsvUrl,
  type AuditFilters,
  auditKeys,
  fetchAudit,
} from '../../../../services/api/audit';
import * as S from './style';

/** Filterable audit log with before/after details and CSV export. */
export function AuditLog({ project }: { project?: string }) {
  const { t } = useTranslation();
  const [filters, setFilters] = useState<AuditFilters>({ project });
  const [open, setOpen] = useState<number | null>(null);
  const query = useInfiniteQuery({
    queryKey: auditKeys.list(filters),
    queryFn: ({ pageParam }) => fetchAudit(filters, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
  const set = (patch: AuditFilters) => setFilters((f) => ({ ...f, ...patch }));
  const rows = query.data?.pages.flatMap((p) => p.items) ?? [];
  return (
    <S.Wrap>
      <S.Filters>
        <Field label={t('audit.actor')}>
          <Input
            value={filters.actor ?? ''}
            placeholder="@handle"
            onChange={(e) => set({ actor: e.target.value || undefined })}
          />
        </Field>
        <Field label={t('audit.action')}>
          <Select
            value={filters.action ?? ''}
            onChange={(e) => set({ action: e.target.value || undefined })}
          >
            <option value="">{t('audit.allActions')}</option>
            {AUDIT_GROUPS.map((g) => (
              <option key={g} value={g}>
                {g}.*
              </option>
            ))}
          </Select>
        </Field>
        {!project && (
          <Field label={t('audit.project')}>
            <Input
              value={filters.project ?? ''}
              placeholder="PA"
              onChange={(e) => set({ project: e.target.value || undefined })}
            />
          </Field>
        )}
        <Field label={t('reports.from')}>
          <Input
            type="date"
            value={filters.from ?? ''}
            onChange={(e) => set({ from: e.target.value || undefined })}
          />
        </Field>
        <Field label={t('reports.to')}>
          <Input
            type="date"
            value={filters.to ?? ''}
            onChange={(e) => set({ to: e.target.value || undefined })}
          />
        </Field>
        <S.Csv href={auditCsvUrl(filters)} download>
          <Download size={16} />
          {t('reports.csv')}
        </S.Csv>
      </S.Filters>
      {query.isPending ? (
        <PageSpinner />
      ) : query.error ? (
        <S.Error role="alert">{String((query.error as Error).message)}</S.Error>
      ) : (
        <S.Table>
          <thead>
            <tr>
              <th scope="col">{t('audit.when')}</th>
              <th scope="col">{t('audit.actor')}</th>
              <th scope="col">{t('audit.action')}</th>
              <th scope="col">{t('audit.target')}</th>
              <th scope="col">{t('audit.project')}</th>
              <th scope="col">IP</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={6}>{t('audit.empty')}</td>
              </tr>
            )}
            {rows.map((e) => (
              <Fragment key={e.id}>
                <tr
                  onClick={() => setOpen(open === e.id ? null : e.id)}
                  aria-expanded={open === e.id}
                  data-testid={`audit-${e.action}`}
                >
                  <td>{formatDateTime(e.created_at)}</td>
                  <td>{e.actor ? `@${e.actor}` : <i>{e.actor_kind}</i>}</td>
                  <td>
                    <code>{e.action}</code>
                  </td>
                  <td>
                    {e.target_type}
                    {e.target_id ? ` · ${e.target_id}` : ''}
                  </td>
                  <td>{e.project ?? ''}</td>
                  <td>{e.ip ?? ''}</td>
                </tr>
                {open === e.id && (
                  <tr>
                    <td colSpan={6}>
                      <S.Details>
                        {'before' in e.details && (
                          <div>
                            <b>{t('audit.before')}</b>
                            <pre>{JSON.stringify(e.details.before, null, 2)}</pre>
                          </div>
                        )}
                        {'after' in e.details && (
                          <div>
                            <b>{t('audit.after')}</b>
                            <pre>{JSON.stringify(e.details.after, null, 2)}</pre>
                          </div>
                        )}
                        <div>
                          <b>{t('audit.more')}</b>
                          <pre>
                            {JSON.stringify(
                              Object.fromEntries(
                                Object.entries(e.details).filter(
                                  ([k]) => k !== 'before' && k !== 'after',
                                ),
                              ),
                              null,
                              2,
                            )}
                          </pre>
                          <small>{e.user_agent}</small>
                        </div>
                      </S.Details>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </S.Table>
      )}
      {query.hasNextPage && (
        <Button
          size="sm"
          onClick={() => void query.fetchNextPage()}
          disabled={query.isFetchingNextPage}
        >
          {t('audit.loadMore')}
        </Button>
      )}
    </S.Wrap>
  );
}
