import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useToast } from '../../../../hooks/useToast';
import { relativeTime } from '../../../../lib/format';
import {
  fetchSpecs,
  sectionKeys,
  type SpecFilters,
  type SpecStatus,
} from '../../../../services/api/folioSections';
import { ActiveFilters, type ActiveFilter } from '../ActiveFilters';
import { FilterPicker } from '../FilterPicker';
import { filtersToSearch } from './filtersToSearch';
import * as S from './style';

const STATUSES: SpecStatus[] = ['live', 'planned', 'done', 'outdated'];
const PAGE = 50;
const pct = (part: number, total: number) => (total ? (100 * part) / total : 0);

type Props = {
  space: string;
  /** Pass both to keep the filters in the URL; without them the table keeps its own. */
  filters?: SpecFilters;
  onFiltersChange?: (filters: SpecFilters) => void;
};

/** The Specs section of a space (RAD-57, board M4): every build spec in one table, filtered
 * by project and then by that project's features, by status and by owner. */
export function SpecsTable({ space, filters, onFiltersChange }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const [own, setOwn] = useState<SpecFilters>({ features: [] });
  const f = filters ?? own;
  const set = (next: SpecFilters) => (onFiltersChange ?? setOwn)(next);
  const [limit, setLimit] = useState(PAGE);
  const { data, error } = useQuery({
    queryKey: sectionKeys.specs(space, f, limit),
    queryFn: () => fetchSpecs(space, f, limit),
    placeholderData: keepPreviousData,
  });

  const status = (s: SpecStatus) => t(`folio.specsTable.status.${s}`);
  const projects = (data?.projects ?? []).map((p) => ({
    value: p.value,
    label: p.value,
    count: p.count,
  }));
  const features = (data?.features ?? []).map((x) => ({
    value: x.value,
    label: x.value,
    count: x.count,
  }));
  const owners = (data?.owners ?? []).map((o) => ({
    value: o.handle,
    label: o.name,
    count: o.count,
  }));
  const ownerName = owners.find((o) => o.value === f.owner)?.label ?? f.owner;

  const active: ActiveFilter[] = [
    ...(f.project
      ? [
          {
            key: 'project',
            label: f.project,
            onRemove: () => set({ ...f, project: undefined, features: [] }),
          },
        ]
      : []),
    ...f.features.map((x) => ({
      key: `feature:${x}`,
      label: x,
      onRemove: () => set({ ...f, features: f.features.filter((y) => y !== x) }),
    })),
    ...(f.status
      ? [
          {
            key: 'status',
            label: status(f.status),
            onRemove: () => set({ ...f, status: undefined }),
          },
        ]
      : []),
    ...(f.owner
      ? [{ key: 'owner', label: ownerName ?? '', onRemove: () => set({ ...f, owner: undefined }) }]
      : []),
    ...(f.q ? [{ key: 'q', label: `“${f.q}”`, onRemove: () => set({ ...f, q: undefined }) }] : []),
  ];

  const saveView = async () => {
    const url = `${window.location.origin}${window.location.pathname}?${filtersToSearch(f)}`;
    try {
      await navigator.clipboard.writeText(url);
      toast(t('folio.specsTable.viewCopied'));
    } catch {
      toast(url);
    }
  };

  return (
    <S.Wrap>
      <S.Bar>
        <FilterPicker
          label={t('folio.specsTable.project')}
          allLabel={t('folio.specsTable.allProjects')}
          options={projects}
          selected={f.project ? [f.project] : []}
          onChange={([p]) => set({ ...f, project: p, features: [] })}
        />
        <FilterPicker
          label={t('folio.specsTable.feature')}
          options={features}
          selected={f.features}
          onChange={(values) => set({ ...f, features: values })}
          multi
          searchable
          hint={f.project ? undefined : t('folio.specsTable.pickProject')}
        />
        <FilterPicker
          label={t('folio.specsTable.statusLabel')}
          allLabel={t('folio.filters.all')}
          options={STATUSES.map((s) => ({ value: s, label: status(s) }))}
          selected={f.status ? [f.status] : []}
          onChange={([s]) => set({ ...f, status: s as SpecStatus | undefined })}
        />
        <FilterPicker
          label={t('folio.specsTable.owner')}
          allLabel={t('folio.filters.all')}
          options={owners}
          selected={f.owner ? [f.owner] : []}
          onChange={([o]) => set({ ...f, owner: o })}
          searchable={owners.length > 8}
        />
        <S.Save type="button" onClick={saveView}>
          {t('folio.specsTable.saveView')}
        </S.Save>
      </S.Bar>
      <ActiveFilters
        filters={active}
        summary={t('folio.specsTable.count', { count: data?.total ?? 0 })}
        onClear={active.length > 1 ? () => set({ features: [] }) : undefined}
      />
      <S.Box>
        {error ? (
          <S.Empty role="alert">{t('folio.specsTable.failed')}</S.Empty>
        ) : data && !data.items.length ? (
          <S.Empty>
            {active.length ? t('folio.specsTable.noMatch') : t('folio.specsTable.empty')}
          </S.Empty>
        ) : (
          <S.Table aria-busy={!data}>
            <thead>
              <tr>
                <th>{t('folio.specsTable.spec')}</th>
                <th>{t('folio.specsTable.project')}</th>
                <th>{t('folio.specsTable.feature')}</th>
                <th>{t('folio.specsTable.progress')}</th>
                <th>{t('folio.specsTable.statusLabel')}</th>
                <th>{t('folio.specsTable.owner')}</th>
                <th>{t('folio.specsTable.updated')}</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((s) => (
                <tr key={s.node.id}>
                  <td>
                    <Link to="/folio/p/$page" params={{ page: `${s.node.id}-${s.node.slug}` }}>
                      {s.node.title}
                    </Link>
                  </td>
                  <td>{s.project ? <S.Project>{s.project}</S.Project> : '—'}</td>
                  <td>
                    {s.features.map((x) => (
                      <S.Feature key={x}>{x}</S.Feature>
                    ))}
                  </td>
                  <td>
                    <S.Progress
                      role="img"
                      aria-label={t('folio.specsTable.ticketsDone', {
                        done: s.tickets_done,
                        total: s.tickets_total,
                      })}
                      title={t('folio.specsTable.ticketsDone', {
                        done: s.tickets_done,
                        total: s.tickets_total,
                      })}
                    >
                      <S.Done $pct={pct(s.tickets_done, s.tickets_total)} />
                      <S.Live $pct={pct(s.tickets_in_progress, s.tickets_total)} />
                    </S.Progress>
                  </td>
                  <td>
                    <S.Status $status={s.status}>{status(s.status)}</S.Status>
                  </td>
                  <td>{s.owner_name ?? s.owner ?? '—'}</td>
                  <S.Muted as="td">{relativeTime(s.updated_at)}</S.Muted>
                </tr>
              ))}
            </tbody>
          </S.Table>
        )}
      </S.Box>
      {data && data.total > data.items.length ? (
        <S.More type="button" onClick={() => setLimit(limit + PAGE)}>
          {t('folio.specsTable.more', { count: Math.min(PAGE, data.total - data.items.length) })}
        </S.More>
      ) : null}
    </S.Wrap>
  );
}
