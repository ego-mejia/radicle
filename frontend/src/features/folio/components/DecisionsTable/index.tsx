import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { formatDate } from '../../../../lib/format';
import {
  fetchDecisions,
  sectionKeys,
  type DecisionFilters,
  type DecisionStatusFilter,
} from '../../../../services/api/folioSections';
import { ActiveFilters, type ActiveFilter } from '../ActiveFilters';
import { FilterPicker } from '../FilterPicker';
import * as S from './style';

const PAGE = 50;
const STATUS_FILTERS: DecisionStatusFilter[] = [
  'current',
  'accepted',
  'proposed',
  'replaced',
  'all',
];
const number = (n: number) => String(n).padStart(4, '0');

type Props = {
  space: string;
  filters?: DecisionFilters;
  onFiltersChange?: (filters: DecisionFilters) => void;
};

/** The Architecture decisions section of a space (RAD-57, board N2): each decision with its
 * number, topic, project and status. Only current ones by default; replaced ones are
 * counted, and a decision says which one it replaces. */
export function DecisionsTable({ space, filters, onFiltersChange }: Props) {
  const { t } = useTranslation();
  const [own, setOwn] = useState<DecisionFilters>({ status: 'current' });
  const f = filters ?? own;
  const set = (next: DecisionFilters) => (onFiltersChange ?? setOwn)(next);
  const [limit, setLimit] = useState(PAGE);
  const { data, error } = useQuery({
    queryKey: sectionKeys.decisions(space, f, limit),
    queryFn: () => fetchDecisions(space, f, limit),
    placeholderData: keepPreviousData,
  });
  const statusFilter = (s: DecisionStatusFilter) => t(`folio.decisionsTable.filter.${s}`);
  const status = (s: string) => t(`folio.decisionsTable.status.${s}`);

  const active: ActiveFilter[] = [
    ...(f.topic
      ? [{ key: 'topic', label: f.topic, onRemove: () => set({ ...f, topic: undefined }) }]
      : []),
    ...(f.project
      ? [{ key: 'project', label: f.project, onRemove: () => set({ ...f, project: undefined }) }]
      : []),
    ...(f.status !== 'current'
      ? [
          {
            key: 'status',
            label: statusFilter(f.status),
            onRemove: () => set({ ...f, status: 'current' }),
          },
        ]
      : []),
    ...(f.q ? [{ key: 'q', label: `“${f.q}”`, onRemove: () => set({ ...f, q: undefined }) }] : []),
  ];

  return (
    <S.Wrap>
      <S.Bar>
        <FilterPicker
          label={t('folio.decisionsTable.topic')}
          allLabel={t('folio.filters.all')}
          options={(data?.topics ?? []).map((x) => ({
            value: x.value,
            label: x.value,
            count: x.count,
          }))}
          selected={f.topic ? [f.topic] : []}
          onChange={([v]) => set({ ...f, topic: v })}
        />
        <FilterPicker
          label={t('folio.decisionsTable.project')}
          allLabel={t('folio.filters.all')}
          options={(data?.projects ?? []).map((x) => ({
            value: x.value,
            label: x.value,
            count: x.count,
          }))}
          selected={f.project ? [f.project] : []}
          onChange={([v]) => set({ ...f, project: v })}
        />
        <FilterPicker
          label={t('folio.decisionsTable.statusLabel')}
          options={STATUS_FILTERS.map((s) => ({ value: s, label: statusFilter(s) }))}
          selected={[f.status]}
          onChange={([v]) => set({ ...f, status: (v as DecisionStatusFilter) ?? 'current' })}
        />
        {data?.hidden_replaced ? (
          <S.Hidden>{t('folio.decisionsTable.hidden', { count: data.hidden_replaced })}</S.Hidden>
        ) : null}
      </S.Bar>
      <ActiveFilters
        filters={active}
        summary={t('folio.decisionsTable.count', { count: data?.total ?? 0 })}
        onClear={active.length > 1 ? () => set({ status: 'current' }) : undefined}
      />
      <S.Box>
        {error ? (
          <S.Empty role="alert">{t('folio.decisionsTable.failed')}</S.Empty>
        ) : data && !data.items.length ? (
          <S.Empty>
            {active.length ? t('folio.decisionsTable.noMatch') : t('folio.decisionsTable.empty')}
          </S.Empty>
        ) : (
          <S.Table aria-busy={!data}>
            <thead>
              <tr>
                <th>#</th>
                <th>{t('folio.decisionsTable.decision')}</th>
                <th>{t('folio.decisionsTable.topic')}</th>
                <th>{t('folio.decisionsTable.project')}</th>
                <th>{t('folio.decisionsTable.statusLabel')}</th>
                <th>{t('folio.decisionsTable.replaces')}</th>
                <th>{t('folio.decisionsTable.date')}</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((d) => (
                <tr key={d.node.id}>
                  <td>
                    <S.Number>{number(d.number)}</S.Number>
                  </td>
                  <td>
                    <Link to="/folio/p/$page" params={{ page: `${d.node.id}-${d.node.slug}` }}>
                      {d.node.title}
                    </Link>
                  </td>
                  <td>{d.topic ? <S.Topic>{d.topic}</S.Topic> : '—'}</td>
                  <td>{d.project ? <S.Project>{d.project}</S.Project> : '—'}</td>
                  <td>
                    <S.Status $status={d.status}>
                      {d.replaced_by
                        ? t('folio.decisionsTable.replacedBy', { number: number(d.replaced_by) })
                        : status(d.status)}
                    </S.Status>
                  </td>
                  <td>{d.replaces ? <S.Number>{number(d.replaces)}</S.Number> : '—'}</td>
                  <S.Muted as="td">
                    {d.published_at ? formatDate(d.published_at.slice(0, 10)) : ''}
                  </S.Muted>
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
